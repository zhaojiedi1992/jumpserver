# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from common.const import create_success_msg, update_success_msg
from .. import forms
from ..models import Service
#from common.permissions import AdminUserRequiredMixin

__all__ = [
#    'AdminUserCreateView', 'AdminUserDetailView',
    #'AdminUserDeleteView', 'ServiceListView',
     'ServiceListView',
    #'AdminUserUpdateView', 'AdminUserAssetsView',
]


class ServiceListView(TemplateView):
    model = Service
    template_name = 'hwl/service_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('hwl'),
            'action': _('Service list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


