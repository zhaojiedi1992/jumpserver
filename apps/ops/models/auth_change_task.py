# -*- coding: utf-8 -*-
#
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _


class AuthChangeTask(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=128, verbose_name=_("Username"))
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', verbose_name=_("Node"))
    interval = models.IntegerField(verbose_name=_("Interval"), default=45, help_text=_("Units: day"))
    crontab = models.CharField(verbose_name=_("Crontab"), blank=True, null=True, help_text="* * 4 * *")
    different = models.BooleanField(default=False, verbose_name=_("Different every asset"))
    comment = models.TextField(verbose_name=_("Comment"))
    created_by = models.CharField(max_length=128, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        instance = super().save(force_insert=force_insert, force_update=force_update,
                                using=using, update_fields=update_fields)
