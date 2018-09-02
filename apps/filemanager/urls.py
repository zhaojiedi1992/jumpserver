# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'filemanager'

urlpatterns = [
    path('model/<int:coll_id>/', views.ModelFileManagerView.as_view(), name='model-view'),
    path('model/connector/<int:coll_id>/', views.ModelVolumeConnectorView.as_view(), name='model-volume-connector'),
]
