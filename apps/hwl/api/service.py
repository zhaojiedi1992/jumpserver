# ~*~ coding: utf-8 ~*~
# Copyright (C) 2014-2018 Beijing DuiZhan Technology Co.,Ltd. All Rights Reserved.
#
# Licensed under the GNU General Public License v2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.gnu.org/licenses/gpl-2.0.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from common.mixins import IDInFilterMixin
from common.utils import get_logger
#from ..hands import IsOrgAdmin
from ..models import Service
from .. import serializers
#from ..tasks import test_admin_user_connectability_manual


logger = get_logger(__file__)
__all__ = [
    'ServiceViewSet',
]


class ServiceViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    hwl service api set, for add,delete,update,list,retrieve resource
    """
    queryset = Service.objects.all()
    serializer_class = serializers.ServiceSerializer
    #permission_classes = (IsOrgAdmin,)


