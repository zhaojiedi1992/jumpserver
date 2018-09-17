# coding:utf-8
from django.urls import path
from .. import views

app_name = 'hwl'

urlpatterns = [
    # Resource asset url
    path('', views.ServiceListView.as_view(), name='service-index'),
    path('hwl/', views.ServiceListView.as_view(), name='service-list'),
#    path('asset/create/', views.AssetCreateView.as_view(), name='asset-create'),
#    path('asset/export/', views.AssetExportView.as_view(), name='asset-export'),
#    path('asset/import/', views.BulkImportAssetView.as_view(), name='asset-import'),
#    path('asset/<uuid:pk>/', views.AssetDetailView.as_view(), name='asset-detail'),
#    path('asset/<uuid:pk>/update/', views.AssetUpdateView.as_view(), name='asset-update'),
#    path('asset/<uuid:pk>/delete/', views.AssetDeleteView.as_view(), name='asset-delete'),
#    path('asset/update/', views.AssetBulkUpdateView.as_view(), name='asset-bulk-update'),



]
