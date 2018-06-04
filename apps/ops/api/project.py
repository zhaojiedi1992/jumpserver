# -*- coding: utf-8 -*-
#

from rest_framework.response import Response
from rest_framework import viewsets

from common.permissions import IsSuperUser
from ..serializers import ProjectSerializer
from ..models import Project


__all__ = ['ProjectViewSet']


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsSuperUser,)



