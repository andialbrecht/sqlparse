from django.conf.urls.defaults import *

urlpatterns = patterns(
    'sqlformat.views',
    (r'^$', 'index'),
    (r'^source/$', 'source'),
    (r'^about/$', 'about'),
    (r'^api/$', 'api'),
    (r'^format/$', 'format'),
    (r'^load_example', 'load_example'),
)
