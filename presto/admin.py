"""
Software developed by Pieter W.G. Bots for the PrESTO project
Code repository: https://github.com/pwgbots/presto
Project wiki: http://presto.tudelft.nl/wiki

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

from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

# Register your models here.

from django.contrib.auth import get_user_model
User = get_user_model()

from .models import (
    Appeal, Assignment,
    CaseUpload, Course, CourseEstafette, CourseStudent,
    Estafette, EstafetteCase, EstafetteLeg, EstafetteTemplate,
    Item, ItemReview,
    Language, LegVideo, LetterOfAcknowledgement,
    Objection,
    Participant, ParticipantUpload, PeerReview, PrestoBadge, Profile,
    QueuePicture, QuestionnaireTemplate,
    Referee, RefereeExam, Role,
    UserDownload, UserSession
)

class AppealAdmin(admin.ModelAdmin):
    raw_id_fields = ('referee', 'review')
        
class AssignmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('successor', 'predecessor', 'clone_of', 'participant')
    
class ItemReviewAdmin(admin.ModelAdmin):
    raw_id_fields = ['review']
        
class PeerReviewAdmin(admin.ModelAdmin):
    raw_id_fields = ('assignment', 'reviewer')
    
class ParticipantAdmin(admin.ModelAdmin):
    raw_id_fields = ['student']

class ParticipantUploadAdmin(admin.ModelAdmin):
    raw_id_fields = ['assignment']

class UserDownloadAdmin(admin.ModelAdmin):
    raw_id_fields = ['assignment']


admin.site.register(Appeal, AppealAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(CaseUpload)
admin.site.register(Course)
admin.site.register(CourseEstafette)
admin.site.register(CourseStudent)
admin.site.register(Estafette)
admin.site.register(EstafetteCase)
admin.site.register(EstafetteLeg)
admin.site.register(EstafetteTemplate)
admin.site.register(Item)
admin.site.register(ItemReview, ItemReviewAdmin)
admin.site.register(Language)
admin.site.register(LegVideo)
admin.site.register(LetterOfAcknowledgement)
admin.site.register(Objection)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(ParticipantUpload, ParticipantUploadAdmin)
admin.site.register(PeerReview, PeerReviewAdmin)
admin.site.register(PrestoBadge)
admin.site.register(Profile)
admin.site.register(QueuePicture)
admin.site.register(QuestionnaireTemplate)
admin.site.register(Referee)
admin.site.register(RefereeExam)
admin.site.register(Role)
admin.site.register(UserSession)
admin.site.register(UserDownload, UserDownloadAdmin)

from django.conf import settings
if settings.USE_SAML is True:
    admin.site.register(User, UserAdmin)
    admin.site.register(Group, GroupAdmin)

