from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework import routers, permissions
from TaskManagerApp import views, viewsets

schema_view = get_schema_view(
   openapi.Info(
      title="TaskManager API",
      default_version='v1',
      description="Authentication/Add/Remove/Task Assigned per user",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="t-yotov@teamyotov.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'customers', viewsets.CustomerViewSet)
router.register(r'projects', viewsets.ProjectViewSet)
router.register(r'tasks', viewsets.TaskViewSet)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^docs/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('auth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('google/auth/', views.GoogleLoginApi.as_view()),
    path('change/password/', views.ChangePassword.as_view()),
    path('reset/password/', views.ResetPassword.as_view()),
    path('reset/change/password/', views.ResetChangePassword.as_view()),
    path('verify/email/', views.VerifyEmail.as_view())
]
