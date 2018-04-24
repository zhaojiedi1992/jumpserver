# ~*~ coding: utf-8 ~*~

import uuid
import os
import time
import datetime

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

__all__ = ["AdHocTask", "AdHocContent", "AdHocRunHistory"]


logger = get_logger(__file__)
signer = get_signer()


class AdHocTask(models.Model):
    """
    This task is different ansible task, Task like 'push system user', 'get asset info' ..
    One task can have some versions of adhoc, run a task only run the latest version adhoc
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    interval = models.CharField(verbose_name=_("Interval"), null=True, blank=True, help_text=_("10s/1m/1h/1d"), max_length=8)
    crontab = models.CharField(verbose_name=_("Crontab"), null=True, blank=True, max_length=128, help_text=_("5 * * * *"))
    is_periodic = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.CharField(max_length=128, blank=True, null=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)
    __latest_content = None

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_content(self):
        if not self.__latest_content:
            self.__latest_content = self.get_latest_content()
        return self.__latest_content

    @latest_content.setter
    def latest_content(self, item):
        self.__latest_content = item

    @property
    def latest_history(self):
        try:
            return self.history.all().latest()
        except AdHocRunHistory.DoesNotExist:
            return None

    def get_latest_content(self):
        try:
            return self.content.all().latest()
        except AdHocContent.DoesNotExist:
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
        if self.latest_content:
            return self.latest_content.run()
        else:
            return {'error': 'No adhoc task'}

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        from ..tasks import run_adhoc_task
        super().save(
            force_insert=force_insert,  force_update=force_update,
            using=using, update_fields=update_fields,
        )

        if self.is_periodic:
            tasks = {
                self.name: {
                    "task": run_adhoc_task.name,
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


class AdHocContent(models.Model):
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
    task = models.ForeignKey(AdHocTask, related_name='content', on_delete=models.CASCADE)
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
        history = AdHocRunHistory(content=self, task=self.task)
        history.save()
        log_f = open(history.log_path, 'w')
        time_start = time.time()
        result = {}
        try:
            runner = AdHocRunner(self.inventory, options=self.options)
            result = runner.run(self.actions, self.pattern, self.task.name, log_f=log_f)
        except Exception as e:
            result = {'raw': {}, 'summary': {'dark': {'all': str(e)}}}
        finally:
            log_f.close()
            history.result = result.get('raw')
            history.summary = result.get('summary')
            history.is_success = result.get('success', False)
            history.is_finished = True
            history.date_finished = timezone.now()
            history.timedelta = time.time() - time_start
            history.save()
        return result

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
        get_latest_by = 'date_created'


class AdHocRunHistory(models.Model):
    """
    AdHocContent running history.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(AdHocTask, related_name='history', on_delete=models.SET_NULL, null=True)
    content = models.ForeignKey(AdHocContent, related_name='history', on_delete=models.SET_NULL, null=True)
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    result = JsonTextField(blank=True, null=True, default={}, verbose_name=_('Adhoc raw result'))
    summary = JsonTextField(blank=True, null=True, default={}, verbose_name=_('Adhoc summary'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))

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
        get_latest_by = 'date_start'
