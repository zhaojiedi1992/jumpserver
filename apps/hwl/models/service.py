# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from orgs.mixins import OrgModelMixin


class Service(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    desc = models.CharField(max_length=128,null=True, verbose_name=_("Desc"))

    def __str__(self):
        return "{}:{}".format(self.name, self.value)

    class Meta:
        db_table = "service"
#        unique_together = [('name', 'name' )]
