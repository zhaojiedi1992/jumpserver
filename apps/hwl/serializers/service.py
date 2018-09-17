# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from rest_framework import serializers

from ..models import Service
#from ..const import ADMIN_USER_CONN_CACHE_KEY

#from .base import AuthSerializer


class ServiceSerializer(serializers.ModelSerializer):
    """
    管理用户
    """
    assets_amount = serializers.SerializerMethodField()
    unreachable_amount = serializers.SerializerMethodField()
    reachable_amount = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = '__all__'

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        return [f for f in fields if not f.startswith('_')]

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets_amount



