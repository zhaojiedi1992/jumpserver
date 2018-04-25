# ~*~ coding: utf-8 ~*~
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import Response

from common.permissions import IsSuperUser
from ..models import AdHocTask, AdHocContent, AdHocRunHistory
from ..serializers import AdHocTaskSerializer, AdHocContentSerializer, \
    AdHocRunHistorySerializer
from ..tasks import run_adhoc_task
from .base import LogTailApi


__all__ = [
    'AdHocTaskViewSet', 'AdHocTaskRunApi', 'AdHocContentViewSet',
    'AdHocRunHistoryViewSet', 'AdHocHistoryLogApi',
]


class AdHocTaskViewSet(viewsets.ModelViewSet):
    queryset = AdHocTask.objects.all()
    serializer_class = AdHocTaskSerializer
    permission_classes = (IsSuperUser,)


class AdHocTaskRunApi(generics.RetrieveAPIView):
    queryset = AdHocTask.objects.all()
    serializer_class = AdHocTaskSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        t = run_adhoc_task.delay(str(task.id))
        return Response({"task": t.id})


class AdHocContentViewSet(viewsets.ModelViewSet):
    queryset = AdHocContent.objects.all()
    serializer_class = AdHocContentSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        if task_id:
            task = get_object_or_404(AdHocTask, id=task_id)
            self.queryset = self.queryset.filter(task=task)
        return self.queryset


class AdHocRunHistoryViewSet(viewsets.ModelViewSet):
    queryset = AdHocRunHistory.objects.all()
    serializer_class = AdHocRunHistorySerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        content_id = self.request.query_params.get('content')

        if task_id:
            self.queryset = self.queryset.filter(task=task_id)

        if content_id:
            self.queryset = self.queryset.filter(content=content_id)
        return self.queryset


class AdHocHistoryLogApi(LogTailApi):
    queryset = AdHocRunHistory.objects.all()
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def get_log_path(self):
        return self.object.log_path

    def is_end(self):
        return self.object.is_finished
