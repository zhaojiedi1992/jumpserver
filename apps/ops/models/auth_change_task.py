# -*- coding: utf-8 -*-
#
import uuid
import datetime
import os
import time

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask

from common.utils import get_signer, encrypt_password
from common.fields import JsonTextField
from ..celery.utils import delete_celery_periodic_task, \
    create_or_update_celery_periodic_tasks, \
    disable_celery_periodic_task

__all__ = ['AuthChangeTask', 'AuthChangeContent', 'AuthChangeRunHistory']
signer = get_signer()


class AuthChangeTask(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    interval = models.IntegerField(verbose_name=_("Interval"), default=45, blank=True, null=True, help_text=_("Units: day"))
    crontab = models.CharField(max_length=32, verbose_name=_("Crontab"), blank=True, null=True, help_text="* * 4 * *")
    different = models.BooleanField(default=False, verbose_name=_("Different"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    comment = models.TextField(verbose_name=_("Comment"), blank=True)

    @property
    def latest_content(self):
        try:
            return AuthChangeContent.objects.filter(task=self).latest()
        except AuthChangeContent.DoesNotExist:
            return None

    @property
    def latest_history(self):
        try:
            return AuthChangeRunHistory.objects.filter(task=self).latest()
        except AuthChangeContent.DoesNotExist:
            return None

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        instance = super().save(force_insert=force_insert, force_update=force_update,
                                using=using, update_fields=update_fields)
        from ..tasks import run_auth_change_task
        if self.is_active:
            interval = self.interval or None
            crontab = self.crontab or None
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

    def run(self, *args, **kwargs):
        try:
            content = self.content.latest()
            return content.run()
        except self.DoesNotExist:
            print("Not get content")


class AuthChangeContent(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(AuthChangeTask, on_delete=models.CASCADE, related_name='content')
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    _password = models.CharField(max_length=1024, blank=True, null=True)
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Asset"), blank=True)
    nodes = models.ManyToManyField('assets.Node', verbose_name=_("Node"), blank=True)
    created_by = models.CharField(max_length=128, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    ansible_pw_key = '_password'

    class Meta:
        get_latest_by = 'date_created'

    def __str__(self):
        return '{}:{}'.format(self.task.name, self.id)

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

    def gen_password(self):
        if self.password:
            return self.password
        else:
            return str(uuid.uuid4())

    def gen_password_vars(self, passwords):
        _vars = {}
        for k, v in passwords.items():
            password = encrypt_password(v, salt="K3mIlKK")
            _vars['__{}'.format(k.id)] = {self.ansible_pw_key: password}
        return _vars

    def gen_passwords(self):
        passwords = {}
        password = self.gen_password()
        for asset in self.get_assets():
            if self.task.different:
                passwords[asset] = self.gen_password()
            else:
                passwords[asset] = password
        return passwords

    def create_auth_book(self, passwords):
        from assets.models import AssetAuthBook

        book = []
        for k, v in passwords.items():
            auth = AssetAuthBook(username=self.username, asset=k)
            auth.password = v
            book.append(auth)
        book_created = AssetAuthBook.objects.bulk_create(book)
        return book_created

    def run(self):
        from ..utils import update_or_create_adhoc_task
        passwords = self.gen_passwords()
        _vars = self.gen_password_vars(passwords)
        book = self.create_auth_book(passwords)

        ansible_task, created = update_or_create_adhoc_task(
            task_name=self.task.name, assets=self.assets.all(), nodes=self.nodes.all(),
            actions=self.get_tasks(), pattern='all', run_as_admin=True,
            vars=_vars,
        )
        history = AuthChangeRunHistory(content=self, task=self.task)
        history.save()
        results = {}
        time_start = time.time()
        try:
            results = ansible_task.run()
            self.update_auth_book(results, book)
            return results
        finally:
            history.results = results
            history.is_success = results.get('success', False)
            history.is_finished = True
            history.date_finished = timezone.now()
            history.timedelta = round(time.time() - time_start, 2)
            history.save()

    @staticmethod
    def update_auth_book(results, book):
        from assets.models import AssetAuthBook
        success = results.get('summary', {}).get('contacted', [])
        book_need_update = set()
        for auth in book:
            if auth.asset.hostname in success:
                book_need_update.add(auth.id)
        AssetAuthBook.objects.filter(pk__in=book_need_update).update(is_active=True)

    def get_tasks(self):
        tasks = [{
            'name': 'Change password {}'.format(self.username),
            'action': {
                'module': 'user',
                'args': "name={} state=present password="
                        "{{{{ hostvars[inventory_hostname]['{}'] }}}}".format(
                             self.username, self.ansible_pw_key,
                        ),
            },
        }]
        return tasks

    def get_assets(self):
        assets = set(self.assets.all().filter(is_active=True))
        for node in self.nodes.all():
            assets.update(set(node.get_all_assets().filter(is_active=True)))
        return assets

    def delete(self, using=None, keep_parents=False):
        delete_celery_periodic_task(self.__str__())
        return super().delete(using=using, keep_parents=keep_parents)


class AuthChangeRunHistory(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    order_num = models.IntegerField()
    results = JsonTextField(blank=True, default={})
    task = models.ForeignKey(AuthChangeTask, on_delete=models.SET_NULL,
                             null=True, related_name='history')
    content = models.ForeignKey(AuthChangeContent, on_delete=models.SET_NULL,
                                null=True, related_name='history')
    is_finished = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'),
                                  null=True)
    date_start = models.DateTimeField(auto_now_add=True)
    date_finished = models.DateTimeField(null=True)

    @property
    def log_path(self):
        dt = datetime.datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(settings.PROJECT_DIR, 'data', 'ansible', dt)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return os.path.join(log_dir, str(self.id) + '.log')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        history = self.__class__.objects.filter(task=self.task)
        if not history:
            max_order_num = 0
        else:
            max_order_num = max(history.values_list('order_num', flat=True))
        self.order_num = max_order_num + 1
        return super().save(force_insert=force_insert, force_update=force_update,
                            using=using, update_fields=update_fields)

    class Meta:
        get_latest_by = 'date_start'


