# -*- coding: utf-8 -*-
#

import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.fields import JsonTextField, JsonCharField


class Job(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    pattern = models.CharField(max_length=1024, default='all',
                               verbose_name=_('Pattern'))
    run_as_admin = models.BooleanField(default=False,
                                       verbose_name=_('Run as admin'))
    run_as = models.ForeignKey('assets.SystemUser', null=True, blank=True,
                               verbose_name=_("Run as"))
    tasks = JsonTextField(verbose_name=_('Tasks'))
    vars = JsonTextField(verbose_name=_('Vars'), blank=True, null=True)
    options = JsonCharField(max_length=1024, blank=True, null=True,
                            verbose_name=_('Options'))
    interval = models.CharField(verbose_name=_("Interval"), null=True, blank=True,
                                max_length=128, help_text=_("s/m/d"))
    is_periodic = models.BooleanField(default=False, verbose_name=_("Enable"))
    crontab = models.CharField(verbose_name=_("Crontab"), null=True, blank=True,
                               max_length=128, help_text=_("5 * * * *"))
    created_by = models.CharField(max_length=128, blank=True, null=True,
                                  default='')
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    active = models.BooleanField(default=True, verbose_name=_("Active"))
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
