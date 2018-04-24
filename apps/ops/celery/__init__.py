# -*- coding: utf-8 -*-

import os
import uuid
import sys

from celery import Celery, platforms, Task

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')

from django.conf import settings
from django.core.cache import cache
from common.utils import TeeObj

from .const import CELERY_LOG_DIR


class CustomTask(Task):
    id = None

    def __init__(self):
        super().__init__()
        old_attr = self.run
        self.run = self.wrapper_run(old_attr)

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        if not task_id:
            self.id = str(uuid.uuid4())
        self.id = task_id
        res = super().apply_async(
            args=args, kwargs=kwargs, task_id=task_id,
            producer=producer, link=link, link_error=link_error,
            shadow=shadow, **options,
        )
        cache.set(res.id, res)
        return res

    def get_log_f(self):
        from .utils import get_log_path
        root_id = self.request.get('root_id')
        log_id = self.request.get('id')

        if root_id:
            log_id = root_id
        if log_id:
            log_path = get_log_path(log_id)
            f = open(log_path, 'a')
            tee = TeeObj(f)
            return tee
        return None

    def wrapper_run(self, method):
        def wrapper(*args, **kwargs):
            log_f = self.get_log_f()
            old_outs = sys.stdout, sys.stderr
            if log_f:
                sys.stdout = log_f
                sys.stderr = log_f
            try:
                return method(*args, **kwargs)
            finally:
                sys.stdout, sys.stderr = old_outs
                log_f.close() if log_f else print()
        return wrapper


app = Celery('jumpserver', task_cls=CustomTask)
platforms.C_FORCE_ROOT = True

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: [app_config.split('.')[0] for app_config in settings.INSTALLED_APPS])


@app.task
def add(x, y):
    return x +y