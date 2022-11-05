# Software developed by Pieter W.G. Bots for the PrESTO project
# Code repository: https://github.com/pwgbots/presto
# Project wiki: http://presto.tudelft.nl/wiki

"""
Copyright (c) 2022 Delft University of Technology

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^administrator$', views.administrator, name='administrator'),
    re_path(r'^ajax$', views.ajax, name='ajax'),
    re_path(r'^announcements$', views.announcements, name='announcements'),
    re_path(r'^awards$', views.awards, name='awards'),
    re_path(r'^badge/(?P<hex>[0-9a-f]{32})$', views.badge, name='badge'),
    re_path(r'^badge/(?P<tiny>tiny)/(?P<hex>[0-9a-f]{32})$', views.badge, name='badge'),
    re_path(r'^badge/sample/(?P<bc>[0-9]+)$', views.badge, name='badge'),
    re_path(r'^course/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.course, name='course'),
    re_path(r'^course/(?P<hex>[0-9a-f]{32})$', views.course, name='course'),
    re_path(r'^course-estafette/(?P<hex>[0-9a-f]{32})$', views.course_estafette, name='course_estafette'),
    re_path(r'^dataset/(?P<hex>[0-9a-f]{32})$', views.dataset, name='dataset'),
    re_path(r'^demo$', views.demo, name='demo'),
    re_path(r'^demo-login$', views.demo_login, name='demo_login'),
    re_path(r'^developer/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$',
        views.developer, name='developer'),
    re_path(r'^developer/(?P<action>[a-z\-]+)$', views.developer, name='developer'),
    re_path(r'^developer$', views.developer, name='developer'),
    re_path(r'^download/(?P<work>pre)/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$',
        views.download, name='download'),
    re_path(r'^download/(?P<dwnldr>ref)/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$',
        views.download, name='download'),
    re_path(r'^download/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$', views.download, name='download'),
    re_path(r'^enroll/(?P<course>[\w\-\s\(\)]+)$', views.enroll, name='enroll'),
    re_path(r'^estafette/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$',
        views.estafette_view, name='estafette_view'),
    re_path(r'^estafette/(?P<hex>[0-9a-f]{32})$', views.estafette_view, name='estafette_view'),
    re_path(r'^guest$', views.guest, name='guest'),
    re_path(r'^guest-login$', views.guest_login, name='guest_login'),
    re_path(r'^history/(?P<hex>[0-9a-f]{32})$', views.history_view, name='history_view'),
    re_path(r'^history$', views.history_view, name='history_view'),
    re_path(r'^instructor/(?P<action>[a-z\-]+)$', views.instructor, name='instructor'),
    re_path(r'^instructor$', views.instructor, name='instructor'),
    re_path(r'^loa/(?P<hex>[0-9a-f]{32})$', views.ack_letter, name='ack_letter'),
    re_path(r'^log/(?P<date>[0-9]{8})/(?P<lines>\-[0-9]+)$', views.log_file, name='log_file'),
    re_path(r'^log/(?P<date>[0-9]{8})/(?P<pattern>.{2,})$', views.log_file, name='log_file'),
    re_path(r'^log/(?P<date>[0-9]{8})$', views.log_file, name='log_file'),
    re_path(r'^log/(?P<lines>\-[0-9]+)$', views.log_file, name='log_file'),
    re_path(r'^log/(?P<pattern>.{2,})$', views.log_file, name='log_file'),
    re_path(r'^log$', views.log_file, name='log_file'),
    re_path(r'^lti/(?P<extra>[\w\-]+)$', views.lti_view, name='lti'),
    re_path(r'^lti$', views.lti_view, name='lti'),
    re_path(r'^pq/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$',
        views.picture_queue, name='picture_queue'),
    re_path(r'^pq/(?P<hex>[0-9a-f]{32})$', views.picture_queue, name='picture_queue'),
    re_path(r'^pq/(?P<action>[a-z\-]+)$', views.picture_queue, name='picture_queue'),
    re_path(r'^progress/(?P<p_or_ce>(p|ce))/(?P<hex>[0-9a-f]{32})$', views.progress, name='instructor'),
    re_path(r'^scan$', views.scan, name='scan'),
    re_path(r'^settings$', views.setting_view, name='setting_view'),
    re_path(r'^student/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.student, name='student'),
    re_path(r'^student$', views.student, name='student'),
    re_path(r'^suspect/(?P<hex>[0-9a-f]{32})$', views.suspect, name='suspect'),
    re_path(r'^test-file$', views.test_file_type, name='test_file_type'),
    re_path(r'^template/(?P<action>[a-z\-]+)/(?P<step>[0-9]+)/(?P<task>[a-z])/(?P<hex>[0-9a-f]{32})$',
        views.template, name='template'),
    re_path(r'^template/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.template, name='template'),
    re_path(r'^template/(?P<hex>[0-9a-f]{32})$', views.template, name='template'),
    re_path(r'^template/(?P<action>[a-z\-]+)$', views.template, name='template'),
    re_path(r'^verify$', views.verify, name='verify'),
    re_path(r'^verify/(?P<hex>[0-9a-f]{32})$', views.verify, name='verify'),
]
