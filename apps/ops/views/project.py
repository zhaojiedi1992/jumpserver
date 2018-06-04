# -*- coding: utf-8 -*-
#
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

from common.mixins import AdminUserRequiredMixin
from ..models import Project


__all__ = ['ProjectListView', 'ProjectDetailView']


class ProjectListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/project_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Project list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ProjectDetailView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/project_detail.html'
