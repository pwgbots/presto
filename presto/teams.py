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
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Appeal, Assignment,
    CourseEstafette, CourseStudent,
    DEFAULT_DATE,
    Participant, PeerReview,
    SHORT_DATE_TIME,
    UserDownload
)

# python modules
from datetime import datetime, timedelta

# presto modules
from presto.generic import log_message
from presto.extension_data import (
    ASSIGNMENT_DEADLINE_EXTENSIONS,
    REVIEW_DEADLINE_EXTENSIONS
)
from presto.team_data import PARTNER_LISTS

# NOTE: partner list is workaround only! To be removed when database implementation is functional

tz = timezone.get_current_timezone()
FOREVER_DATE = timezone.make_aware(datetime.strptime('2100-12-31 00:00', SHORT_DATE_TIME))

FORMER_TEAM_LIST = '&nbsp; <span style="font-size: x-small" data-tooltip="{} {}">({})</span>'
SEPARATED_M_LIST =  '&nbsp; <span style="font-size: x-small">({})</span>'
SEPARATED_MEMBER = '<span data-tooltip="{} {}">{}</span>'

def extended_assignment_deadline(p):
    r = p.estafette
    rt = r.title_text()
    xh = ASSIGNMENT_DEADLINE_EXTENSIONS.get(rt, {}).get(p.student.user.username, 0)
    if xh:
        return r.deadline + timedelta(hours=xh)
    return r.deadline


def extended_review_deadline(p):
    r = p.estafette
    rt = r.title_text()
    xh = REVIEW_DEADLINE_EXTENSIONS.get(rt, {}).get(p.student.user.username, 0)
    if xh:
        return r.review_deadline + timedelta(hours=xh)
    return r.review_deadline


# NOTE: To separate a *leader* from his/her team, the remaining team should be assigned a
#       new leader (swap roles if team count = 2) AND (!) re-register all team leader actions
#       (assignments, file uploads, reviews, appeals, objections) to the new leader.



# returns the list of partner tuples for relay r if it is defined
def relay_partner_list(r):
    # compose the relay title without HTML tags (this is the key in the dict of partner lists)
    rt = r.title_text()
    return PARTNER_LISTS.get(rt, None)


# adds team leaders for relay r as participant if they ar not already
# and returns their names as a string (empty string indicates that none have been added)
def team_leaders_added_to_relay(r):
    l = relay_partner_list(r)
    if not l:
        return ''
    # distinguish between normal students and instructor dummies
    unl = []
    dnl = []
    for tpl in l:
        undi = tpl[0].split('__')
        un = undi[0]
        if len(undi) > 1:
            dnl.append((un, int(undi[1])))
        else:
            unl.append(un)
    # remove duplicates
    unl = list(set(unl))
    # now unl contains all "normal" user names, and dnl tuples (username, dummy index)
    # get IDs of students already registered as participant
    rpids = Participant.objects.filter(estafette=r, student__user__username__in=unl
        ).values_list('student__id', flat=True)
    cs_set = CourseStudent.objects.filter(course=r.course, user__username__in=unl
        ).exclude(id__in=rpids)
    nl = []
    for cs in cs_set:
        p, created = Participant.objects.get_or_create(estafette=r, student=cs)
        if created:
            nl.append(cs.dummy_name())
    # TO DO: also add "dummy users"
    return ', '.join(nl)


# returns a dict {participant ID: entry} for relay r (to permit rapid lookup in course_estafette.py)
# NOTE: for LEADING participants, entry is a list of tuples (partner participant ID, separation time)
#       for non-leaders (hence: team members), entry is the lead participant ID
def team_lookup_dict(r):
    l = relay_partner_list(r)
    if not l:
        return {}
    # create a list with all usernames in the partner list
    unl = []
    for tpl in l:
        # trim dummy suffixes
        unl += [tpl[0].split('__')[0], tpl[1].split('__')[0]]
    # remove duplicates
    unl = list(set(unl))
    # get participants in relay r having a matching username
    p_set = Participant.objects.filter(estafette=r, student__user__username__in=unl
        ).values_list('student__user__username', 'id', 'student__dummy_index')
    # make a lookup dict {username: participant ID}
    un_p_dict = {}
    for tpl in list(p_set):
        # add dummy index as suffix if greater than 0
        un = '{}__{}'.format(tpl[0], tpl[2]) if tpl[2] > 0 else tpl[0]
        un_p_dict[un] = tpl[1]
    tz = timezone.get_current_timezone()
    # start with empty lookup dict
    tl_dict = {}
    for tpl in l:
        # first element of tuple is ID of leading participant
        lpid = un_p_dict.get(tpl[0], None)
        # second element is ID of team member
        mpid = un_p_dict.get(tpl[1], None)
        # only add if BOTH users are participant in the relay
        if lpid and mpid:
            # add the entry for the member participant (= ID of leader)
            tl_dict[mpid] = lpid
            # compute the separation date
            if len(tpl) == 2:
                dt = FOREVER_DATE
            else:
                dt = timezone.make_aware(datetime.strptime(tpl[2], SHORT_DATE_TIME))
            # append the tuple to the list for the leading participant (or create a new entry)
            if lpid in tl_dict:
                tl_dict[lpid].append((mpid, dt))
            else:
                tl_dict[lpid] = [(mpid, dt)]
    return tl_dict


# returns the username of participant p with suffix __n if p is a "dummy student" with index n 
def suffixed_username(p):
    un = p.student.user.username
    # add dummy index suffix if applicable
    if p.student.dummy_index > 0:
        un += '__{}'.format(p.student.dummy_index)
    return un


# returns queryset of partnered participants of participant p (as leader)
# NOTE: ignores separations!
def partner_set(p):
    un = suffixed_username(p) 
    l = relay_partner_list(p.estafette)
    if l:
        unl = []
        trimmed_unl = []
        # iterate through the partner list and append matching user names to list
        for tpl in l:
            # NOTE: the first element of a tuple is the leading partner
            if tpl[0] == un:
                unl.append(tpl[1])
                # trim the dummy suffix
                trimmed_unl.append(tpl[1].split('__')[0])
        if trimmed_unl:
            # get the set of participants having these user names
            p_set = Participant.objects.filter(estafette=p.estafette,
                student__user__username__in=trimmed_unl)
            # iterate through the set to select only the IDs of participants with matching dummy indices
            pids = []
            for p in p_set:
                un = suffixed_username(p) 
                if un in unl:
                    pids.append(p.id)
            return p_set.filter(id__in=pids)
    return None


# returns the participant that is leading the partnership that includes participant p
# NOTE: ignores separations!
def leading_participant(p):
    un = suffixed_username(p) 
    l = relay_partner_list(p.estafette)
    if l:
        # iterate through the partner list and return the first participant with matching name
        for tpl in l:
            # NOTE: the *second* element in tuple should equal the participant's name
            if tpl[1] == un:
                # split into username and dummy suffix (if any)
                undi = tpl[0].split('__')
                # by default, dummy index = 0
                di = 0 if len(undi) == 1 else int(undi[1])
                return Participant.objects.filter(estafette=p.estafette,
                    student__user__username=undi[0], student__dummy_index=di).first()
    return None


# returns time that leading participant lp and partnered particpant pp were separated
# (1-1-2001 if they never partnered, 31-12-2100 if they are still partnered)
def time_separated(lp, pp):
    # NOTE: a (presumed) team leader never separates from his/her own (single person) team
    if lp == pp:
        return FOREVER_DATE
    l = relay_partner_list(lp.estafette)
    if l:
        # iterate through the partner list and append matching user names
        ln = suffixed_username(lp) 
        pn = suffixed_username(pp) 
        tz = timezone.get_current_timezone()
        for tpl in l:
            if tpl[0] == ln and tpl[1] == pn:
                # check if separation date-time is specified
                if len(tpl) == 2:
                    return FOREVER_DATE
                else:
                    return timezone.make_aware(datetime.strptime(tpl[2], SHORT_DATE_TIME))
    return DEFAULT_DATE


# returns the participant that is leading the partnership in that includes participant p
def current_team_leader(p):
    # see if p is a team member
    lp = leading_participant(p)
    if lp:
        # if so, see if the partnership still holds
        if timezone.now() < time_separated(lp, p):
            # if so, return the lead participant 
            return lp
    return None


# returns the list of participants currently partnered with participant p
def current_team(p):
    # see if p is a team member
    lp = leading_participant(p)
    if lp:
        # get all team partners
        # if so, see if the partnership still holds
        if timezone.now() < time_separated(lp, p):
            # if so, return the lead participant 
            return lp
    # no partners, then just p
    return [p]


# returns TRUE if participant p corresponds to user u, or to the team leader for u
def authorized_participant(p, u):
    # NOTE: comment out the 2 lines below if admin should not be allowed to act for any participant
    if u.username == 'pbots':
        return True
    # authorized if participant p is user u
    psu = p.student.user
    if psu == u:
        return True
    # if not, see whether p is a team leader
    ps = partner_set(p)
    if ps:
        # if so, see whether u is a team member
        mp = ps.filter(student__user=u).first()
        if mp:
            # if so, see if the partnership still holds
            dts = time_separated(p, mp)
            if timezone.now() < dts:
                log_message('Authorized to act via team leader '
                            + p.student.dummy_name(), u)
                return True
            else:
                log_message(
                    ''.join([
                        'No longer authorized to act via team leader ',
                        p.student.dummy_name(), 
                        ' (since ',
                        datetime.strftime(dts, SHORT_DATE_TIME),
                        ')'
                        ]),
                    u
                    )
    return False


# returns queryset of users that at some time have been team partner of user u
def sometime_team_partners(u):
    un = u.username
    punl = [un]
    for k in PARTNER_LISTS.keys():
        # iterate through ALL partner lists
        for tpl in PARTNER_LISTS[k]:
            ln = tpl[0].split('__')[0]
            pn = tpl[1].split('__')[0]
            # add partner if leading user, or leading user if partner
            if ln == un:
                punl.append(pn)
            elif pn == un:
                punl.append(ln)
    # return the matching users
    return User.objects.filter(username__in=list(set(punl)))


# returns tuple (team leader, [all participants on the team])
# NOTE: ignores separations!
def partner_list(p):
    # first check if p has (had) a team leader
    lp = leading_participant(p)
    if lp:
        # if so, the team list should be this leader plus all other team members
        pl = [lp] + [pp for pp in partner_set(lp)]
    else:
        # otherwise check if p IS a team leader
        pl = partner_set(p)
        if pl:
            # if so, the team list should be p plus all other team members
            lp = p
            pl = [lp] + [pp for pp in pl]
        else:
            # no team => no leader, team consists of p only
            return (None, [p])
    return (lp, pl)


# returns current team of participant p, also considering separations
def current_team(p):
    lp, pl = partner_list(p)
    if not lp:
        # no team leader, then the team consists only of p
        return [p]
    team = []
    # now check which team members remain and which have (been) separated
    dtnow = timezone.now()
    for pp in pl:
        dts = time_separated(lp, pp)
        if dts <= dtnow:
            if pp == p:
                # if p DID separate, the team consists only of p
                return [p]
        else:
            team.append(pp)
    return team


# returns HTML for list of team members of participant p (marked if separated)
def team_as_html(p):
    lang = p.student.course.language
    lp, pl = partner_list(p)
    if not lp:
        return ''
    # make a list with HTML-formatted full participant names
    html = []
    # check which team members remain and which have (been) separated
    dtnow = timezone.now()
    rem = []
    sep = []
    # assume that p did NOT separate
    p_sep = False
    for pp in pl:
        dts = time_separated(lp, pp)
        if dts <= dtnow:
            sep.append(
                SEPARATED_MEMBER.format(
                    lang.phrase('Until'),
                    datetime.strftime(dts, SHORT_DATE_TIME),
                    pp.student.dummy_name()
                    )
            )
            if pp == p:
                # If p DID separate, record the separation time to signal
                # this special case.
                p_sep = dts
        else:
            rem.append(pp.student.dummy_name())
    html = []
    # if p separated, this implies a one-person team for p, separated from the entire former team
    if p_sep:
        for pp in pl:
            # NOTE: do not include p in the former team list
            if pp != p:
                html.append(pp.student.dummy_name())
        return p.student.user.dummy_name() + FORMER_TEAM_LIST.format(
            lang.phrase('Until'),
            datetime.strftime(p_sep, SHORT_DATE_TIME),
            ', '.join(html)
            )
    # otherwise, list remaining members, followed by the list of separated members (if any)
    html = ', '.join(rem)
    if sep:
        html += SEPARATED_M_LIST.format(', '.join(sep))
    return html


# returns a string showing the number of submitted assignments + final reviews
# for participant p, including (!) those submitted by the team leader while p was team member,
# over the required numbers
def team_submissions(p):
    steps = p.estafette.estafette.template.nr_of_legs()
    frevs = p.estafette.final_reviews
    ta = 0
    tr = 0
    # check wether participant p is (or was) member of a team
    lp = leading_participant(p)
    if lp:
        # if so, get the separation time of p (will be future if partnership still holds)
        dts = time_separated(lp, p)
        # count the assignments submitted (i.e., completed!) through the team leader 
        ta = Assignment.objects.filter(participant=lp, clone_of__isnull=True).exclude(
            time_uploaded=DEFAULT_DATE).exclude(time_uploaded__gte=dts).count()
        if frevs:
            # also count the final reviews submitted through the team leader 
            tr = PeerReview.objects.filter(reviewer=lp, final_review_index__gt=0).exclude(
                time_submitted=DEFAULT_DATE).exclude(time_submitted__gte=dts).count()
    # add number of p's own submitted assignments
    ta += Assignment.objects.filter(participant=p, is_rejected=False, clone_of__isnull=True
            ).exclude(time_uploaded=DEFAULT_DATE).count()
    if frevs:
        # if final reviews required, add number of p's own submitted final reviews
        tr += PeerReview.objects.filter(reviewer=p, final_review_index__gt=0
            ).exclude(time_submitted=DEFAULT_DATE).count()
        # display total review count only if non-zero
        sr = '+' + str(tr) if tr > 0 else '' 
        return '{}{} / {}+{}'.format(ta, sr, steps, frevs)
    # otherwise, only display submitted steps
    return '{} / {}'.format(ta, steps)


# returns a list of assignments worked on by participant p OR by team members (!)
def team_assignments(p):
    # check wether participant p is (or was) member of a team
    lp = leading_participant(p)
    if not lp:
        # if not, team assignment set is empty
        ta_set = Assignment.objects.none()
    else:
        # otherwise, get the assignments of the team leader (excluding clones and rejected ones) 
        ta_set = Assignment.objects.filter(participant=lp, is_rejected=False, clone_of__isnull=True)
        # get the separation time of p (will be future if partnership still holds)
        dts = time_separated(lp, p)
        if dts < FOREVER_DATE:
            # if separated, retain only those submitted (i.e., completed) before the separation
            ta_set = ta_set.filter(time_uploaded__gt=DEFAULT_DATE, time_uploaded__lt=dts)
    # get assignments participant p has worked on so far (not necessarily uploaded),
    # ignoring rejected ones and clones (since clones are "owned" by the student needing one)
    a_set = Assignment.objects.filter(participant=p, is_rejected=False, clone_of__isnull=True)
    return ta_set | a_set


# returns a list of user downloads performed by participant p OR by team members (!)
# for assignments having ID in list aid_list
def team_user_downloads(p, aid_list):
    # check wether participant p is (or was) member of a team
    lp = leading_participant(p)
    if not lp:
        # if not, user download set is empty
        tud_set = UserDownload.objects.none()
    else:
        # otherwise, get the separation time of p (will be future if partnership still holds)
        dts = time_separated(lp, p)
        # get the user downloads performed through the team leader prior to separation 
        tud_set = UserDownload.objects.filter(user=lp.student.user,
            time_downloaded__lte=dts, assignment__id__in=aid_list)
    # also get user downloads performed participant p
    ud_set = (tud_set | UserDownload.objects.filter(
        user=p.student.user, assignment__id__in=aid_list)).order_by('time_downloaded')
    # NOTE: return sorted such that first element is oldest
    return ud_set 


# returns a list of final reviews worked on by participant p OR by team members (!)
def team_final_reviews(p):
    return team_given_reviews(p, 2)

    
# returns a list of regular reviews (rtype=1), final reviews (rtype=2) or both (rtype=0)
# that have been worked on by participant p OR by team members (!)
def team_given_reviews(p, rtype=0):
    # check wether participant p is (or was) member of a team
    lp = leading_participant(p)
    if not lp:
        # if not, team review set is empty
        tr_set = PeerReview.objects.none()
    else:
        # otherwise, get the reviews assigned to the team leader
        if rtype == 1:
            tr_set = PeerReview.objects.filter(reviewer=lp, final_review_index=0)
        elif rtype == 2:
            tr_set = PeerReview.objects.filter(reviewer=lp, final_review_index__gt=0)
        else:
            tr_set = PeerReview.objects.filter(reviewer=lp)
        # get the separation time of p (will be future if partnership still holds)
        dts = time_separated(lp, p)
        if dts < FOREVER_DATE:
            # if separated, retain only the reviews submitted before the separation
            tr_set = tr_set.filter(time_submitted__gt=DEFAULT_DATE, time_submitted__lt=dts)
    # get the final reviews p has worked on so far
    if rtype == 1:
        r_set = PeerReview.objects.filter(reviewer=p, final_review_index=0)
    elif rtype == 2:
        r_set = PeerReview.objects.filter(reviewer=p, final_review_index__gt=0)
    else:
        r_set = PeerReview.objects.filter(reviewer=p)
    return tr_set | r_set


# returns a list of appeals made by participant p OR by team members (!)
# NOTE: (1) only returns the DECIDED appeals, as only these are shown to participants
#       (2) if not_ack=True, the already acknowledged appeal decisions are omitted
def team_appeals(p, not_ack=False):
    # check wether participant p is (or was) member of a team
    lp = leading_participant(p)
    if not lp:
        # if not, team appeal set is empty
        tap_set = Appeal.objects.none()
    else:
        # otherwise, get the appeals made by the team leader that are decided
        pap_set = Appeal.objects.filter(review__assignment__participant=lp,
            time_decided__gt=DEFAULT_DATE)
        if not_ack:
            pap_set = pap_set.filter(time_acknowledged_by_predecessor=DEFAULT_DATE)
        sap_set = Appeal.objects.filter(review__reviewer=lp, time_decided__gt=DEFAULT_DATE)
        if not_ack:
            sap_set = sap_set.filter(time_acknowledged_by_successor=DEFAULT_DATE)
        tap_set = pap_set | sap_set
        # get the separation time of p (will be future if partnership still holds)
        dts = time_separated(lp, p)
        if dts < FOREVER_DATE:
            # if separated, retain only the appeals decided before the separation
            tap_set = tap_set.filter(time_decided__lt=dts)
    # get the final reviews p has worked on so far
    pap_set = Appeal.objects.filter(review__assignment__participant=p,
        time_decided__gt=DEFAULT_DATE)
    if not_ack:
        pap_set = pap_set.filter(time_acknowledged_by_predecessor=DEFAULT_DATE)
    sap_set = Appeal.objects.filter(review__reviewer=p, time_decided__gt=DEFAULT_DATE)
    if not_ack:
        sap_set = sap_set.filter(time_acknowledged_by_successor=DEFAULT_DATE)
    return tap_set | pap_set | sap_set


# returns a dict with progress data for each step and final review (for display as progress bar)
# for participant p, taking into account its team!
def things_to_do(p):
    lang = p.student.course.language
    r = p.estafette
    steps = r.estafette.template.nr_of_legs()
    all_steps_done = False
    all_final_reviews_done = r.final_reviews == 0
    last_completed = DEFAULT_DATE
    # initialize "to do" list to contain a dict for each step
    ttd = [{
        'step': i + 1,
        'assigned': False,
        'assigned_tip': lang.phrase('Step_not_assigned').format(i + 1),
        'downloaded': False,
        'downloaded_tip': lang.phrase('Step_not_downloaded').format(i),
        'reviewed': False,
        'reviewed_tip': lang.phrase('Step_not_reviewed').format(i),
        'uploaded': False,
        'uploaded_tip': lang.phrase('Step_not_uploaded').format(i + 1),
        } for i in range(steps)]
    # add data on these assignments to the progress list
    for a in team_assignments(p):
        t = ttd[a.leg.number - 1]
        t['assigned'] = True
        t['assigned_tip'] = lang.phrase('Step_assigned').format(
            nr=t['step'],
            time=lang.ftime(a.time_assigned)
            )
        if a.leg.number > 1:
            # NOTE: show tooltip only if step has required files
            if a.leg.required_files:
                # check whether the student (or team) already downloaded the predecessor's work
                dl = team_user_downloads(p, [a.predecessor.id])
                if dl:
                    t['downloaded'] = True
                    t['downloaded_tip'] = lang.phrase('Step_downloaded').format(
                        nr=(t['step'] - 1),
                        time=lang.ftime(dl.first().time_downloaded)
                        )
            else:
                t['downloaded'] = True
                t['downloaded_tip'] = t['assigned_tip']
            # NOTE: ignore ID of reviewer (could be team leader)
            ur = PeerReview.objects.filter(assignment=a.predecessor)
            if ur:
                ur = ur.first()
                if ur.time_submitted != DEFAULT_DATE:
                    t['reviewed'] = True
                    t['reviewed_tip'] = lang.phrase('Step_reviewed').format(
                        nr=(t['step'] - 1),
                        time=lang.ftime(ur.time_submitted)
                        )
        if a.time_uploaded != DEFAULT_DATE:
            t['uploaded'] = True
            t['uploaded_tip'] = lang.phrase('Step_uploaded').format(
                nr=t['step'],
                time=lang.ftime(a.time_uploaded)
                )
            last_completed = a.time_uploaded
            all_steps_done = t['step'] == steps
    # add dicts for final reviews
    ttd += [{
        'review': i + 1,
        'downloaded': False,
        'downloaded_tip': lang.phrase('Review_not_downloaded').format(i + 1),
        'reviewed': False,
        'reviewed_tip': lang.phrase('Review_not_uploaded').format(i + 1)
        } for i in range(r.final_reviews)]
    # add data for each final review this participant has worked on so far
    for ur in team_final_reviews(p):
        t = ttd[steps + ur.final_review_index - 1]
        # NOTE: show tooltip only if step has required files
        a = ur.assignment
        if a.leg.required_files:
            # check whether the student (or team) already downloaded the work
            dl = team_user_downloads(p, [a.id])
            if dl:
                t['downloaded'] = True
                t['downloaded_tip'] = lang.phrase('Review_downloaded').format(
                    nr=t['review'],
                    time=lang.ftime(dl.first().time_downloaded)
                    )
        if ur.time_submitted != DEFAULT_DATE:
            t['reviewed'] = True
            t['reviewed_tip'] = lang.phrase('Review_reviewed').format(
                nr=t['review'],
                time=lang.ftime(ur.time_submitted)
                )
            last_completed = ur.time_submitted
            all_final_reviews_done = t['review'] == r.final_reviews
    if all_steps_done and all_final_reviews_done:
        ttd += [{'finish': lang.ftime(last_completed)}]
    return ttd


