# ~*~ coding: utf-8 ~*~

import os
from collections import namedtuple

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.vars.manager import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.playbook.play import Play
import ansible.constants as C

from .callback import AdHocResultCallback, PlaybookResultCallBack, \
    CommandResultCallback
from common.utils import get_logger
from .exceptions import AnsibleError


__all__ = ["AdHocRunner", "PlayBookRunner"]
C.HOST_KEY_CHECKING = False
logger = get_logger(__name__)


Options = namedtuple('Options', [
    'verbosity', 'listhosts', 'subset', 'module_path', 'extra_vars',
    'forks', 'ask_vault_pass', 'vault_password_files', 'new_vault_password_files',
    'vault_ids', 'new_vault_id', 'tags', 'skip_tags', 'ask_pass', 'private_key_file',
    'remote_user', 'connection', 'timeout', 'ssh_common_args', 'sftp_extra_args',
    'scp_extra_args', 'ssh_extra_args', 'sudo', 'sudo_user', 'su', 'su_user',
    'become', 'become_method', 'become_user', 'ask_sudo_pass', 'ask_su_pass',
    'become_ask_pass', 'check', 'syntax', 'diff', 'force_handlers', 'flush_cache',
    'listtasks', 'listtags', 'step', 'start_at_task', 'passwords',
])


def get_default_options():
    options = Options(
        verbosity=0,
        listhosts=None,
        subset=None,
        module_path=None,
        extra_vars=[],
        forks=5,
        ask_vault_pass=False,
        vault_password_files=[],
        new_vault_password_files=[],
        vault_ids=[],
        new_vault_id=None,
        tags=['all'],
        skip_tags=[],
        ask_pass=False,
        private_key_file='',
        remote_user='root',
        connection='smart',
        timeout=10,
        ssh_common_args='',
        sftp_extra_args='',
        scp_extra_args='',
        ssh_extra_args='',
        sudo=False,
        sudo_user=None,
        su=False,
        su_user=None,
        become=False,
        become_method='sudo',
        become_user='root',
        ask_sudo_pass=False,
        ask_su_pass=False,
        become_ask_pass=False,
        check=False,
        syntax=None,
        diff=False,
        force_handlers=False,
        flush_cache=None,
        listtasks=None,
        listtags=None,
        step=None,
        start_at_task=None,
        passwords=None,
    )
    return options


# Jumpserver not use playbook
class PlayBookRunner:
    """
    用于执行AnsiblePlaybook的接口.简化Playbook对象的使用.
    """

    # Default results callback
    results_callback_class = PlaybookResultCallBack
    loader_class = DataLoader
    variable_manager_class = VariableManager
    options = get_default_options()

    def __init__(self, inventory=None, options=None):
        """
        :param options: Ansible options like ansible.cfg
        :param inventory: Ansible inventory
        """
        if options:
            self.options = options
        C.RETRY_FILES_ENABLED = False
        self.inventory = inventory
        self.loader = self.loader_class()
        self.results_callback = self.results_callback_class()
        self.playbook_path = options.playbook_path
        self.variable_manager = self.variable_manager_class(
            loader=self.loader, inventory=self.inventory
        )
        self.passwords = options.passwords
        self.__check()

    def __check(self):
        if self.options.playbook_path is None or \
                not os.path.exists(self.options.playbook_path):
            raise AnsibleError(
                "Not Found the playbook file: {}.".format(self.options.playbook_path)
            )
        if not self.inventory.list_hosts('all'):
            raise AnsibleError('Inventory is empty')

    def run(self):
        executor = PlaybookExecutor(
            playbooks=[self.playbook_path],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords
        )

        if executor._tqm:
            executor._tqm._stdout_callback = self.results_callback
        executor.run()
        executor._tqm.cleanup()
        return self.results_callback.output


class AdHocRunner:
    """
    ADHoc Runner接口
    """
    results_callback_class = AdHocResultCallback
    results_callback = None
    loader_class = DataLoader
    variable_manager_class = VariableManager
    default_options = get_default_options()
    options = None

    def __init__(self, inventory, options=None):
        self.options = self.get_options(options)
        self.inventory = inventory
        self.loader = DataLoader()
        self.variable_manager = VariableManager(
            loader=self.loader, inventory=self.inventory
        )

    def get_result_callback(self):
        return self.results_callback_class()

    @staticmethod
    def check_module_args(module_name, module_args=''):
        if module_name in C.MODULE_REQUIRE_ARGS and not module_args:
            err = "No argument passed to '%s' module." % module_name
            raise AnsibleError(err)

    def check_pattern(self, pattern):
        if not pattern:
            raise AnsibleError("Pattern `{}` is not valid!".format(pattern))
        if not self.inventory.list_hosts("all"):
            raise AnsibleError("Inventory is empty.")
        if not self.inventory.list_hosts(pattern):
            raise AnsibleError(
                "pattern: %s  dose not match any hosts." % pattern
            )

    def clean_tasks(self, tasks):
        cleaned_tasks = []
        for task in tasks:
            self.check_module_args(task['action']['module'], task['action'].get('args'))
            cleaned_tasks.append(task)
        return cleaned_tasks

    def get_options(self, options):
        _options = self.default_options
        if options and isinstance(options, dict):
            _options = _options._replace(**options)
        return _options

    def update_options(self, options):
        if options and isinstance(options, dict):
            self.options = self.options._replace(**options)

    def run(self, tasks, pattern, play_name='Ansible Ad-hoc', gather_facts='no'):
        """
        :param tasks: [{'action': {'module': 'shell', 'args': 'ls'}, ...}, ]
        :param pattern: all, *, or others
        :param play_name: The play name
        :param gather_facts:
        :return:
        """
        self.check_pattern(pattern)
        self.results_callback = self.get_result_callback()
        cleaned_tasks = self.clean_tasks(tasks)

        play_source = dict(
            name=play_name,
            hosts=pattern,
            gather_facts=gather_facts,
            tasks=cleaned_tasks
        )

        play = Play().load(
            play_source,
            variable_manager=self.variable_manager,
            loader=self.loader,
        )

        tqm = TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            stdout_callback=self.results_callback,
            passwords=self.options.passwords,
        )
        print("Get matched hosts: {}".format(
            self.inventory.get_matched_hosts(pattern)
        ))

        try:
            tqm.run(play)
            return self.results_callback
        except Exception as e:
            raise AnsibleError(e)
        finally:
            tqm.cleanup()
            self.loader.cleanup_all_tmp_files()


class CommandRunner(AdHocRunner):
    results_callback_class = CommandResultCallback
    modules_choices = ('shell', 'raw', 'command', 'script')

    def execute(self, cmd, pattern, module=None):
        if module and module not in self.modules_choices:
            raise AnsibleError("Module should in {}".format(self.modules_choices))
        else:
            module = "shell"

        tasks = [
            {"action": {"module": module, "args": cmd}}
        ]
        hosts = self.inventory.get_hosts(pattern=pattern)
        name = "Run command {} on {}".format(cmd, ", ".join([host.name for host in hosts]))
        return self.run(tasks, pattern, play_name=name)

