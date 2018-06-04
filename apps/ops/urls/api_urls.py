# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "ops"

router = DefaultRouter()
router.register(r'v1/adhoc/tasks', api.AdHocTaskViewSet, 'adhoc-task')
router.register(r'v1/adhoc/contents', api.AdHocContentViewSet, 'adhoc-content')
router.register(r'v1/adhoc/history', api.AdHocRunHistoryViewSet, 'adhoc-history')
router.register(r'v1/projects', api.ProjectViewSet, 'project')

urlpatterns = [
    url(r'^v1/adhoc/tasks/(?P<pk>[0-9a-zA-Z\-]{36})/run/$', api.AdHocTaskRunApi.as_view(), name='adhoc-task-run'),
    url(r'^v1/adhoc/history/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.AdHocHistoryLogApi.as_view(), name='adhoc-history-log'),
    url(r'^v1/celery/tasks/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.CeleryLogApi.as_view(), name='celery-task-log'),
    url(r'^v1/auth-change/tasks/(?P<pk>[0-9a-zA-Z\-]{36})/run/$', api.AuthChangeTaskRunApi.as_view(), name='auth-change-task-run'),
]

urlpatterns += router.urls
