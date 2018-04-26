# -*- coding: utf-8 -*-
#

from django.shortcuts import reverse
from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, DetailView
from celery.result import AsyncResult

from common.mixins import DatetimeSearchMixin
from ..models import AdHocTask, AdHocContent, AdHocRunHistory
from ..hands import AdminUserRequiredMixin
from .base import LogTailMixin


__all__ = [
    'AdHocTaskListView', 'AdHocTaskDetailView',
    'AdhocTaskContentListView', 'AdHocContentDetailView',
    'AdHocContentHistoryListView',
    'AdHocTaskHistoryListView', 'AdHocHistoryLogView', 'AdHocHistoryDetailView',
]


class AdHocTaskListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    model = AdHocTask
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/adhoc_task_list.html'
    keyword = ''

    def get_queryset(self):
        self.queryset = super().get_queryset()
        self.keyword = self.request.GET.get('keyword', '')
        self.queryset = self.queryset.filter(
            date_created__gt=self.date_from,
            date_created__lt=self.date_to
        )

        if self.keyword:
            self.queryset = self.queryset.filter(
                name__icontains=self.keyword,
            )
        return self.queryset

    def get_context_data(self, **kwargs):
        res = AsyncResult("180821e7-5190-4d64-97af-6d18f48bb20b")
        context = {
            'app': _('Ops'),
            'action': _('AdHoc task list'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'keyword': self.keyword,
            'task': {"task": res.id, "state": res.state}
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocTaskDetailView(AdminUserRequiredMixin, DetailView):
    model = AdHocTask
    template_name = 'ops/adhoc_task_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdhocTaskContentListView(AdminUserRequiredMixin, DetailView):
    model = AdHocTask
    template_name = 'ops/adhoc_task_content_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task versions'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocTaskHistoryListView(AdminUserRequiredMixin, DetailView):
    model = AdHocTask
    template_name = 'ops/adhoc_task_history_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocContentDetailView(AdminUserRequiredMixin, DetailView):
    model = AdHocContent
    template_name = 'ops/adhoc_content_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': 'Task version detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocContentHistoryListView(AdminUserRequiredMixin, DetailView):
    model = AdHocContent
    template_name = 'ops/adhoc_content_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Version run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryDetailView(AdminUserRequiredMixin, DetailView):
    model = AdHocRunHistory
    template_name = 'ops/adhoc_history_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Run history detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryLogView(AdminUserRequiredMixin, LogTailMixin, DetailView):
    model = AdHocRunHistory

    def get_context_data(self, **kwargs):
        context = {
            'url': reverse('api-ops:adhoc-history-log', kwargs={'pk': self.object.id})
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
