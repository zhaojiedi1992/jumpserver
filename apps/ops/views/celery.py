# -*- coding: utf-8 -*-
#
from django.shortcuts import reverse
from django.views.generic import TemplateView

from ..hands import AdminUserRequiredMixin
from .base import LogTailMixin


__all__ = ['CeleryTaskLogView']


class CeleryTaskLogView(AdminUserRequiredMixin, LogTailMixin, TemplateView):
    task_id = None

    def get(self, request, *args, **kwargs):
        self.task_id = kwargs.get('pk')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'url': reverse('api-ops:celery-task-log', kwargs={'pk': self.task_id})
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

