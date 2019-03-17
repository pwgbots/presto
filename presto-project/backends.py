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

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.conf import settings
from presto.models import Role

from djangosaml2.backends import Saml2Backend


class MySaml2Backend(Saml2Backend):
    def authenticate(self, request, session_info=None, attribute_mapping=None,
                     create_unknown_user=True, **kwargs):        
        

        user = super(MySaml2Backend, self).authenticate(request, session_info, attribute_mapping,
                     create_unknown_user, **kwargs) 

        is_employee = False
        eduPersonAffiliation = session_info['ava']['urn:mace:dir:attribute-def:eduPersonAffiliation']
        
        if eduPersonAffiliation is not None:
            is_employee = eduPersonAffiliation[0] == 'employee'        
                
        user.profile.is_employee = is_employee
        user.profile.save()
        
        # if no roles then assign one
        if user.profile.roles.count() == 0:
            # only employees can have instructor role
            if is_employee:
                user.profile.roles.add(Role.objects.get(name="Instructor"))
            # all users can have student role
            user.profile.roles.add(Role.objects.get(name="Student"))
            user.profile.save()

        return user