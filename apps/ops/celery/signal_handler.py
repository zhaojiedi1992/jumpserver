# -*- coding: utf-8 -*-
#
import os
import datetime
import sys
import time

from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from celery import subtask
from celery.signals import worker_ready, worker_shutdown, task_prerun, \
    task_postrun, after_task_publish
from django_celery_beat.models import PeriodicTask

from common.utils import get_logger, TeeObj, get_object_or_none
from .const import CELERY_LOG_DIR
from .utils import get_after_app_ready_tasks, get_after_app_shutdown_clean_tasks
from ..models import CeleryTask

logger = get_logger(__file__)


@worker_ready.connect
def on_app_ready(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_READY", 0) == 1:
        return
    cache.set("CELERY_APP_READY", 1, 10)
    logger.debug("App ready signal recv")
    tasks = get_after_app_ready_tasks()
    logger.debug("Start need start task: [{}]".format(
        ", ".join(tasks))
    )
    for task in tasks:
        subtask(task).delay()


@worker_shutdown.connect
def after_app_shutdown(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_SHUTDOWN", 0) == 1:
        return
    cache.set("CELERY_APP_SHUTDOWN", 1, 10)
    tasks = get_after_app_shutdown_clean_tasks()
    logger.debug("App shutdown signal recv")
    logger.debug("Clean need cleaned period tasks: [{}]".format(
        ', '.join(tasks))
    )
    PeriodicTask.objects.filter(name__in=tasks).delete()


# @task_prerun.connect
# def pre_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
#     now = datetime.datetime.now().strftime("%Y-%m-%d")
#     log_path = os.path.join(now, task_id + '.log')
#     full_path = os.path.join(CELERY_LOG_DIR, log_path)
#
#     if not os.path.exists(os.path.dirname(full_path)):
#         os.makedirs(os.path.dirname(full_path))
#     f = open(full_path, 'w')
#     tee = TeeObj(f)
#     sys.stdout = tee
#     task.log_f = tee
# #
#
# @task_postrun.connect
# def post_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
#     if getattr(task, 'log_f'):
#         task.log_f.flush()
#         sys.stdout = task.log_f.origin_stdout
#         task.log_f.close()

