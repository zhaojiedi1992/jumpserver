# ~*~ coding: utf-8 ~*~
from common.utils import get_logger, get_object_or_none
from .models import AnsibleTask, AdHoc

logger = get_logger(__file__)


def get_task_by_id(task_id):
    return get_object_or_none(AnsibleTask, id=task_id)


def update_or_create_ansible_task(
        task_name, assets=None, actions=None, nodes=None,
        interval=None, crontab=None, is_periodic=False,
        pattern='all', options=None, run_as_admin=False,
        run_as=None, created_by=None, vars=None, comment='',
        become=None,
    ):

    if not assets and not nodes:
        raise ValueError("Must set assets and nodes")
    elif not actions:
        raise ValueError("Actions must be set")

    defaults = {
        'name': task_name,
        'interval': interval,
        'crontab': crontab,
        'is_periodic': is_periodic,
        'comment': comment,
        'created_by': created_by,
    }

    created = False
    task, _ = AnsibleTask.objects.update_or_create(
        defaults=defaults, name=task_name,
    )

    adhoc = task.latest_adhoc
    new_adhoc = AdHoc(
        task=task, actions=actions, vars=vars, pattern=pattern,
        options=options, run_as_admin=run_as_admin,
        run_as=run_as, become=become, created_by=created_by
    )

    changed = False
    if not adhoc or adhoc != new_adhoc:
        logger.debug("Adhoc changed")
        changed = True
    elif assets and set(assets) != set(adhoc.assets.all()):
        logger.debug("Assets changed")
        changed = True
    elif nodes and set(nodes) != set(adhoc.nodes.all()):
        logger.debug("Nodes changed")
        changed = True

    if changed:
        logger.debug("Task create new adhoc: {}".format(task_name))
        new_adhoc.save()
        if assets:
            new_adhoc.assets.set(assets)
        if nodes:
            new_adhoc.nodes.set(nodes)
        task.latest_adhoc = new_adhoc
        created = True
    return task, created



