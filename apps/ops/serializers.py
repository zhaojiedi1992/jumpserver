# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers

from .models import AnsibleTask, AdHoc, AdHocRunHistory


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnsibleTask
        fields = '__all__'


class AdHocSerializer(serializers.ModelSerializer):
    total_assets_count = serializers.SerializerMethodField()

    class Meta:
        model = AdHoc
        fields = '__all__'

    @staticmethod
    def get_total_assets_count(obj):
        return obj.total_assets_count

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['short_id'])
        return fields


class AdHocRunHistorySerializer(serializers.ModelSerializer):
    task = serializers.SerializerMethodField()
    adhoc_short_id = serializers.SerializerMethodField()
    stat = serializers.SerializerMethodField()

    class Meta:
        model = AdHocRunHistory
        exclude = ('result', 'summary')

    @staticmethod
    def get_adhoc_short_id(obj):
        return obj.adhoc.short_id

    @staticmethod
    def get_task(obj):
        return obj.adhoc.task.id

    @staticmethod
    def get_stat(obj):
        return {
            "total": len(obj.adhoc.total_assets),
            "success": len(obj.summary.get("contacted", [])) if obj.summary else 0,
            "failed": len(obj.summary.get("dark", [])) if obj.summary else 0,
        }

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['summary', 'short_id'])
        return fields
