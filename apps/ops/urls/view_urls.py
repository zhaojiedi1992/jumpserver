# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from .. import views

__all__ = ["urlpatterns"]

app_name = "ops"

urlpatterns = [
    url(r'^adhoc/$', views.AdHocTaskListView.as_view(), name='adhoc-task-list'),
    url(r'^adhoc/(?P<pk>[0-9a-zA-Z\-]{36})/$', views.AdHocTaskDetailView.as_view(), name='adhoc-task-detail'),
    url(r'^adhoc/(?P<pk>[0-9a-zA-Z\-]{36})/version/$', views.AdhocTaskContentListView.as_view(), name='adhoc-task-content-list'),
    url(r'^adhoc/(?P<pk>[0-9a-zA-Z\-]{36})/history/$', views.AdHocTaskHistoryListView.as_view(), name='adhoc-task-history-list'),
    url(r'^adhoc/version/(?P<pk>[0-9a-zA-Z\-]{36})/$', views.AdHocContentDetailView.as_view(), name='adhoc-content-detail'),
    url(r'^adhoc/version/(?P<pk>[0-9a-zA-Z\-]{36})/history/$', views.AdHocContentHistoryListView.as_view(), name='adhoc-content-history-list'),
    url(r'^adhoc/history/(?P<pk>[0-9a-zA-Z\-]{36})/$', views.AdHocHistoryDetailView.as_view(), name='adhoc-history-detail'),
    url(r'^adhoc/history/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', views.AdHocHistoryLogView.as_view(), name='adhoc-history-log'),

    url(r'^celery/task/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', views.CeleryTaskLogView.as_view(), name='celery-task-log'),

    url(r'^auth-change/$', views.AuthChangeTaskListView.as_view(), name='auth-change-task-list'),
    url(r'^auth-change/create/$', views.AuthChangeTaskCreateView.as_view(), name='auth-change-task-create'),
    url(r'^auth-change/(?P<pk>[0-9a-zA-Z\-]{36})/update/$', views.AuthChangeTaskUpdateView.as_view(), name='auth-change-task-update'),
    url(r'^auth-change/(?P<pk>[0-9a-zA-Z\-]{36})/$', views.AuthChangeTaskDetailView.as_view(), name='auth-change-task-detail'),
]
