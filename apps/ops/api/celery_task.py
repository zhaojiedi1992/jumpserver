# -*- coding: utf-8 -*-
#
from celery.result import AsyncResult

from .base import LogTailApi
from ..celery.utils import get_log_path

__all__ = ['CeleryLogApi']


class CeleryLogApi(LogTailApi):
    task_id = None

    def get(self, request, *args, **kwargs):
        self.task_id = kwargs.get('pk')
        return super().get(request, *args, **kwargs)

    def get_log_path(self):
        return get_log_path(self.task_id)

    def is_end(self):
        ret = AsyncResult(self.task_id)
        if ret.ready():
            return True
        return False
