# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from common.mixins import DatetimeSearchMixin
from ..models import AuthChangeTask
from ..hands import AdminUserRequiredMixin
from ..forms import AuthChangeTaskCreateUpdateForm


__all__ = [
    'AuthChangeTaskListView', 'AuthChangeTaskDetailView',
    'AuthChangeTaskCreateView', 'AuthChangeTaskUpdateView',
]


class AuthChangeTaskListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    model = AuthChangeTask
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/auth_change_task_list.html'
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
        context = {
            'app': _('Ops'),
            'action': _('Auth change task list'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AuthChangeTaskCreateView(AdminUserRequiredMixin, CreateView):
    model = AuthChangeTask
    form_class = AuthChangeTaskCreateUpdateForm
    template_name = 'ops/auth_change_task_create_update.html'
    success_url = reverse_lazy('ops:auth-change-task-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Create auth change task'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AuthChangeTaskUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AuthChangeTask
    form_class = AuthChangeTaskCreateUpdateForm
    template_name = 'ops/auth_change_task_create_update.html'
    success_url = reverse_lazy('ops:auth-change-task-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Update auth change task'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AuthChangeTaskDetailView(AdminUserRequiredMixin, DetailView):
    model = AuthChangeTask
    template_name = 'ops/task_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)