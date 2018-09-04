# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'filemanager'

urlpatterns = [
    path('model/<int:coll_id>/', views.SFTPManagerView.as_view(), name='model-view'),
    path('model/connector/<int:coll_id>/', views.SFTPConnectorView.as_view(), name='model-volume-connector'),
]
