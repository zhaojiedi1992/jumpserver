# -*- coding: utf-8 -*-
#
import os
from django.conf import settings

CELERY_LOG_DIR = os.path.join(settings.PROJECT_DIR, 'data', 'celery')
