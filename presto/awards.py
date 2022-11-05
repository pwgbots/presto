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

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import render

from .models import (
    Appeal, Assignment,
    Course,
    DEFAULT_DATE,
    EstafetteLeg,
    Participant, PeerReview, PrestoBadge,
    Referee,
    LetterOfAcknowledgement
)

# presto modules
from presto.badge import participant_badge_image, referee_badge_image
from presto.generic import generic_context, warn_user, inform_user
from presto.utils import encode, decode, log_message

# python modules
import poplib

@login_required(login_url=settings.LOGIN_URL)
def awards(request):
    context = generic_context(request)

    # check awardable achievements, and create/update badges if appropriate

    # (1) get participant badges issued so far
    b_list = PrestoBadge.objects.filter(participant__isnull=False
        ).filter(participant__student__user=context['user']).distinct()
    badge_dict = {}
    for b in b_list:
        # get the badge relevant properties as a dict
        d = b.as_dict()
        # and add to this dict the badge object and its ID hex code
        d['object'] = b
        d['hex'] = encode(b.id, context['user_session'].encoder)
        badge_dict[b.id] = d 

    # (2) get user's finished steps in relays that issue badges
    # NOTE: no badges for instructor participants (dummy index must be 0)
    p_list = Participant.objects.filter(student__user=context['user'],
        student__dummy_index=0, estafette__with_badges=True)
    # ignore "clone" assignments, as only their original represents the actual work
    # NOTE: this also prevents rewards for a "selfie" review
    a_list = Assignment.objects.filter(participant__in=p_list,
        time_uploaded__gt=DEFAULT_DATE, clone_of__isnull=True)
    r_list = PeerReview.objects.filter(assignment__in=a_list,
        time_submitted__gt=DEFAULT_DATE, grade__gt=2).distinct()

    # (3) create badges for those steps not already rewarded
    for r in r_list:
        # NOTE: only consider reviews of assignments that have an uploaded successor,
        #       or are final reviews, or are instructor reviews
        if (r.reviewer.student.dummy_index < 0
            or r.final_review_index > 0
            or (r.assignment.successor != None
                and r.assignment.successor.time_uploaded != DEFAULT_DATE)):
            # badge must match participant and level
            if not lookup_badge(badge_dict, r.assignment.leg.number, r.assignment.participant):
                b = PrestoBadge.objects.create(course = r.assignment.participant.student.course,
                    participant = r.assignment.participant, referee = None,
                    levels = r.assignment.leg.template.nr_of_legs(),
                    attained_level = r.assignment.leg.number)
                d = b.as_dict()
                d['object'] = b
                d['hex'] = encode(b.id, context['user_session'].encoder)
                badge_dict[b.id] = d

    # (4) get referee decisions that revised the user's grade to 3+ stars
    r_list = PeerReview.objects.filter(assignment__in=a_list, is_appeal=True,
        time_appeal_assigned__gt=DEFAULT_DATE).distinct()
    a_list = Appeal.objects.filter(review__in=r_list,
        time_decided__gt=DEFAULT_DATE, grade__gt=2).distinct()

    # (5) create badges for those steps not already rewarded
    for a in a_list:
        ara = a.review.assignment
        # badge must match participant and level
        if not lookup_badge(badge_dict, ara.leg.number, ara.participant):
            b = PrestoBadge.objects.create(course = ara.participant.student.course,
                participant = ara.participant, referee = None,
                levels = ara.leg.template.nr_of_legs(),
                attained_level = ara.leg.number)
            d = b.as_dict()
            d['object'] = b
            d['hex'] = encode(b.id, context['user_session'].encoder)
            badge_dict[b.id] = d

    # (6) add list of entries to context, sorted by template name and then levels attained
    context['participant_badges'] = badge_dict.values()
    context['participant_badges'].sort(cmp=compare_badge_info)

    # (7) get referee badges issued so far
    # NOTE: referee badges are awarded only upon passing a referee exam, hence not created here
    ref_badge_dict = {}
    for b in PrestoBadge.objects.filter(referee__isnull=False).filter(referee__user=context['user']):
        d = b.as_dict()
        d['object'] = b
        d['hex'] = encode(b.id, context['user_session'].encoder)
        ref_badge_dict[b.referee.id] = d

    # add list of entries to context, sorted by template name and then levels attained
    context['referee_badges'] = ref_badge_dict.values()
    context['referee_badges'].sort(cmp=compare_badge_info)

    # get referee LoA's issued so far (with ID encoded as hex)
    l_dict = {}
    # first add participant LoA's
    # NOTE: keys prefixed by P to distinguish participant IDs from referee IDs
    for l in LetterOfAcknowledgement.objects.filter(
        participant__student__user=context['user']
        ):
        l_dict['P' + l.participant.id] = {
            'object': l,
            'hex': encode(l.id, context['user_session'].encoder)
            }
    # NOTE: referee LoA's have their estafette ID as key
    for l in LetterOfAcknowledgement.objects.filter(
        referee__user=context['user']
        ):
        l_dict[l.estafette.id] = {
            'object': l,
            'hex': encode(l.id, context['user_session'].encoder)
            }

    # get the user's referee object instances (created upon passing a referee exam)
    r_list = Referee.objects.filter(user=context['user'])

    # get decided appeal cases, and tally them (1) per course estafette (2) per leg
    re_dict = {}
    a_list = Appeal.objects.filter(referee__in=r_list, time_decided__gt=DEFAULT_DATE)

    # NOTE: to qualify for a referee letter of acknowledgement, referees must have
    #       made at least 1 appeal decision (so re_dict remains empty if a_list is empty)
    for a in a_list:
        e = a.review.assignment.participant.estafette
        l = a.review.assignment.leg.number
        # update step count if estafette already has an entry ...
        if e.id in re_dict:
            if l in re_dict[e.id]:
                re_dict[e.id][l] += 1
            else:
                re_dict[e.id][l] = 1
            re_dict[e.id]['first'] = min(re_dict[e.id]['first'], a.time_decided)
            re_dict[e.id]['last'] = max(re_dict[e.id]['last'], a.time_decided)
        # ... or create a new entry
        else:
            re_dict[e.id] = {
                'ce': e,
                'ref': a.referee,
                'first': a.time_decided,
                'last': a.time_decided,
                'sum': 0,
                'cnt': 0,
                l: 1
                }
        # collect statistics on appraisal of the decisions (by default, assume neutral: 2)
        if a.predecessor_appraisal > 0:
            re_dict[e.id]['sum'] += a.predecessor_appraisal
        else:
            re_dict[e.id]['sum'] += 2
        if a.successor_appraisal > 0:
            re_dict[e.id]['sum'] += a.successor_appraisal
        else:
            re_dict[e.id]['sum'] += 2
        re_dict[e.id]['cnt'] += 2

    # re_dict now contains all "entitlements" for referee LoA's
    for e in re_dict.keys():
        # count refereed steps while making a list of refereed step numbers
        ns = re_dict[e]['ce'].estafette.template.nr_of_legs()
        acc = 0
        rs = []
        for i in range(1, ns + 1):
            if i in re_dict[e]:
                rs.append(i)
                acc += re_dict[e][i]
        # format this as a nice phrase, e.g. "steps 1, 2 and 4 (of 4)"
        if ns == 1:
            steps = 'the single step'
        elif len(rs) == 1:
            steps = 'step {} (of {})'.format(rs[0], ns)
        elif len(rs) == ns:
            steps = 'all {} steps'.format(ns)
        else:
            steps = 'steps {} and {} (of {})'.format(
                ', '.join([str(s) for s in rs[:-1]]),
                rs[-1],
                ns
                )
        # compute the average appreciation on a scale from -1 to 1
        appr = 0
        # print('count=' + re_dict[e]['cnt'])
        # print('sum=' + re_dict[e]['sum'])
        if re_dict[e]['cnt'] > 0:
            appr = re_dict[e]['sum'] / float(re_dict[e]['cnt']) - 2  # subtract 2 because frown = 1 and smile = 3
        if e in l_dict:
            # upgrade letter if needed
            changed = False
            l = l_dict[e]['object']
            if l.appeal_case_count != acc:
                l.appeal_case_count = acc
                l.extra_hours = acc * re_dict[e]['ce'].estafette.hours_per_appeal
                l.time_first_case = re_dict[e]['first']
                l.time_last_case = re_dict[e]['last']
                changed = True
            if l.average_appreciation != appr:
                l.average_appreciation = appr
                changed = True
            if changed:
                l.save()
        else:
            # create new letter if user has indeed decided on one or more appeal cases
            l = LetterOfAcknowledgement.objects.create(
                estafette = re_dict[e]['ce'],
                referee = re_dict[e]['ref'],
                step_list = steps,
                time_first_case = re_dict[e]['first'],
                time_last_case = re_dict[e]['last'],
                appeal_case_count = acc,
                extra_hours = acc * re_dict[e]['ce'].estafette.hours_per_appeal,
                average_appreciation = appr)
            l_dict[e] = {'object': l, 'hex': encode(l.id, context['user_session'].encoder)}

    context['letters'] = l_dict

    context['page_title'] = 'Presto Awards' 
    return render(request, 'presto/awards.html', context)


# lookup function to see whether a *participant* badge with attained level l
# and participant p has been issued
def lookup_badge(b_dict, l, p):
    for k, b in b_dict.iteritems():
        if b['AL'] == l and b['PID'] == p.id and not b.get('RID', False):
            return True
    return False


# compare function for sorting lists of dicts with badge info
def compare_badge_info(x, y):
    # sort on (1) course code, (2) project relay (template name), (3) attained level, (4) time issued
    # NOTE: tilde is used as separator because it has the highest ASCII code 
    nx = '~'.join([x['CC'].lower(), x['PR'].lower(), str(x['AL']), x['TI']])
    ny = '~'.join([y['CC'].lower(), y['PR'].lower(), str(y['AL']), y['TI']])
    if nx < ny:
        return -1
    if nx > ny:
        return 1
    return 0
