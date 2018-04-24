# ~*~ coding: utf-8 ~*~
import uuid
import os

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import viewsets, generics
from rest_framework.views import Response

from .hands import IsSuperUser
from .models import AdHocTask, AdHocContent, AdHocRunHistory
from .serializers import AdHocTaskSerializer, AdHocContentSerializer, \
    AdHocRunHistorySerializer
from .tasks import run_adhoc_task
from .celery.utils import get_log_path


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


class LogTailApi(generics.RetrieveAPIView):
    permission_classes = (IsSuperUser,)
    buff_size = 1024 * 10
    end = False

    def is_end(self):
        return False

    def get_log_path(self):
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        mark = request.query_params.get("mark") or str(uuid.uuid4())
        log_path = self.get_log_path()

        if not log_path or not os.path.isfile(log_path):
            if self.is_end():
                return Response({"data": 'Not found the log', 'end': self.is_end(), 'mark': mark})
            else:
                return Response({"data": _("Waiting ...\n")}, status=200)

        with open(log_path, 'r') as f:
            offset = cache.get(mark, 0)
            f.seek(offset)
            data = f.read(self.buff_size).replace('\n', '\r\n')
            mark = str(uuid.uuid4())
            cache.set(mark, f.tell(), 5)

            if data == '' and self.is_end():
                self.end = True
            return Response({"data": data, 'end': self.end, 'mark': mark})


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


class CeleryLogApi(LogTailApi):
    task_id = None

    def get(self, request, *args, **kwargs):
        self.task_id = kwargs.get('pk')
        return super().get(request, *args, **kwargs)

    def get_log_path(self):
        return get_log_path(self.task_id)

    def is_end(self):
        ret = cache.get(self.task_id)
        if not ret:
            return True
        if ret.children:
            for i in ret.children:
                if not i.ready():
                    return False
            return True
        return ret.ready()
