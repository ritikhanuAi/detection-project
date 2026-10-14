from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # REST APIs
    path('api/jobs/', include('apps.jobs.urls', namespace='jobs')),
    path('api/profiling/', include('apps.profiling.urls', namespace='profiling')),
    path('api/validation/', include('apps.validation.urls', namespace='validation')),

    # Frontend Web Views (Streamlined Nomenclature)
    path('', TemplateView.as_view(template_name='pages/home.html'), name='home'),
    path('video-analysis/', TemplateView.as_view(template_name='pages/video_analysis.html'), name='video_analysis'),
    path('json-analysis/', TemplateView.as_view(template_name='pages/json_analysis.html'), name='json_analysis'),

    # Compatibility Aliases
    path('dashboard/', TemplateView.as_view(template_name='pages/video_analysis.html'), name='dashboard'),
    path('stage1/', TemplateView.as_view(template_name='pages/video_analysis.html'), name='stage1'),
    path('stage2/', TemplateView.as_view(template_name='pages/json_analysis.html'), name='stage2'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
