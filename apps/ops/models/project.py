# -*- coding: utf-8 -*-
#
import uuid

from django.utils.translation import ugettext_lazy as _
from django.db import models

from ..inventory import JMSInventory


class Project(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', verbose_name=_("Node"))
    description = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Description"))
    created_by = models.CharField(max_length=128, blank=True, null=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def inventory(self):
        inventory = JMSInventory(
            self.assets.all(), nodes=self.nodes.all(),
        )
        return inventory
