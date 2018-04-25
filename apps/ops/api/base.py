# -*- coding: utf-8 -*-
#
import uuid
import os

from django.core.cache import cache
from django.utils.translation import ugettext as _
from rest_framework import generics
from rest_framework.views import Response

from common.permissions import IsSuperUser


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
