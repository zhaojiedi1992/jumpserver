# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "ops"

router = DefaultRouter()
router.register(r'v1/tasks', api.AdHocTaskViewSet, 'task')
router.register(r'v1/adhoc', api.AdHocContentViewSet, 'adhoc')
router.register(r'v1/history', api.AdHocRunHistoryViewSet, 'history')

urlpatterns = [
    url(r'^v1/tasks/(?P<pk>[0-9a-zA-Z\-]{36})/run/$', api.AdHocTaskRunApi.as_view(), name='task-run'),
    url(r'^v1/celery/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.CeleryLogApi.as_view(), name='celery-task-log'),
    url(r'^v1/adhoc/history/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.AdHocHistoryLogApi.as_view(), name='adhoc-history-log'),
]

urlpatterns += router.urls
