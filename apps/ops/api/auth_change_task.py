# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics
from rest_framework.views import Response

from common.permissions import IsSuperUser
from ..models import AuthChangeTask
from ..serializers import AdHocTaskSerializer
from ..tasks import run_auth_change_task

__all__ = ['AuthChangeTaskRunApi']


class AuthChangeTaskRunApi(generics.RetrieveAPIView):
    queryset = AuthChangeTask.objects.all()
    serializer_class = AdHocTaskSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        t = run_auth_change_task.delay(str(task.id))
        return Response({"task": t.id})
