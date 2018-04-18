# -*- coding: utf-8 -*-
#
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask

from common.utils import get_signer
from ..celery.utils import delete_celery_periodic_task, \
    create_or_update_celery_periodic_tasks, \
    disable_celery_periodic_task

__all__ = ['AuthChangeTask']
signer = get_signer()


class AuthChangeTask(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True)
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    _password = models.CharField(max_length=1024, blank=True, null=True)
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', verbose_name=_("Node"))
    interval = models.IntegerField(verbose_name=_("Interval"), default=45, help_text=_("Units: day"))
    crontab = models.CharField(max_length=32, verbose_name=_("Crontab"), blank=True, null=True, help_text="* * 4 * *")
    different = models.BooleanField(default=False, verbose_name=_("Different every asset"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    comment = models.TextField(verbose_name=_("Comment"))
    created_by = models.CharField(max_length=128, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{}:{}'.format(self.name, self.id)

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        else:
            return None

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def schedule(self):
        try:
            return PeriodicTask.objects.get(name=self.__str__())
        except PeriodicTask.DoesNotExist:
            return None

    def run(self):
        from ..utils import update_or_create_ansible_task
        from ..tasks import run_auth_change_task
        hosts = [str(host.id) for host in self.get_assets()]
        ansible_task = update_or_create_ansible_task(
            self.name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
        )

    def get_tasks(self):
        tasks = []
        assets = self.get_assets()



    def get_assets(self):
        assets = set(self.assets.all().filter(is_active=True))
        for node in self.nodes.all():
            assets.update(set(node.get_all_assets().filter(is_active=True)))
        return assets

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        instance = super().save(force_insert=force_insert, force_update=force_update,
                                using=using, update_fields=update_fields)
        if self.is_active:
            interval = None
            crontab = None

            if self.interval:
                interval = self.interval
            elif self.crontab:
                crontab = self.crontab

            tasks = {
                self.__str__(): {
                    "task": run_auth_change_task.name,
                    "interval": '{}d'.format(interval),
                    "crontab": crontab,
                    "args": (str(self.id),),
                    "enabled": True,
                }
            }
            create_or_update_celery_periodic_tasks(tasks)
        else:
            disable_celery_periodic_task(self.name)
        return instance


