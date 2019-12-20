from django.urls import path, include

from .tables import urls as table_urls
from .views import urls as view_urls

app_name = 'baserow.contrib.database.api.v0'

urlpatterns = [
    path('tables/', include(table_urls, namespace='tables')),
    path('views/', include(view_urls, namespace='views')),
]
