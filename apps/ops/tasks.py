# coding: utf-8
from celery import shared_task, subtask

from common.utils import get_logger, get_object_or_none
from .models import AnsibleTask, AuthChangeTask

logger = get_logger(__file__)


def rerun_task():
    pass


@shared_task
def run_ansible_task(tid, callback=None, **kwargs):
    """
    :param tid: is the ansible task id or adhoc
    :param callback: callback function name
    :return:
    """
    task = get_object_or_none(AnsibleTask, id=tid)
    if task:
        result = task.run()
        if callback is not None:
            subtask(callback).delay(result, task_name=task.name)
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

