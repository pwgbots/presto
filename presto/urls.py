# Software developed by Pieter W.G. Bots for the PrESTO project
# Code repository: https://github.com/pwgbots/presto
# Project wiki: http://presto.tudelft.nl/wiki

"""
Copyright (c) 2019 Delft University of Technology

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


# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^administrator$', views.administrator, name='administrator'),
    url(r'^ajax$', views.ajax, name='ajax'),
    url(r'^announcements$', views.announcements, name='announcements'),
    url(r'^awards$', views.awards, name='awards'),
    url(r'^badge/(?P<hex>[0-9a-f]{32})$', views.badge, name='badge'),
    url(r'^badge/(?P<tiny>tiny)/(?P<hex>[0-9a-f]{32})$', views.badge, name='badge'),
    url(r'^badge/sample/(?P<bc>[0-9]+)$', views.badge, name='badge'),
    url(r'^course/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.course, name='course'),
    url(r'^course/(?P<hex>[0-9a-f]{32})$', views.course, name='course'),
    url(r'^course-estafette/(?P<hex>[0-9a-f]{32})$', views.course_estafette, name='course_estafette'),
    url(r'^dataset/(?P<hex>[0-9a-f]{32})$', views.dataset, name='dataset'),
    url(r'^demo$', views.demo, name='demo'),
    url(r'^demo-login$', views.demo_login, name='demo_login'),
    url(r'^developer/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.developer, name='developer'),
    url(r'^developer/(?P<action>[a-z\-]+)$', views.developer, name='developer'),
    url(r'^developer$', views.developer, name='developer'),
    url(r'^download/(?P<work>pre)/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$', views.download, name='download'),
    url(r'^download/(?P<dwnldr>ref)/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$', views.download, name='download'),
    url(r'^download/(?P<file_name>[\w\-]+)/(?P<hex>[0-9a-f]{32})$', views.download, name='download'),
    url(r'^enroll/(?P<course>[\w\-\s\(\)]+)$', views.enroll, name='enroll'),
    url(r'^estafette/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.estafette_view, name='estafette_view'),
    url(r'^estafette/(?P<hex>[0-9a-f]{32})$', views.estafette_view, name='estafette_view'),
    url(r'^history/(?P<hex>[0-9a-f]{32})$', views.history_view, name='history_view'),
    url(r'^history$', views.history_view, name='history_view'),
    url(r'^instructor/(?P<action>[a-z\-]+)$', views.instructor, name='instructor'),
    url(r'^instructor$', views.instructor, name='instructor'),
    url(r'^loa/(?P<hex>[0-9a-f]{32})$', views.ack_letter, name='ack_letter'),
    url(r'^log/(?P<date>[0-9]{8})/(?P<lines>\-[0-9]+)$', views.log_file, name='log_file'),
    url(r'^log/(?P<date>[0-9]{8})/(?P<pattern>.{2,})$', views.log_file, name='log_file'),
    url(r'^log/(?P<date>[0-9]{8})$', views.log_file, name='log_file'),
    url(r'^log/(?P<lines>\-[0-9]+)$', views.log_file, name='log_file'),
    url(r'^log/(?P<pattern>.{2,})$', views.log_file, name='log_file'),
    url(r'^log$', views.log_file, name='log_file'),
    url(r'^pq/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.picture_queue, name='picture_queue'),
    url(r'^pq/(?P<hex>[0-9a-f]{32})$', views.picture_queue, name='picture_queue'),
    url(r'^pq/(?P<action>[a-z\-]+)$', views.picture_queue, name='picture_queue'),
    url(r'^progress/(?P<p_or_ce>(p|ce))/(?P<hex>[0-9a-f]{32})$', views.progress, name='instructor'),
    url(r'^scan$', views.scan, name='scan'),
    url(r'^settings$', views.setting_view, name='setting_view'),
    url(r'^student/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.student, name='student'),
    url(r'^student$', views.student, name='student'),
    url(r'^suspect/(?P<hex>[0-9a-f]{32})$', views.suspect, name='suspect'),
    url(r'^test-file$', views.test_file_type, name='test_file_type'),
    url(r'^template/(?P<action>[a-z\-]+)/(?P<hex>[0-9a-f]{32})$', views.template, name='template'),
    url(r'^template/(?P<hex>[0-9a-f]{32})$', views.template, name='template'),
    url(r'^template/(?P<action>[a-z\-]+)$', views.template, name='template'),
    url(r'^verify$', views.verify, name='verify'),
    url(r'^verify/(?P<hex>[0-9a-f]{32})$', views.verify, name='verify'),
]