# -*- coding: utf-8 -*-
#
import os
import datetime
import sys
import time
import logging

from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from celery import subtask
from celery.signals import worker_ready, worker_shutdown, task_prerun, \
    task_postrun, after_task_publish, after_setup_task_logger, setup_logging
from celery.utils.log import get_logger
from django_celery_beat.models import PeriodicTask

from common.utils import  StdRedirectFile, get_object_or_none
from .const import CELERY_LOG_DIR
from .utils import get_after_app_ready_tasks, get_after_app_shutdown_clean_tasks, \
    redirect_stdout
from ..models import CeleryTask
from . import app

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


@task_prerun.connect
def pre_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    print("PRE RUN" * 20)
    print(task)
    print(task.request)
    root_id = task.request.get("root_id")
    log_id = root_id if root_id else task_id
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(now, log_id + '.log')
    full_path = os.path.join(CELERY_LOG_DIR, log_path)

    if not os.path.exists(os.path.dirname(full_path)):
        os.makedirs(os.path.dirname(full_path))
    fh = logging.FileHandler(full_path)
    logger.addHandler(fh)
    redirect_stdout(logger)
    print("Hello world")
    print("Hello world\r\n")
    print("Hello world")
    task.fh = fh


@task_postrun.connect
def post_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    logger.removeHandler(task.fh)
