# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'filemanager'

urlpatterns = [
    path('common-sftp/', views.CommonSFTPView.as_view(), name='common-sftp-view'),
    path('sftp/<str:token>/', views.SFTPManagerView.as_view(), name='sftp-filermanager-view'),
    path('sftp/connector/<str:token>/', views.SFTPConnectorView.as_view(), name='sftp-connector'),
]
