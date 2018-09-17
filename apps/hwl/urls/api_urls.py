# coding:utf-8
from django.urls import path
from .. import api
from rest_framework_bulk.routes import BulkRouter

app_name = 'hwl'

#router = BulkRouter()
#router.register(r'hwl', api.ServiceViewSet, 'hwl')

#urlpatterns = [
#    path('assets-bulk/', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
#]

#urlpatterns += router.urls

