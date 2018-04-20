# ~*~ coding: utf-8 ~*~

import json
import uuid
import os
import time
import datetime

from celery import current_task
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask

from common.fields import JsonCharField, JsonTextField
from common.utils import get_signer, get_logger
from ..celery.utils import delete_celery_periodic_task, \
    create_or_update_celery_periodic_tasks, \
    disable_celery_periodic_task
from ..ansible import AdHocRunner
from ..inventory import JMSInventory

__all__ = ["AnsibleTask", "AdHoc", "AdHocRunHistory"]


logger = get_logger(__file__)
signer = get_signer()


class AnsibleTask(models.Model):
    """
    This task is different ansible task, Task like 'push system user', 'get asset info' ..
    One task can have some versions of adhoc, run a task only run the latest version adhoc
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    interval = models.IntegerField(verbose_name=_("Interval"), null=True, blank=True, help_text=_("Units: seconds"))
    crontab = models.CharField(verbose_name=_("Crontab"), null=True, blank=True, max_length=128, help_text=_("5 * * * *"))
    is_periodic = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.CharField(max_length=128, blank=True, null=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)
    __latest_adhoc = None

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_adhoc(self):
        if not self.__latest_adhoc:
            self.__latest_adhoc = self.get_latest_adhoc()
        return self.__latest_adhoc

    @latest_adhoc.setter
    def latest_adhoc(self, item):
        self.__latest_adhoc = item

    @property
    def latest_history(self):
        try:
            return self.history.all().latest()
        except AdHocRunHistory.DoesNotExist:
            return None

    def get_latest_adhoc(self):
        try:
            return self.adhoc.all().latest()
        except AdHoc.DoesNotExist:
            return None

    @property
    def history_summary(self):
        history = self.get_run_history()
        total = len(history)
        success = len([history for history in history if history.is_success])
        failed = len([history for history in history if not history.is_success])
        return {'total': total, 'success': success, 'failed': failed}

    def get_run_history(self):
        return self.history.all()

    def run(self):
        if self.latest_adhoc:
            return self.latest_adhoc.run()
        else:
            return {'error': 'No adhoc'}

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        from ..tasks import run_ansible_task
        super().save(
            force_insert=force_insert,  force_update=force_update,
            using=using, update_fields=update_fields,
        )

        if self.is_periodic:
            tasks = {
                self.name: {
                    "task": run_ansible_task.name,
                    "interval": self.interval or None,
                    "crontab": self.crontab or None,
                    "args": (str(self.id),),
                    "enabled": True,
                }
            }
            create_or_update_celery_periodic_tasks(tasks)
        else:
            disable_celery_periodic_task(self.name)

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
        delete_celery_periodic_task(self.name)

    @property
    def schedule(self):
        try:
            return PeriodicTask.objects.get(name=self.name)
        except PeriodicTask.DoesNotExist:
            return None

    def __str__(self):
        return '{}:{}'.format(self.name, self.id)

    class Meta:
        get_latest_by = 'date_created'


class AdHoc(models.Model):
    """
    task: A task reference
    actions: [{'name': 'task_name', 'action': {'module': '', 'args': ''}, 'other..': ''}, ]
    options: ansible options, more see ops.ansible.runner.Options
    assets:
    nodes:
    run_as_admin: if true, then need get every host admin user run it, because every host may be have different admin user, so we choise host level
    run_as: if not run as admin, it run it as a system/common user from cmdb
    become: May be using become [sudo, su] options. {method: "sudo", user: "user", pass: "pass"]
    pattern: Even if we set _hosts, We only use that to make inventory, We also can set `patter` to run task on match hosts
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    assets = models.ManyToManyField('assets.Asset', blank=True, verbose_name=_("Asset"))  # ['hostname1', 'hostname2']
    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Node"))
    task = models.ForeignKey(AnsibleTask, related_name='adhoc', on_delete=models.CASCADE)
    actions = JsonTextField(verbose_name=_('Actions'))
    vars = JsonTextField(verbose_name=_('Vars'), blank=True, null=True)
    pattern = models.CharField(max_length=1024, default='all', verbose_name=_('Pattern'))
    options = JsonCharField(max_length=1024, blank=True, null=True, verbose_name=_('Options'))
    run_as_admin = models.BooleanField(default=False, verbose_name=_('Run as admin'))
    run_as = models.ForeignKey('assets.SystemUser', null=True, blank=True, verbose_name=_("Run as"))
    become = JsonCharField(max_length=1024, blank=True, null=True, verbose_name=_("Become"))
    created_by = models.CharField(max_length=64, default='', null=True, verbose_name=_('Create by'))
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def inventory(self):
        become_info = {'become': self.become} if self.become else None
        inventory = JMSInventory(
            self.assets.all(), nodes=self.nodes.all(), run_as_admin=self.run_as_admin,
            run_as=self.run_as, become_info=become_info, vars=self.vars,
        )
        return inventory

    @property
    def total_assets(self):
        assets = set(self.assets.all())
        for node in self.nodes.all():
            assets.update(set(node.get_all_assets()))
        return assets

    @property
    def total_assets_count(self):
        return len(self.total_assets)

    def run(self):
        history = AdHocRunHistory(adhoc=self, task=self.task)
        history.save()
        log_f = open(history.log_path, 'w')
        print(history.log_path)
        time_start = time.time()
        is_success = False
        try:
            result = self._run(log_f=log_f)
            if result:
                is_success = True
                history.result = result.results_raw
                history.summary = result.results_summary
                return result.results_raw, result.results_summary
        finally:
            log_f.close()
            history.is_success = is_success
            history.is_finished = True
            history.date_finished = timezone.now()
            history.timedelta = time.time() - time_start
            history.save()

    def _run(self, log_f=None):
        runner = AdHocRunner(self.inventory, options=self.options)
        try:
            result = runner.run(self.actions, self.pattern, self.task.name, log_f=log_f)
            return result
        except Exception as e:
            logger.warn("Failed run adhoc {}, {}".format(self.task.name, e))
            return None

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_history(self):
        try:
            return self.history.all().latest()
        except AdHocRunHistory.DoesNotExist:
            return None

    def __str__(self):
        return "{} of {}".format(self.task.name, self.short_id)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        fields_check = []
        for field in self.__class__._meta.fields:
            if field.name not in ['id', 'date_created', 'created_by']:
                fields_check.append(field)
        for field in fields_check:
            if getattr(self, field.name) != getattr(other, field.name):
                return False
        return True

    class Meta:
        db_table = "ops_adhoc"
        get_latest_by = 'date_created'


class AdHocRunHistory(models.Model):
    """
    AdHoc running history.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(AnsibleTask, related_name='history', on_delete=models.SET_NULL, null=True)
    adhoc = models.ForeignKey(AdHoc, related_name='history', on_delete=models.SET_NULL, null=True)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    result = JsonTextField(blank=True, null=True, default={}, verbose_name=_('Adhoc raw result'))
    summary = JsonTextField(blank=True, null=True, default={}, verbose_name=_('Adhoc summary'))

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def log_path(self):
        dt = datetime.datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(settings.PROJECT_DIR, 'data', 'ansible', dt)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return os.path.join(log_dir, str(self.id) + '.log')

    @property
    def success_hosts(self):
        return self.summary.get('contacted', []) if self.summary else []

    @property
    def failed_hosts(self):
        return self.summary.get('dark', {}) if self.summary else []

    def __str__(self):
        return self.short_id

    class Meta:
        db_table = "ops_adhoc_history"
        get_latest_by = 'date_start'
