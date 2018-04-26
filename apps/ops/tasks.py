# coding: utf-8
from celery import shared_task, subtask, Task

from common.utils import get_logger, get_object_or_none
from .celery.utils import log_task_stdout
from .models import AdHocTask, AuthChangeTask

logger = get_logger(__file__)


@shared_task
def run_adhoc_task(tid, callback=None, **kwargs):
    """
    :param tid: is the ansible task id or adhoc
    :param callback: callback function name
    :return:
    """
    task = get_object_or_none(AdHocTask, id=tid)
    if task:
        result = task.run()
        return result
    else:
        logger.error("No ansible task found: {}".format(tid))


@shared_task
def run_auth_change_task(tid, **kwargs):
    task = get_object_or_none(AuthChangeTask, pk=tid)
    if task:
        return task.run()
    else:
        logger.error("No auth change task found: {}".format(tid))


@shared_task
def hello(name, callback=None):
    print("Hello {}".format(name))
    if callback is not None:
        subtask(callback).delay("Guahongwei")


@shared_task
def hello_callback(result):
    print(result)
    print("Hello callback")

