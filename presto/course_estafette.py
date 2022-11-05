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

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import connection
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Appeal,
    Assignment, 
    Course,
    CourseEstafette,
    CourseStudent,
    DEFAULT_DATE,
    Estafette,
    EstafetteCase,
    EstafetteLeg,
    EstafetteTemplate,
    ItemReview,
    Objection,
    Participant,
    PeerReview,
    QuestionnaireTemplate,
    Referee,
    SHORT_DATE_TIME,
    UserSession
)

# python modules
from datetime import datetime, timedelta
from hashlib import md5
from json import dumps, loads
from math import floor
import os

# presto modules
from presto.generic import (
    change_role,
    generic_context,
    has_role,
    inform_user,
    report_error,
    warn_user
    )
from presto.plag_scan import step_status
from presto.teams import (
    current_team,
    team_assignments,
    team_as_html,
    team_final_reviews,
    team_leaders_added_to_relay,
    team_lookup_dict
    )
from presto.utils import (
    DATE_FORMAT,
    DATE_TIME_FORMAT,
    decode,
    encode,
    FACES,
    GRACE_MINUTE,
    log_message,
    prefixed_user_name,
    signed_half_points,
    string_to_datetime
    )

INSTRUCTOR_SUFFIX = ' (instructor)'

UPDATE_2019 = timezone.make_aware(datetime.strptime('2019-11-01 00:00', SHORT_DATE_TIME))

ICON_COLORS = ['', 'red', 'orange', 'yellow', 'olive', 'green']

# Initialize dictionaries for storing participants, assignments, reviews, and
# appeals (as *global* variables) in memory to minimize database access.
p_dict = {}
a_dict = {}
r_dict = {}
ob_dict = {}
ap_dict = {}

# likewise, make the "halfway the estafette periode" time global
half_way = DEFAULT_DATE

# also make the course estafette parameters global
speed_bonus = 0
bonus_per_step = False
bonus_deadline_dict = {}
scoring_system = 0  # default: differential scoring
nr_of_legs = 0
case_letters = []

# and finally also the object-to-be-instantiated for collecting statistics
stats = None


# auxiliary function that aggregates star or score count matrix to vector with averages
def matrix_to_vector(m):
    if len(m) == 0:
        return None
    # None indicates "no average due to count = 0"
    v = [None for row in m]
    r = 0
    for row in m:
        s = 0
        n = 0
        for col in range(len(row)):
            n += row[col]
            s += row[col] * col # col being the number of stars (0-5) or the appraisal (0-3)
        if n > 0:
            # NOTE: forcing s to floating point to avoid integer division
            v[r] = float(s) / n
        r += 1
    return v


# auxiliary class for collecting statistics
class EstafetteStatistics(object):

    def __init__(self):
        # collect overall statistics
        self.count = 0
        self.selfies = 0
        self.clones = 0
        self.hours_till_submit = 0
        self.hours_till_grade = 0
        self.hours_till_appraisal = 0
        self.hours_till_judgement = 0
        self.submitted = 0
        self.graded = 0
        # matrix for tallying the frequency of (stars given, stars received)
        self.stars = [[0 for g in range(6)] for r in range(6)]
        self.scores = [0 for g in range(6)]
        self.gg_count = [0 for g in range(6)]
        # matrix for tallying the frequency of (stars received, appraisal)
        # NOTE: appraisal scores are 0 = none, 1 = smile, 2 = meh, 3 = frown, 4 = appeal)
        self.appraisals = [[0 for a in range(5)] for r in range(6)]
        self.rejected = 0
        self.appraised = 0
        self.appealed = 0
        self.judged = 0
        self.sustained = 0
        self.predecessor_penalties = 0
        self.successor_penalties = 0
        self.bonuses = 0
        # collect statistics per leg
        self.legs = []
        global nr_of_legs
        for l in range(nr_of_legs):
            self.legs.append({
                'count': 0,
                'selfies': 0,
                'clones': 0,
                'hours_till_submit': 0,
                'hours_till_grade': 0,
                'hours_till_appraisal': 0,
                'hours_till_judgement': 0,
                'submitted': 0,
                'graded': 0,
                # matrix for tallying the frequency of (stars given, stars received)
                'stars': [[0 for g in range(6)] for r in range(6)],
                'scores': [0 for g in range(6)],
                'gg_count': [0 for g in range(6)],
                # matrix for tallying the frequency of (stars received, appraisal)
                'appraisals': [[0 for a in range(5)] for r in range(6)],
                'rejected': 0,
                'appraised': 0,
                'appealed': 0,
                'judged': 0,
                'sustained': 0,
                'predecessor_penalties': 0,
                'successor_penalties': 0,
                'bonuses': 0
            })
        # likewise, collect statistics per case
        self.cases = {}
        for l in case_letters:
            self.cases[l] = {
                'count': 0,
                'selfies': 0,
                'clones': 0,
                'hours_till_submit': 0,
                'hours_till_grade': 0,
                'hours_till_appraisal': 0,
                'hours_till_judgement': 0,
                'submitted': 0,
                'graded': 0,
                # matrix for tallying the frequency of (stars given, stars received)
                'stars': [[0 for g in range(6)] for r in range(6)] ,
                'scores': [0 for g in range(6)],
                'gg_count': [0 for g in range(6)],
                # matrix for tallying the frequency of (stars received, appraisal)
                'appraisals': [[0 for a in range(5)] for r in range(6)],
                'rejected': 0,
                'appraised': 0,
                'appealed': 0,
                'judged': 0,
                'sustained': 0,
                'predecessor_penalties': 0,
                'successor_penalties': 0,
                'bonuses': 0
            }

    # add a data point (one per participant step)
    def data_point(self, step):
        l = self.legs[step.number - 1]
        c = self.cases[step.letter]
        # update primary tallies
        self.count += 1
        l['count'] += 1
        c['count'] += 1
        if step.self_review:
            self.selfies += 1
            l['selfies'] += 1
            c['selfies'] += 1
        if step.clone:
            self.clones += 1
            l['clones'] += 1
            c['clones'] += 1
        # no further statistics unless assignment was uploaded
        ut = step.assignment['time_uploaded']
        if ut == DEFAULT_DATE:
            return
        self.submitted += 1
        l['submitted'] += 1
        c['submitted'] += 1
        h = (ut - step.assignment['time_assigned']).total_seconds() / 3600
        self.hours_till_submit += h
        l['hours_till_submit'] += h
        c['hours_till_submit'] += h
        # no further statistics unless assignment was reviewed & graded
        if not step.received_reviews:
            return
        # no review => step 1 => "given grade" = 0 (so stars received are absolute points)
        if step.given_review:
            gg = step.given_review['grade']
        else:
            gg = 0
        for review in step.received_reviews:
            rt = review['time_submitted']
            # only consider submitted reviews
            if rt == DEFAULT_DATE:
                continue
            self.graded += 1
            l['graded'] += 1
            c['graded'] += 1
            rg = review['grade'] 
            self.stars[gg][rg] += 1
            l['stars'][gg][rg] += 1
            c['stars'][gg][rg] += 1
            # cumulate total score and score count per given grade
            self.scores[gg] += step.score
            l['scores'][gg] += step.score
            c['scores'][gg] += step.score
            self.gg_count[gg] += 1
            l['gg_count'][gg] += 1
            c['gg_count'][gg] += 1
            if review['is_rejection']:
                self.rejected += 1
                l['rejected'] += 1
                c['rejected'] += 1
            h = (rt - ut).total_seconds() / 3600
            self.hours_till_grade += h
            l['hours_till_grade'] += h
            c['hours_till_grade'] += h
            # no further statistics unless participant responded to review & grade
            at = review['time_appraised']
            if at == DEFAULT_DATE:
                continue
            self.appraised += 1
            l['appraised'] += 1
            c['appraised'] += 1
            h = (at - rt).total_seconds() / 3600
            self.hours_till_appraisal += h
            l['hours_till_appraisal'] += h
            c['hours_till_appraisal'] += h
            # collect separate statistics on "appeal" and "frown" by replacing 3 by 4 for appeals
            appeal = review['appeal']
            if appeal:
                appr = 4
            else:
                appr = review['appraisal']
            # link appraisal to received stars, not their eventual point score  
            self.appraisals[rg][appr] += 1
            l['appraisals'][rg][appr] += 1
            c['appraisals'][rg][appr] += 1
            # no further statistics unless participant appealed
            if not appeal:
                continue
            self.appealed += 1
            l['appealed'] += 1
            c['appealed'] += 1
            # no further statistics unless appeal has been decided
            if appeal['time_decided'] == DEFAULT_DATE:
                continue
            self.judged += 1
            l['judged'] += 1
            c['judged'] += 1
            h = (appeal['time_decided'] - at).total_seconds() / 3600
            self.hours_till_judgement += h
            l['hours_till_judgement'] += h
            c['hours_till_judgement'] += h
            # consider an appeal "sustained" only if the referee grade is higher than the reviewer's
            if appeal['grade'] > review['grade']:
                self.sustained += 1
                l['sustained'] += 1
                c['sustained'] += 1
            # NOTE: negative penalty points indicate bonus points
            bp = 0
            pp = appeal['predecessor_penalty']
            if pp < 0:
                bp -= pp
            else:
                self.predecessor_penalties += pp
                l['predecessor_penalties'] += pp
                c['predecessor_penalties'] += pp
            pp = appeal['successor_penalty']
            if pp < 0:
                bp -= pp
            else:
                self.successor_penalties += pp
                l['successor_penalties'] += pp
                c['successor_penalties'] += pp
            if bp > 0:
                self.bonuses += bp
                l['bonuses'] += bp
                c['bonuses'] += bp
        # end of FOR loop over reviews

    # compute averages by dividing totals by corresponding count
    def compute_averages(self):
        # averages reated to submitted assignments (if any)
        if self.submitted == 0:
            return
        self.avg_hours_till_submit = self.hours_till_submit / self.submitted
        global nr_of_legs
        for i in range(nr_of_legs):
            l = self.legs[i]
            if l['submitted'] == 0:
                continue
            l['avg_hours_till_submit'] = l['hours_till_submit'] / l['submitted']
        for l in case_letters:
            c = self.cases[l]
            if c['submitted'] == 0:
                continue
            c['avg_hours_till_submit'] = c['hours_till_submit'] / c['submitted']
        # averages reated to graded assignments (if any)
        if self.graded == 0:
            return
        self.avg_hours_till_grade = self.hours_till_grade / self.graded
        self.avg_stars = matrix_to_vector(self.stars)
        for i in range(6):
            if self.gg_count[i] == 0:
                self.scores[i] = None
            else:
                self.scores[i] /= self.gg_count[i]
        for i in range(nr_of_legs):
            l = self.legs[i]
            if l['graded'] == 0:
                continue
            l['avg_hours_till_grade'] = l['hours_till_grade'] / l['graded']
            l['avg_stars'] = matrix_to_vector(l['stars'])
            for i in range(6):
                if l['gg_count'][i] == 0:
                    l['scores'][i] = None
                else:
                    l['scores'][i] /= l['gg_count'][i]
        for l in case_letters:
            c = self.cases[l]
            if c['graded'] == 0:
                continue
            c['avg_hours_till_grade'] = c['hours_till_grade'] / c['graded']
            c['avg_stars'] = matrix_to_vector(c['stars'])
            for i in range(6):
                if c['gg_count'][i] == 0:
                    c['scores'][i] = None
                else:
                    c['scores'][i] /= c['gg_count'][i]
        # averages reated to appraised reviews (if any)
        if self.appraised == 0:
            return
        self.avg_hours_till_appraisal = self.hours_till_appraisal / self.appraised
        self.avg_appraisal = matrix_to_vector(self.appraisals)
        for i in range(nr_of_legs):
            l = self.legs[i]
            if l['appraised'] == 0:
                continue
            l['avg_hours_till_appraisal'] = l['hours_till_appraisal'] / l['appraised']
            l['avg_appraisal'] = matrix_to_vector(l['appraisals'])
        for l in case_letters:
            c = self.cases[l]
            if c['appraised'] == 0:
                continue
            c['avg_hours_till_appraisal'] = c['hours_till_appraisal'] / c['appraised']
            c['avg_appraisal'] = matrix_to_vector(c['appraisals'])
        # averages reated to decided appeals (if any)
        if self.judged == 0:
            return
        self.avg_hours_till_judgement = self.hours_till_judgement / self.judged
        self.avg_sustained = float(self.sustained) / self.judged
        self.avg_predecessor_penalty = self.predecessor_penalties / self.judged
        self.avg_successor_penalty = self.successor_penalties / self.judged
        self.avg_bonus = self.bonuses / self.judged
        for i in range(nr_of_legs):
            l = self.legs[i]
            if l['judged'] == 0:
                continue
            l['avg_hours_till_judgement'] = l['hours_till_judgement'] / l['judged']
            l['avg_sustained'] = float(l['sustained']) / l['judged']
            l['avg_predecessor_penalty'] = l['predecessor_penalties'] / l['judged']
            l['avg_successor_penalty'] = l['successor_penalties'] / l['judged']
            l['avg_bonus'] = l['bonuses'] / l['judged']
        for l in case_letters:
            c = self.cases[l]
            if c['judged'] == 0:
                continue
            c['avg_hours_till_judgement'] = c['hours_till_judgement'] / c['judged']
            c['avg_sustained'] = float(c['sustained']) / c['judged']
            c['avg_predecessor_penalty'] = c['predecessor_penalties'] / c['judged']
            c['avg_successor_penalty'] = c['successor_penalties'] / c['judged']
            c['avg_bonus'] = c['bonuses'] / c['judged']


# auxiliary class that groups all info on the steps of a participant (incl. final reviews)
class Step(object):

    def __init__(self, a):
        self.assignment = a
        self.letter = a['case__letter']
        self.number = a['leg__number']
        self.predecessor = None
        # hedge against key errors that may occur due to manual changes to database
        try:
            if a['predecessor__id']:
                self.predecessor = p_dict[a_dict[a['predecessor__id']]['participant__id']]
        except:
            pass
        self.given_review = None
        self.received_reviews = []
        self.expected_reviews = [1]  # by default, expect one review per step
        self.self_review = False
        self.clone = False
        self.rejection = False
        self.hasty_work = ''
        if a['time_scanned'] == DEFAULT_DATE:
            self.scan_status = step_status(self.number)  # will denote "undetermined"
        else:
            self.scan_status = step_status(self.number, a['scan_result'])
        self.score = 0
        self.score_details = ''
        self.rejection_penalties = 0
        self.rejection_penalty_details = ''

    def set_attributes(self, log_statistics):
        """
        Calculate participant sub-score for this step.
        """
        # Initialize default values.
        self.score = 0
        self.score_details = ''
        ggr = 0
        ggr_pw = 0
        rgr = 0
        rgr_pw = 0
        gpp = 0
        gppd = ''
        rpp = 0
        rppd = ''
        xp = 0
        xpd = ''
        # Then do the real work.
        if self.assignment['successor__id']:
            self.successor = p_dict[a_dict[
                self.assignment['successor__id']
                ]['participant__id']]
        if self.given_review:
            r = self.given_review
            a = a_dict[r['assignment__id']]
            self.predecessor = p_dict[a['participant__id']]
            self.clone = a['clone_of'] != None
            self.self_review = a_dict[r['assignment__id']]['is_selfie']
            self.rejection = self.assignment['is_rejected']
            ggr = r['grade']
            # NOTE: separate grade for predecessor's work need not be given.
            ggr_pw = r.get('grade_pw', 0)
            # If the review was appealed, the actual grade may have
            # been set by a referee.
            if r['appeal']:
                ap = r['appeal']
                if ap['time_decided'] != DEFAULT_DATE:

                    # temporary solution for storing two grades in the `grade` field
                    x, ggr = divmod(ap['grade'], 256)
                    if x > 0:
                        ggr_pw = x
                    # so ggr = original grade, ggr_pw grade for prior work

                    # For incurred appeals, the participant is the successor.
                    gpp = ap['successor_penalty']
                    # Objection may override appeal decision. 
                    ob = ob_dict.get(ap['id'], None)
                    if ob and ob['time_decided'] != DEFAULT_DATE:
                        # temporary solution for storing two grades in the `grade` field
                        x, ggr = divmod(ob['grade'], 256)
                        if x > 0:
                            ggr_pw = x
                        gpp = ob['successor_penalty']
                    # Only display penalty points if non-zero.
                    # NOTE: Negative value indicates bonus points.
                    if gpp != 0:
                        # Add suffix "p" for "penalty".
                        gppd = signed_half_points(-gpp) + 'p'
        # Keep track of most critical review in case of multiple reviews.
        mcr = None
        if self.received_reviews:
            # For all but the final step, this means that no further
            # reviews are expected.
            self.expected_reviews = []
            # If multiple reviews, the lowest counts, or the instructor's.
            rgr = 10  # <-- NOTE: initial value 10 used in test further down.
            rgr_pw = 10 # Likewise treat grade for improved predecessor work.
            rpp = 0
            rppd = ''
            for r in self.received_reviews:
                g = r['grade']
                g_pw = r.get('grade_pw', 0)
                # If instructor review, this grade is binding, so
                # ignore appeals by breaking out of the loop.
                if r['by_instructor']:
                    rgr = g
                    rgr_pw = g_pw
                    mcr = r
                    break
                # If the review was appealed, the actual grade may have
                # been set by a referee.
                if r['appeal']:
                    # NOTE: Do NOT overwrite previous appeal unless this
                    # appeal has been decided.
                    if r['appeal']['time_decided'] != DEFAULT_DATE:
                        ap = r['appeal']
                        x, g = divmod(ap['grade'], 256)
                        if x:
                            g_pw = x
                        ppp = ap['predecessor_penalty']
                        # Objection may override appeal decision. 
                        ob = ob_dict.get(ap['id'], None)
                        if ob and ob['time_decided'] != DEFAULT_DATE:
                            x, g = divmod(ob['grade'], 256)
                            if x:
                                g_pw = x
                            ppp = ob['predecessor_penalty']
                        # For made appeals, the participant is the predecessor.
                        rpp += ppp
                        # Only display penalty points if non-zero.
                        # (NOTE: negative indicates bonus)
                        if rpp != 0:
                            rppd += signed_half_points(-rpp) + 'p'
                        # Referee / instructor decision is binding
                        rgr = g
                        rgr_pw = g_pw
                        mcr = r
                        break
                # Update most critical review
                if g > 0 and (g < rgr or (g == rgr and g_pw > 0 and g_pw < rgr_pw)):
                    mcr = r
                    # Prevent overwriting by undefined grade (0).
                    if g > 0:
                        rgr = min(g, rgr)
                    if g_pw > 0:
                        rgr_pw = min(g_pw, rgr_pw)
            # NOTE: rgr still 10? Then received review was not submitted.
            if rgr == 10:
                # no points if not submitted yet.
                rgr = 0
                rgr_pw = 0
                mcr = None
            # Calculate bonus/malus points for maintaining (good/bad) rating.
            # NOTE: this does not apply in the new 2020 scoring system
            if scoring_system != 2 and ggr == rgr and rgr != 0:
                xp = 0.5 * (ggr - 3)
                if xp != 0:
                    # Letter 'c' denotes "maintained Constant level".
                    xpd = signed_half_points(xp) + 'c'
        if self.number == 1:
            # in ALL scoring systems, first step score equals received grade.
            self.score = rgr - rpp
            self.score_details = '{}{}'.format(rgr, rppd)
        elif self.given_review:
            if scoring_system == 1:
                # NOTE: in scoring system #1 ("MOOC style"), received grades
                # are "absolute"; improvement gives bonus; no malus.
                if rgr > ggr:
                    xp = rgr - ggr
                    xpd = '+{}i'.format(xp)
                else:
                    xp = 0
                    xpd = ''
                self.score = rgr + xp - rpp - gpp
                self.score_details = '{}{}{}{}'.format(rgr, xpd, gppd, rppd)
            elif scoring_system == 2:
                # NOTE: in scoring system #2 ("2020 style"), participants
                # give and receive 2 grades per step (Own and Previous), and
                # their score is calculated as received O+P minus given O,
                # or for Step 3 and beyond: minus given (O+P)/2.
                if ggr_pw > 0:
                    impr = rgr_pw - 0.5*(ggr + ggr_pw)
                    # Also graded predecessor's improved work (so Step 3 or beyond).
                    self.score = rgr + impr - gpp - rpp
                    self.score_details = '{}+{}-&frac12;({}+{}){}{}'.format(
                        rgr, rgr_pw, ggr, ggr_pw, gppd, rppd
                        )
                elif ggr > 0:
                    # Predecessor, but no grade for improved work (so Step 2),
                    # then only one grade given, so do not divide by 2.
                    impr = rgr_pw - ggr
                    self.score = rgr + impr - gpp - rpp
                    self.score_details = '{}+{}-{}{}{}'.format(
                        rgr, rgr_pw, ggr, gppd, rppd
                        )
                else:
                    impr = 0
                    self.score = rgr - rpp - gpp
                    self.score_details = '{}{}{}'.format(rgr, gppd, rppd)
                # Indicate improvement (if any) by superscript + or - after case letter.
                if mcr:
                    # Indicate improvement relative to most critical review.
                    if impr > 0:
                        mcr['improvement'] = '&#8314;'
                    elif impr < 0:
                        mcr['improvement'] = '&#8315;'
            else:
                # By default, use differential scoring method.
                self.score = rgr - ggr + xp - rpp - gpp
                self.score_details = '{}-{}{}{}{}'.format(
                    rgr, ggr, xpd, gppd, rppd
                    )
        # In all scoring methods, rejection penalties can occur
        #if self.rejection_penalties > 0:
        #    log_message('Successor penalty for rejection: ' + self.rejection_penalty_details)
        self.score -= self.rejection_penalties
        self.score_details += self.rejection_penalty_details
        # collect statistics on this step (only for individuals and team leaders)
        global stats
        if log_statistics:
            stats.data_point(self)


# groups data on progress of a participant (to minimize database lookups)
class ParticipantProgress(object):

    def __init__(self, p, un, n, h):
        self.participant = p
        # by default, not a referee
        self.referee = False
        self.appeals = 0
        # by default, not member of a team (empty string)
        self.team = ''
        self.is_leader = False
        self.separated = False
        # add dummy index to username (to differentiate between dummy students)
        if n[-1:] == ')':
            un += '(' + n.split('# ')[-1]
        self.username = un  # user name is needed only when downloading grades
        self.name = n
        self.instructor = (INSTRUCTOR_SUFFIX in n)
        # add the session-encoded database id (to be used for transactions)
        self.encoded_id = h
        # also add a code that can be used as anchor ID in HTML without disclosing database keys
        self.hexed_id = md5(hex(p.id).encode('ascii', 'ignore')).hexdigest()
        # for dummy participants, add their course student PIN
        if p.student.dummy_index > 0 and p.student.user.username == settings.DEMO_USER_NAME:
            self.pin = p.student.pin()
        # format the participant's last action time
        self.last_action = timezone.localtime(p.time_last_action).strftime(DATE_TIME_FORMAT)
        # initialize list attributes
        self.steps = []
        self.given_final_reviews = []
        self.progress = 0
        self.progress_color = ''
        self.rblanks = []
        self.gblanks = []
        self.scan_status = ''
        self.rejects = []

    def add_step(self, a):
        # cloned assignments and rejected assignments do not constitute a step for the participant
        if a['is_rejected']:
            # Show number of previous step, as that is the work that was rejected
            rap_data = str(a['leg__number'] - 1) + a['case__letter']
            rap = None
            if a['predecessor__id']:
                rap = p_dict.get(a_dict[a['predecessor__id']]['participant__id'], None)
            if rap:
                rap_data += ' (' + rap.name + ')'
            else:
                rap_data += ' (???)'
            # The `rejects` string is shown as pop-up balloon on the dashboard
            self.rejects.append(rap_data)
        elif not a['clone_of']:
            self.steps.append(Step(a))

    def did_upload_step(self, nr):
        if len(self.steps) >= nr:
            dtu = self.steps[nr - 1].assignment['time_uploaded']
            if dtu > DEFAULT_DATE:
                return timezone.localtime(dtu).strftime(SHORT_DATE_TIME)
        return 'not uploaded yet'

    def gave_review(self, r):
        # NOTE: "double checking" patch to cope with (erroneously!) assigned reviews
        #       that relate to work in ANOTHER course relay
        if r['assignment__id'] not in a_dict.keys():
            return
         # Add display attributes to review.
        a = a_dict[r['assignment__id']]
        r['letter'] = a['case__letter']
        r['improvement'] = ''
        r['reviewer_hex'] = self.hexed_id
        p = p_dict[a['participant__id']]
        r['receiver_hex'] = p.hexed_id
        if r['time_submitted'] == DEFAULT_DATE:
            dt = 'not submitted yet'
        elif r['is_rejection'] or r['final_review_index'] > 0:
            dt = timezone.localtime(r['time_submitted']).strftime(SHORT_DATE_TIME)
        else:
            dt = self.did_upload_step(a['leg__number'] + 1)
        r['reviewer_popup'] = '{} ({})'.format(
            p_dict[r['reviewer__id']].name,
            dt
            )
        r['clone'] = a['clone_of'] != None
        if r['clone']:
            c = a_dict[a['clone_of']]
            p = p_dict[c['participant__id']]
            r['receiver_popup'] = 'clone {} ({})'.format(p.name, dt)
            r['receiver_hex'] = p.hexed_id
        else:
            r['receiver_popup'] = '{} ({})'.format(p.name, dt)
        r['self_review'] = a_dict[r['assignment__id']]['is_selfie']
        # Assume that review has not been appealed.
        r['appeal'] = None
        if r['improper_language']:
            # Add warning sign and language scan status.
            r['receiver_popup'] += ' &#9888; ' + r['improper_language']
            r['shadow'] = '; box-shadow: 0px 0px 3px 3px #0000a0 inset'
        else:
            r['shadow'] = ''
        if r['is_rejection']:
            r['color'] = 'black'
        else:
            # color should reflect the given grade
            r['color'] = ICON_COLORS[r['grade']]
        r['icon'] = FACES[r['appraisal']]
        if r['time_appraised'] == DEFAULT_DATE:
            r['icon_color'] = 'inverted grey'
            r['status'] = 'not appraised yet'
        else:
            dt = timezone.localtime(r['time_appraised']).strftime(SHORT_DATE_TIME)
            if r['is_appeal']:
                r['icon'] = FACES[4]
                r['icon_color'] = 'inverted grey'
                status = 'appealed'
            else:
                r['icon_color'] = 'black' 
                status = 'appraised'
            r['status'] = '{} ({})'.format(status, dt)
        if r['final_review_index'] > 0:
            self.given_final_reviews.append(r)
        # ignore second opinions, instructor reviews, and also rejections, as these imply
        # that new work must be reviewed
        elif not (r['is_second_opinion'] or r['by_instructor'] or r['is_rejection']):
            # NOTE: steps is a zero-based list => leg number of reviewed assignment is step index 
            self.steps[r['assignment__leg__number']].given_review = r

    def received_review(self, r):
        # NOTE: protect with TRY to be robust against errors due to manual database updates
        try:
            if r['final_review_index'] > 0:
                self.steps[r['assignment__leg__number'] - 1].received_reviews.append(r)
            # ignore reviews of this participant's cloned assignments
            elif not r['assignment__clone_of']:
                # NOTE: received review is associated with the assignment's leg number,
                # and since steps is a zero-based list, the correct index is this number minus 1
                self.steps[r['assignment__leg__number'] - 1].received_reviews.append(r)
        except:
            pass

    def is_appealed(self, ap):
        r = r_dict[ap['review__id']]
        r['appeal'] = ap
        if r['time_appeal_assigned'] != DEFAULT_DATE:
            ref = ap['referee'] + ', '
        else:
            ref = ''
        # add the appeal icon, color and status fields to the review dictionary entry
        if ap['time_decided'] != DEFAULT_DATE:
            x, grade = divmod(ap['grade'], 256)
            pp = ap['predecessor_penalty']
            sp = ap['successor_penalty']
            dt = ap['time_decided']
            r['icon'] = ''
            if ap['is_contested_by_predecessor'] or ap['is_contested_by_successor']:
                r['objection'] = True
                r['icon'] = 'small circular ' 
                # if not assigned to instructor yet, draw light gray circle around small hand icon
                r['pending'] = '#c0c0c0'
                # objection may override appeal decision 
                ob = ob_dict.get(ap['id'], None)
                if ob:
                    ref = ob['referee'] + '&rarr;' + ref
                    if ob['time_decided'] != DEFAULT_DATE:
                        x, grade = divmod(ob['grade'], 256)
                        pp = ob['predecessor_penalty']
                        sp = ob['successor_penalty']
                        dt = ob['time_decided']
                        r['icon'] += 'inverted '
                        r['pending'] = ''
                    else:
                        # assigned to instructor => draw dark gray circle around small hand icon
                        r['pending'] = '#606060'
            # NOTE: for a rejected assignment, the successor penalty must be
            # recorded separately, as it will not appear in the successor's
            # review list
            if sp > 0 and r['is_rejection']:
                log_message('Successor penalty for rejection: ' + self.name)
                swar = self.steps[r['assignment__leg__number']]
                swar.rejection_penalties += sp
                swar.rejection_penalty_details += signed_half_points(-sp) + 'R'
                # check for team members, as these should also incur the penalty
                pteam = current_team(self.participant)
                for tp in pteam:
                    if tp != self.participant:
                        # find the team partner participant
                        tpp = p_dict[tp.id]
                        swar = tpp.steps[r['assignment__leg__number']]
                        swar.rejection_penalties += sp
                        swar.rejection_penalty_details += signed_half_points(-sp) + 'R'
            # icon reflects type of referee decision
            if pp == 0 and sp == 0:
                r['icon'] += FACES[8]
                status = 'no penalties'
            elif pp == sp:
                r['icon'] += FACES[5]
                status = signed_half_points(-pp) + ' to both'
            else:
                if pp > sp:
                    r['icon'] += FACES[6]
                else:
                    r['icon'] += FACES[7]
                if pp == 0:
                    status =  signed_half_points(-sp) + ' for successor'
                elif sp == 0:
                    status = signed_half_points(-pp) + ' for predecessor'
                else:
                    status = 'mixed: {} / {}'.format(
                        signed_half_points(-pp),
                        signed_half_points(-sp)
                        )
            # color reflects grade decided by referee
            r['icon_color'] = ICON_COLORS[grade]                
        elif ap['time_first_viewed']:
            r['icon'] = FACES[4]
            r['icon_color'] = 'black'
            status = 'case opened'
            dt = ap['time_first_viewed']
        elif r['time_appeal_assigned'] != DEFAULT_DATE:
            r['icon'] = FACES[4]
            r['icon_color'] = 'grey'
            status = 'case assigned'
            dt = r['time_appeal_assigned']
        else:
            r['icon'] = FACES[4]
            r['icon_color'] = 'inverted grey'
            status = 'appealed'
            dt = r['time_appraised']
        r['status'] = '{} ({}{})'.format(
            status,
            ref,
            timezone.localtime(dt).strftime(SHORT_DATE_TIME)
            )

    def set_attributes(self, nr, legs, final_reviews):
        # NOTE: nr is participant number (used in HTML view to enumerate the table rows)
        self.nr = nr
        log_stats = not self.team or (self.is_leader and not self.separated) 
        # set the attributes for each of the steps this participant has made so far
        for s in self.steps:
            s.set_attributes(log_stats)
            if s.number == legs:
                s.expected_reviews = range(0, final_reviews - len(s.received_reviews))
        # The progress attribute expresses the participant's advancement as a
        # percentage (100% = done).
        # The score attribute calculates the participant's total number of
        # "relay points".
        # Zero progress indicates: not started, i.e., not yet accepted the
        # "rules of the game".
        p = 0  
        self.score = 0
        self.completed_steps = 0
        # bonus is scored if step was uploaded "early" (explained below)
        bonus = 0
        self.score_details = ''
        gr_count = 0 # count number of given reviews (ignoring rejections) to later calculate blanks
        for s in self.steps:
            p += 1  # getting an assignment is one step forward
            if s.assignment['time_uploaded'] != DEFAULT_DATE:
                p += 1  # uploading it is a second step forward
                self.completed_steps += 1 # count this assignment as a completed step
            if s.given_review:
                p += 1  # starting with a review is also a step forward
                if not s.given_review['is_rejection']:
                    gr_count += 1  # started-but-not-yet-submitted reviews already show up in overview
                if s.given_review['time_submitted'] != DEFAULT_DATE:
                    p += 1   # submitting it is a second step forward
            self.score += s.score
            if s.assignment['time_uploaded'] != DEFAULT_DATE:
                # (1) calculate how much time the participant used for this step 
                taken_time = s.assignment['time_uploaded'] - s.assignment['time_assigned']
                # set the "hasty work" flag if the time spent is less than twice (!) the minimum time
                if taken_time.total_seconds() < 2 * 60 * s.assignment['leg__min_upload_minutes']:
                    s.hasty_work = '; box-shadow: 0px 0px 3px 3px #ffffff inset'
                if speed_bonus > 0:
                    if bonus_per_step:
                        # NOTE: until 1-11-2019, speed bonus deadlines were individually computed
                        if self.participant.estafette.end_time < UPDATE_2019:
                            # award absolute bonus if step was uploaded within good time, i.e.,
                            # (2) calculate time between time assigned and assignments deadline MINUS 24 hrs
                            remaining_time = bonus_deadline - s.assignment['time_assigned']
                            # (3) calculate nominal time as remaining time / remaining steps
                            nominal_time = remaining_time / (legs - s.number + 1)
                            # (4) award bonus only if user used less than nominal time to upload
                            if taken_time <= nominal_time:
                                bonus += speed_bonus
                        else:
                            # since then, speed bonus deadlines are fixed for each relay
                            # NOTE: speed bonus deadlines are computed as global variable to save time
                            if (s.assignment['time_uploaded'] <=
                                bonus_deadline_dict.get(s.number, DEFAULT_DATE) + GRACE_MINUTE):
                                bonus += speed_bonus
    
                    elif s.assignment['time_uploaded'] <= half_way:
                        # relative bonus (score multiplier!) for each assignment uploaded before half of the duration
                        bonus += speed_bonus * s.score
            self.scan_status += s.scan_status

        # compile score details in a single string
        self.score_details = ' + '.join([s.score_details for s in self.steps])
        if speed_bonus:
            if bonus:
                bonus = round(2*bonus + 0.25) / 2  # round in favor of student to nearest half point
                self.score += bonus
                self.score_details += ' ' + signed_half_points(bonus) + 's'  # 's' for speed
        # given final reviews can also affect score (extra points and penalties)
        xp = 0
        xpd = ''
        pp = 0
        ppd = ''
        gfr = 0
        for r in self.given_final_reviews:
            # NOTE: skip if review was not submitted!
            if r['time_submitted'] != DEFAULT_DATE:
                # count this review as "given"
                gfr += 1
                g = r['grade']
                referee_grade = False
                # if the review was appealed, the actual grade may have been set by a referee
                if r['appeal']:
                    ap = r['appeal']
                    if ap['time_decided'] != DEFAULT_DATE:
                        # NOTE: if lost appeal or grade modified by referee, no bonus
                        referee_grade = (g != ap['grade'] or ap['successor_penalty'] > 0)
                        g = ap['grade']
                        # for incurred appeals, the participant is the successor
                        pp += ap['successor_penalty']
                        # only display penalty points if non-zero (NOTE: negative indicates bonus)
                        if pp != 0:
                            ppd += signed_half_points(-ap['successor_penalty']) + 'p'
                # if own review is not overruled, see if same assignment has received other reviews
                if not referee_grade:
                    # find the participant who submitted the reviewed assignment
                    op = p_dict[a_dict[r['assignment__id']]['participant__id']]
                    # make a list of all SUBMITTED final reviews received by this participant
                    orr = []
                    for rr in op.steps[legs - 1].received_reviews:
                        if rr['time_submitted'] != DEFAULT_DATE:
                            orr.append(rr)
                    if len(orr) > 0:
                        # prepare to find the lowest rating of this assignment
                        low_g = g
                        # assume no referee grade
                        referee_grade = False
                        bonus = 0.5  # half point if all others gave the same rating
                        # iterate through the reviews received for this final step
                        for rr in orr:
                            og = rr['grade']
                            # correct other reviewer's rating if the review was appealed
                            if rr['appeal']:
                                if rr['appeal']['time_decided'] != DEFAULT_DATE:
                                    og = rr['appeal']['grade']
                                    referee_grade = og
                            # compare the ratings to obtain the lowest
                            if og > g:
                                bonus = 1  # full point if at least one other gave higher rating
                            else:
                                low_g = og
                        # bonus is earned by being the most critical reviewer, or concurring with the referee
                        if (referee_grade and g == referee_grade) or (not referee_grade and g == low_g):
                            xp += bonus
                            xpd += signed_half_points(bonus) + 'r'  # r for Review
        # add points to score and score details
        self.score += xp - pp
        self.score_details += xpd + ppd
                
        # to keep nice progress percentages, each final review counts as 5%
        all_steps = 100 - 5 * final_reviews
        # each step can generate 4 "progress steps" except for the first (does not have the 2 review actions)
        self.progress = int(floor(p * all_steps / (legs * 4 - 2)) + 5 * gfr)
        if self.progress < all_steps:
            self.progress_color = 'blue'
        elif self.progress == 100:
            self.progress_color = 'violet'
        else:
            self.progress_color = 'orange'
        # blank circles should be drawn for unassigned steps
        if len(self.steps) < legs:
            self.rblanks = range(0, legs - len(self.steps) + final_reviews - 1)
        self.gblanks = range(0, legs - gr_count + final_reviews - len(self.given_final_reviews) - 1)

        # indicate whether participant is eligible for a grade
        # NOTE: Until 1-11-2019, this was when all but 1 steps were completed.
        #       Now, ALL steps must be completed
        if self.participant.estafette.end_time < UPDATE_2019:
            self.eligible = int(self.completed_steps >= nr_of_legs - 1)
            self.finished = int(self.completed_steps >= nr_of_legs)
        else:
            self.eligible = int(self.completed_steps >= nr_of_legs)
            self.finished = int(gfr >= final_reviews)


# view for course page that processes POST data with own CSRF protection (using encode/decode)
@method_decorator(csrf_exempt, name='dispatch')
@login_required(login_url=settings.LOGIN_URL)
def course_estafette(request, **kwargs):
    # count queries
    q_count = len(connection.queries)
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    # check whether user can view this course_estafette
    try:
        ceid = decode(h, context['user_session'].decoder)
        ce = CourseEstafette.objects.get(pk=ceid)
        if not (ce.course.manager == context['user']
                or ce.course.instructors.filter(id=context['user'].id)):
            log_message('ACCESS DENIED: Invalid course estafette parameter', context['user'])
            return render(request, 'presto/forbidden.html', context)
    except Exception as e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)

    # get the cases for this estafette
    global case_letters
    q_set = EstafetteCase.objects.filter(estafette=ce.estafette)
    case_letters = [c.letter for c in q_set]
    context['case_letters'] = case_letters
    
    # get the legs for this estafette
    global nr_of_legs
    q_set = EstafetteLeg.objects.filter(template=ce.estafette.template)
    nr_of_legs = len(q_set)
    context['leg_numbers'] = range(1, nr_of_legs + 1)
    
    # add list of estafette legs to the context
    context['legs'] = [{
        'object': el,
        'hex': encode(el.id, context['user_session'].encoder)
        } for el in q_set
    ]
    
    # make a list of leg IDs (for identifying qualified referees later on)
    leg_ids = q_set.values_list('id', flat=True)
    
    # add appraisal icon lists to context
    context['face_list'] = ['hand point up outline', 'smile', 'meh', 'frown']

    # also make speed-related parameters for this estafette accessible by all functions
    global half_way
    global speed_bonus
    global bonus_per_step
    global bonus_deadline
    global bonus_deadline_dict
    global scoring_system

    # if non-zero, speed bonus B makes that points earned in the first half
    # are multiplied by (1 + B) -- unless bonus_per_step is TRUE, see below!
    speed_bonus = ce.speed_bonus
    half_way = ce.start_time + (ce.deadline - ce.start_time) / 2

    # if bonus_per_step is TRUE, participants earn B points for each step i (of n steps) that they
    # complete within the 1/(n - i) fraction of the remaining time until the deadline minus 1 day
    # (i.e., no speed bonus on the last day of a relay)
    # NOTE: per 1-11-2019, this system has been replaced by fixed speed bonus deadlines
    bonus_per_step = ce.bonus_per_step
    if bonus_per_step:
        bonus_deadline_dict = ce.bonus_deadlines()
    bonus_deadline = ce.deadline - timedelta(days=1)
    
    # scoring system: 0 = relative differential;
    #                 1 = absolute with differential bonus
    #                 2 = new 2020 system with separate grade for previous work
    scoring_system = ce.scoring_system
    
    # add hex of this course estafette (used in action URL of settings form)
    context['ce_hex'] = encode(ce.id, context['user_session'].encoder)

    # add demonstration code (most often an empty string)
    context['demo_code'] = ce.demonstration_code()
    
    # see if the settings form was submitted
    if request.POST.get('s-time', ''):
        try:
            sdt = timezone.make_aware(datetime.strptime(
                string_to_datetime(request.POST.get('s-time', '')), SHORT_DATE_TIME))
            ddt = timezone.make_aware(datetime.strptime(
                string_to_datetime(request.POST.get('d-time', '')), SHORT_DATE_TIME))
            fdt = timezone.make_aware(datetime.strptime(
                string_to_datetime(request.POST.get('f-time', '')), SHORT_DATE_TIME))
            edt = timezone.make_aware(datetime.strptime(
                string_to_datetime(request.POST.get('e-time', '')), SHORT_DATE_TIME))
            qt = request.POST.get('questionnaire', '')
            if qt:
                try:
                    qt  = decode(qt, context['user_session'].decoder)
                except:
                    raise ValueError('Form session key does not match.')
            if edt <= sdt:
                raise ValueError('End time must fall after start time.')
            if ddt < sdt or ddt > edt:
                raise ValueError('Assignments deadline must fall between start time and end time.')
            if fdt < ddt or fdt > edt:
                raise ValueError('Final reviews deadline must fall between assignments deadline and end time.')
            try:
                fr = int(request.POST.get('reviews', ''))
                if fr < 0 or fr > 3:
                    raise ValueError('')
            except:
                raise ValueError('Number of final reviews can range from 0 to 3.')
            wrc = request.POST.get('clips', '') == '1'
            wb = request.POST.get('badges', '') == '1'
            wr = request.POST.get('referees', '') == '1'
            try:
                sb = float(request.POST.get('bonus', ''))
                if sb < 0 or sb > 1:
                    raise ValueError('')
            except:
                raise ValueError('Speed bonus must be a fraction between 0 and 1.')
            ps = request.POST.get('per-step', '') == '1'
            ih = request.POST.get('hidden', '') == '1'
            # if no errors occur, save the new parameter values
            ce.start_time = sdt
            ce.deadline = ddt
            ce.review_deadline = fdt
            ce.end_time = edt
            ce.final_reviews = fr
            ce.with_review_clips = wrc
            ce.with_badges = wb
            ce.with_referees = wr
            ce.speed_bonus = sb
            ce.bonus_per_step = ps
            ce.is_hidden = ih
            ce.save()
            inform_user(context, 'Relay settings have been changed')
        except ValueError as e:
            warn_user(context, 'Invalid input', str(e))

    # for the estafette form add the list of available evaluation questionnaires
    context['questionnaires'] = [{
        'name': t.name,
        'desc': t.description,
        'hex': encode(t.id, context['user_session'].encoder)
        } for t in QuestionnaireTemplate.objects.filter(published=True)
    ]

    # since viewing this page entails that the user is instructor,
    # (1) s/he must have a CourseStudent instance having dummy index = -1 to indicate
    #     "course instructor"
    instructor_cs, created = CourseStudent.objects.get_or_create(user=context['user'],
        course=ce.course, dummy_index=-1)
    if created:
        context['notifications'].append([
            'blue',
            'info circle',
            'Added as instructor',
            'You have been made instructor of this course: ' + ce.course.title()
        ])
        log_message('Added course instructor: ' + str(instructor_cs), context['user'])

    # (2) s/he must also be made "instructor participant" in this relay because this
    #     participant will be used as "successor" for assignments that have been rejected,
    #     and as "reviewer" for instructor reviews of "orphan assignments"
    instructor_participant, created = Participant.objects.get_or_create(student=instructor_cs,
        estafette=ce)
    if created:
        context['notifications'].append([
            'blue',
            'info circle',
            'Fit to review',
            'As instructor you can complete missing reviews when this relay has finished.'
        ])
        log_message('Added as instructor-participant: ' + str(instructor_participant),
            context['user'])
    
    # (3) s/he must be made referee for this estafette (if not already)
    n = 0
    for l in q_set:
        r, created = Referee.objects.get_or_create(user=context['user'], estafette_leg=l)
        if created:
            n += 1
    if n > 0:
        context['notifications'].append([
            'blue',
            'info circle',
            'Qualified as referee',
            'As instructor you qualify for all steps of this estafette.'
            ])
        log_message(
            'Qualified as referee for {} (n={})'.format(str(ce), n),
            context['user']
            )

    # for database efficiency, avoid queries within the main loop
    context.update({
        'estafette': ce,
        'start_time': timezone.localtime(ce.start_time).strftime(DATE_TIME_FORMAT),
        'end_time': timezone.localtime(ce.end_time).strftime(DATE_TIME_FORMAT),
        'next_deadline': ce.next_deadline(),
        's_time': timezone.localtime(ce.start_time).strftime(SHORT_DATE_TIME),
        'd_time': timezone.localtime(ce.deadline).strftime(SHORT_DATE_TIME),
        'f_time': timezone.localtime(ce.review_deadline).strftime(SHORT_DATE_TIME),
        'e_time': timezone.localtime(ce.end_time).strftime(SHORT_DATE_TIME),
        'participant_count': Participant.objects.filter(
            estafette=ce, student__dummy_index__gt=-1).count(),
        'active_count': Participant.objects.filter(
            estafette=ce, student__dummy_index__gt=-1
            ).filter(
            time_last_action__gte=timezone.now() - timedelta(days=1)
            ).count(),
        'pending_decisions': ce.pending_decisions()
    })
    # add url for chart image
    context['chart_url'] = 'progress/ce/' + encode(ce.id, context['user_session'].encoder)

    # the dictionaries are assigned to, so they must be declared as global
    global ref_dict      # referees
    global ref_case_dict # case count per referee
    global p_dict        # participants
    global a_dict        # assignments
    global r_dict        # reviews
    global ob_dict       # objections
    global ap_dict       # appeals

    # to display aliases of "focused" demo-users, collect aliases of related course students
    # as a dictionary with course student ID as key and alias as value
    demo_aliases = {}
    usl = UserSession.objects.all()
    for us in usl:
        uss = loads(us.state)
        if 'alias' in uss:
            demo_aliases[uss['course_student_id']] = uss['alias']
    
    # create a dict with all referees qualified for this course estafette, idexed by their ID
    q_set = Referee.objects.filter(estafette_leg__id__in=leg_ids)
    ref_dict = {}
    for r in q_set:
        ref_dict[r.id] = prefixed_user_name(r.user)

    # create a dict to count the appeals assigned to referees (by their name!)
    # NOTE: entries are dicts {assigned: n, undecided: m}
    rnl = list(set([ref_dict[k] for k in ref_dict.keys()]))
    ref_case_dict = {}
    for rn in rnl:
        ref_case_dict[rn] = {'assigned': 0, 'undecided': 0}

    # register lead students for this relay
    tla = team_leaders_added_to_relay(ce)
    if tla:
        inform_user(context, 'Lead students added as participants', 'Student name(s): ' + tla)

    # get all participants in this course estafette
    q_set = Participant.objects.filter(estafette=ce).exclude(deleted=True
        ).distinct().select_related('student', 'student__user')
    # create a dictionary with ParticipantProgress objects indexed by participant IDs
    p_dict = {}
    # and also make a list of IDs of "instructor participants"
    ipids = []
    for p in q_set:
        # do not use function dummy_name() so as not to access the database 
        if p.student.dummy_index > 0:
            if p.student.id in demo_aliases:
                di = ' (' + demo_aliases[p.student.id] + ')'
            elif p.student.particulars:
                di = ' (' + p.student.particulars + ')'
            else:
                di = ' (dummy # {})'.format(p.student.dummy_index)
        elif p.student.dummy_index < 0:
            di = INSTRUCTOR_SUFFIX
            ipids.append(p.id)
        else:
            di = ''
        p_dict[p.id] = ParticipantProgress(
            p,
            p.student.user.username,
            prefixed_user_name(p.student.user) + di,
            encode(p.id, context['user_session'].encoder)
            )

    # get the team lookup dict
    team_dict = team_lookup_dict(ce)
    # NOTE: This dict has as keys the participant IDs for all participants who have teamed up,
    #       with leading participants having a list of member participant IDs, and member
    #       participants just the ID of the leading participant.
    #       This data suffices to make a complete team string for each teamed up participant.
    t_now = timezone.now()
    for pid in p_dict.keys():
        t_entry = team_dict.get(pid, None)
        if t_entry:
            if type(t_entry) is list:
                lpid = pid
                p_dict[pid].is_leader = True
            else:
                lpid = t_entry
                t_entry = team_dict.get(lpid, None)
            n_list = [p_dict[lpid].name]
            for tpl in t_entry:
                mpn = p_dict[tpl[0]].name
                if t_now >= tpl[1]:
                    mpn += (' (until '
                        + datetime.strftime(tpl[1], SHORT_DATE_TIME) + ')'
                        )
                n_list.append(mpn)
            # add the team description string to the participant's attributes dict
            p_dict[pid].team = ', '.join(n_list)
            p_dict[pid].separated = '(until ' in p_dict[pid].team

    # construct assignment list while adding each assignment to the list of the associated participant
    q_set = Assignment.objects.filter(participant__in=p_dict.keys()
        ).distinct().select_related('case', 'leg', 'participant'
        ).order_by('time_assigned'
        ).values('id', 'participant__id',
        'leg__number', 'leg__min_upload_minutes',
        'case__letter', 'is_selfie', 'clone_of',
        'time_assigned', 'time_uploaded', 'is_rejected', 'predecessor__id', 'successor__id',
        'time_scanned', 'scan_result')
    a_dict = {}
    for a in q_set:
        a_dict[a['id']] = a
        pid = a['participant__id']
        p_dict[pid].add_step(a)
        # also add this same assignment as step for team members
        tl = team_dict.get(pid, [])
        if type(tl) is list:
            for tpl in tl:
                if a['time_uploaded'] < tpl[1]:
                    p_dict[tpl[0]].add_step(a)

    # add reviews to reviewer's "given" list and receiver's "received" list
    q_set = PeerReview.objects.filter(
        reviewer__in=p_dict.keys()
        ).distinct().order_by(
        'assignment__leg__number', 'time_submitted'
        ).values(
        'id', 'assignment__id', 'assignment__participant__id',
        'assignment__leg__number', 'assignment__clone_of', 'reviewer__id',
        'final_review_index', 'grade', 'is_rejection', 'is_second_opinion',
        'time_first_download', 'time_submitted', 'appraisal',
        'improvement_appraisal', 'time_appraised', 'improper_language',
        'is_appeal', 'time_appeal_assigned'
        )
    r_dict = {}
    for r in q_set:
        rev_pid = r['reviewer__id']
        # add field indicating whether review is a post-review by an instructor
        r['by_instructor'] = rev_pid in ipids
        r_dict[r['id']] = r
        p_dict[rev_pid].gave_review(r)
        # also add this same assignment as step for team members
        tl = team_dict.get(rev_pid, [])
        if type(tl) is list:
            for tpl in tl:
                p_dict[tpl[0]].gave_review(r)
        rec_pid = r['assignment__participant__id']
        if not (rec_pid in p_dict.keys()):
            # NOTE: "double checking" patch to cope with (erroneously!) assigned reviews
            #       that relate to work in ANOTHER course relay
            log_message('Review of unknown participant: ' + str(r), context['user'])
        else:
            p_dict[rec_pid].received_review(r)
            # also add this same assignment as step for team members
            tl = team_dict.get(rec_pid, [])
            if type(tl) is list:
                for tpl in tl:
                    p_dict[tpl[0]].received_review(r)

    # construct list of predecessor work ratings
    # NOTE: list should be empty if such items are not specified by the review template
    q_set = ItemReview.objects.filter(
        review__in=r_dict.keys(), item__appraisal='rating:5:star'
        ).distinct().order_by(
        'review__id'
        ).values(
        'review__id', 'rating'
        )
    # non-empty list => new scoring system (2)
    if q_set:
        scoring_system = 2
    # for all items found, add their rating as a field to the review dict
    for ir in q_set:
        r_dict[ir['review__id']]['grade_pw'] = ir['rating']

    # add list of objections for this estafette
    q_set = Objection.objects.filter(appeal__review__in=r_dict.keys()
        ).distinct().values('id', 'referee__id', 'appeal__id',
            'time_decided', 'grade', 'predecessor_penalty', 'successor_penalty')
    ob_dict = {}
    for ob in q_set:
        # add the referee's name
        ob['referee'] = ref_dict[ob['referee__id']]
        # NOTE: use the APPEAL ID as index to facilitate lookup
        ob_dict[ob['appeal__id']] = ob

    # add list of appeals for this estafette
    q_set = Appeal.objects.filter(review__in=r_dict.keys()
        ).distinct().values(
            'id', 'referee__id', 'review__id', 'appeal_type',
            'time_first_viewed', 'time_decided', 'grade',
            'predecessor_penalty', 'successor_penalty',
            'time_acknowledged_by_predecessor','time_acknowledged_by_successor',
            'predecessor_appraisal', 'successor_appraisal',
            'is_contested_by_predecessor', 'is_contested_by_successor'
            )
    ap_dict = {}
    for ap in q_set:
        ap['referee'] = ref_dict[ap['referee__id']]
        # Increment the case counter for this referee.
        ref_case_dict[ap['referee']]['assigned'] += 1
        # If case not decided, also increment the undecided case couter.
        if ap['time_decided'] == DEFAULT_DATE:
            ref_case_dict[ap['referee']]['undecided'] += 1
        # NOTE: Set to false to prohibit display of default date.
        if ap['time_first_viewed'] == DEFAULT_DATE:
            ap['time_first_viewed'] = False
        ap_dict[ap['id']] = ap
        p_dict[r_dict[ap['review__id']]['reviewer__id']].is_appealed(ap)


    # as statistics are collected "on the fly", create the global stats object
    # before calculating the participant objects
    global stats
    stats = EstafetteStatistics()

    # calculate all participant attributes and add list to context
    # NOTE: the participants are numbered to allow retrieving their score in JavaScript
    p_nr = 0
    context['participants'] = []
    for p in p_dict:
        p_dict[p].set_attributes(p_nr, nr_of_legs, ce.final_reviews)
        p_dict[p].referee = p_dict[p].name in ref_case_dict.keys()
        p_dict[p].appeals = ref_case_dict.get(
            p_dict[p].name, {'assigned': 0, 'undecided': 0})
        p_nr += 1
        context['participants'].append(p_dict[p])

    # complete statistics and add them to the context
    stats.compute_averages()
    context['stats'] = stats 
    context['stats_json'] = dumps(stats.__dict__).replace(', "', ',\n"')

    # allow administrators to download relay as dataset
    if has_role(context, 'Administrator'):
        context['can_download'] = True

    # log # queries performed for this view (NOTE: works only if settings.DEBUGGING = True)
    if q_count > 0:
        log_message(
            '{} queries performed to generate dashboard'.format(
                len(connection.queries) - q_count
                ),
            context['user']
            )

    # finally, return the rendered template
    context['page_title'] = 'Presto Course Relay'
    context['scoring_system'] = scoring_system
    return render(request, 'presto/course_estafette.html', context)

