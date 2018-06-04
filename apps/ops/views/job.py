# -*- coding: utf-8 -*-
#
from django.views.generic import TemplateView, CreateView
from django.utils.translation import ugettext as _

from common.mixins import AdminUserRequiredMixin

from ..models import Job
from ..forms import JobCreateUpdateForm


__all__ = ['JobListView', 'JobDetailView', 'JobCreateView', 'JobUpdateView']


class JobListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/job_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Job list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class JobDetailView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/project_detail.html'


class JobCreateView(AdminUserRequiredMixin, CreateView):
    model = Job
    form_class = JobCreateUpdateForm
    template_name = 'ops/job_create_update.html'


class JobUpdateView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/project_detail.html'
