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

# NOTE: partner list is workaround only! To be removed when database implementation is functional

tz = timezone.get_current_timezone()
FOREVER_DATE = timezone.make_aware(datetime.strptime('2100-12-31 00:00', SHORT_DATE_TIME))

FORMER_TEAM_LIST = '&nbsp; <span style="font-size: x-small" data-tooltip="{} {}">({})</span>'
SEPARATED_M_LIST =  '&nbsp; <span style="font-size: x-small">({})</span>'
SEPARATED_MEMBER = '<span data-tooltip="{} {}">{}</span>'

# workaround -- temporary; to be implemented with database objects
# NOTE: extensions are specified in hours
ASSIGNMENT_DEADLINE_EXTENSIONS = {
    'TB112-2019 Estafette B 2019':
    {
        'jsaoulidis': 48, 
        'mvervelde': 48,
    },
    'TB112-2019 Inhaalestafette 2020':
    {
        'llmink': 48, 
    },
    'TB112-2020 Estafette A 2020':
    {
        'fvanderpoestcl': 24,
        'mblankevoort': 24,
        'wvanbeusekom': 24,
    },
    'TB112-2020 Inhaalestafette 2021':
    {
        'nvanligten': 6,
        'tkeunen': 6,
    },
    'TB351-2020-Q3 BEP onderzoeksvoorstel':
    {
        'amaccreanor': 48, 
    },
    'TB112-2021 Implementatie 2021':
    {
        'rmhvankesteren': 5,
    },
    'TB112-2021 Inhaalestafette 2022':
    {
        'sophiekramer': 4, 
        'cvanneijenhoff': 4,
        'guusvandermeer': 24,
        'zdequaij': 24,
    }
}

REVIEW_DEADLINE_EXTENSIONS = {
    'TB112-2019 Estafette B 2019':
    {
        'jsaoulidis': 12, 
        'mvervelde': 12,
    },
    'TB112-2021 Conceptualisatie 2021':
    {
        'edschat': 10,
        'pleundevriesde': 10,
    },
    'TB112-2021 Modeltoepassing en interpretatie 2021':
    {
        'hvandeloo': 4,
        'ttilleman': 4,
        'mgwvanderkroon': 4,
        'bsoenen': 4,
        'gijsdebruijne': 4,
        'gkerkvliet': 4,
        'jrjernst': 68,
        'jram': 68,
    },
}


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


# partner list holds tuples (lead user name, partner user name [, separation date-time])
# NOTE: suffix __n indicates a dummy participant defined by an instructor
PARTNER_LISTS = {
    'DEMO Estafette A 2019':
    [
        ('maritboom', 'mtermaat'),
        ('machielvanderw', 'tvangend'),
    ],
    'DEMO Estafette A 2019 (2e)':
    [
        ('maritboom', 'mtermaat'),
        ('machielvanderw', 'tvangend'),
        ('pbots__1', 'pbots__2'),
        ('pbots__1', 'pbots__3'),
    ],
    'TB112-2019 Estafette A 2019':
    [
        ('rmozaffarian', 'yalmoussawi'),
        ('vzuurdeeg', 'josephineschol'),
        ('mjvanwageninge', 'qjapikse'),
        ('skoninkx', 'jvirginia'),
        ('pmoensi', 'yywu'),
        ('jttoet', 'jmschilder'),
        ('tkaal', 'zvanboxtel'),
        ('shelwegen', 'mbjhendriks'),
        ('eterhoeven', 'couwehand'),
        ('jhijlkema', 'jamvanraaij'),
        ('jtilman', 'shoefkens'),
        ('jborhem', 'atjschuurmans'),
        ('cnijenhuis', 'mmbeekman'),
        ('mvaneijck', 'dzevenberg'),
        ('bvanburik', 'smaingay'),
        ('eameeuwsen', 'evanbemmelen'),
        ('tsbos', 'rhavermans'),
        ('ftempelaar', 'mvantienhoven'),
        ('dhulsebos', 'tvandenbogaerd'),
        ('noijevaar', 'bradleyvanegmo'),
        ('hfaraji', 'sgokbekir'),
        ('nbroersen', 'satpijnenburg'),
        ('jwijffels', 'tmvanderschans'),
        ('rfrans', 'svanprooijen'),
        ('florismastenbr', 'mmuter'),
        ('ihall', 'lgijsen'),
        ('bejtimmer', 'dnienhuis'),
        ('wvanrootselaar', 'hpmeijer'),
        ('fhalkes', 'adekoeijer'),
        ('gbommele', 'sgcvos'),
        ('mjkooistra', 'pascalstam'),
        ('zsiliakus', 'agoselink'),
        ('jversantvoort', 'slwdevries'),
        ('rsimonides', 'jlmrebel'),
        ('ldvandijk', 'swielders'),
        ('medejonge', 'vfoekens'),
        ('svanderboon', 'marithuisman'),
        ('musaabahmed', 'oatta'),
        ('dvanderkeur', 'mlkragtwijk'),
        ('jvanderschans', 'nprast'),
        ('lucbos', 'skraaijeveld'),
        ('moavanteeffele', 'movandermost'),
        ('thuijsinga', 'jmndroge'),
        ('jsaoulidis', 'mvervelde'),
        ('emilyvermeulen', 'suzannemeijer'),
        ('bvaneijden', 'fkorthalsaltes'),
        ('cfmartens', 'jbuysschaert'),
        ('mwijn', 'tguleij'),
        ('idedroog', 'svanherwijnen'),
        ('bkraij', 'fboekhorst'),
        ('lwestrikbroeks', 'mmarang'),
        ('berendket', 'jsvanpaassen'),
        ('ubhagole', 'daanmuller'),
        ('esdejong', 'jchansen'),
        ('lvanderwolf', 'jming'),
        ('pzilch', 'sblaas'),
        ('nccornelissen', 'mzvanrooijen'),
        ('hkavelaars', 'lmjroggeveen'),
        ('ngedevreede', 'stektas'),
        ('jnelisse', 'eschepers'),
        ('pmalekiseifar', 'ssabirli'),
        ('vschuurman', 'jsvanreeuwijk'),
        ('spahnke', 'christophdeput'),
        ('cvanhaaff', 'kvanderschans'),
        ('lmolkenboer', 'kengee'),
        ('jlamore', 'dpiket'),
        ('mvandop', 'dahbouman'),
        ('lbsdejonge', 'mlaaraj'),
        ('averspeek', 'dshuizer'),
        ('jelmermerkus', 'spoli'),
        ('phamming', 'szlimburg'),
        ('fvodegel', 'kcsteijger'),
        ('jspbaars', 'bnieuwschepen'),
        ('tkiemeneij', 'luukversteeg'),
        ('lkeppels', 'fmmdeboer'),
        ('rcstorm', 'jkeulen'),
        ('mberns', 'bagroeneveld'),
        ('jbissumbhar', 'mtavanderzee'),
        ('mddeweerd', 'jrozenberg'),
        ('tvanbeeck', 'fheijermans'),
        ('nvandercamp', 'ozeeman'),
        ('mwilders', 'ewesselink'),
        ('hlvandermeulen', 'vrdeniet'),
        ('auzun', 'rszwetsloot'),
        ('jwspaans', 'shjvandekamp'),
        ('nvanulsen', 'jtterhorst'),
        ('eborst', 'aenvanderhelm'),
        ('pherfkens', 'mdekorver'),
        ('rgravenberch', 'tjcluiten'),
        ('mvankaauwen', 'mtulleken'),
        ('dmurray', 'llmink'),
        ('sclement', 'bbrans'),
        ('samjacobs', 'ftilro'),
        ('fbcmswinkels', 'nlinssen'),
        ('manonschneider', 'mvanhaften'),
        ('jbruning', 'pvanarkel'),
        ('aavangelder', 'apkamp'),
        ('lrijnbeek', 'milabenschop'),
        ('estoelinga', 'ptreanor'),
        ('mnvanberkum', 'jmvanmaanen'),
        ('sdoerdjan', 'emarts'),
        ('fdemolvanotter', 'svoskamp'),
        ('rmalmberg', 'jcederboom'),
        ('hmann', 'sfockemawurfba'),
        ('aquist', 'lximenezbruide'),
        ('jvanlanschot', 'jstubbe'),
        ('lvanwensveen', 'ajanissen'),
        ('jnjahangir', 'vinojbalasubra'),
        ('pgmdekruijff', 'pwetselaar'),
        ('inovakovic', 'esadegh'),
        ('rloos', 'bvanhest'),
        ('rhoogervorst', 'svandekerkhove'),
        ('mholl', 'amaccreanor'),
        ('pdoeswijk', 'djwvandorp'),
        ('dtabos', 'dbdrenth'),
        ('sweites', 'vmeier'),
        ('mvanschaick', 'suzannewink'),
        ('mokkema', 'nkansouh'),
        ('bvanuitert', 'tvandersluijs'),
        ('adblock', 'imschrama'),
        ('lsteur', 'rjmuller'),
        ('kgerasimovtel', 'pweijland'),
        ('tadeweijer', 'mmallens'),
        ('djsderuijter', 'ajansink'),
        ('salstevens', 'tmjvandijk'),
        ('ladewild', 'lswillemsen'),
        ('tepsmid', 'dvoskuil'),
        ('aibrahim3', 'malrobayi'),
        ('theutink', 'kurtvanpelt'),
        ('irvanderheide', 'nchangsingpang'),
        ('cwongatjong', 'lwahlen'),
        ('mhrbos', 'lgerbens'),
        ('sbelali', 'gderonde'),
        ('cgjvandermeer', 'jvgroen'),
        ('iheikoop', 'ohopmans'),
        ('ctaetsvanamero', 'jbulkmans'),
        ('stijnleussink', 'sbouwknegt'),
        ('wvankints', 'sjbol'),
        ('speper', 'mrvanderwerff'),
        ('skuppers', 'avangrotenhuis'),
        ('akoopal', 'kmekes'),
        ('tverwoerd', 'mvanderstichel'),
        ('trvissers', 'avanwijngaarde'),
        ('bklapwijk', 'hscheuer'),
        ('jnordemann', 'sboelhouwer'),
        ('cbgman', 'lcoremans'),
        ('jbussink', 'jpeteri'),
        ('avanlaarhoven', 'jponfoort'),
        ('tsome', 'tatenhave'),
        ('lvonck', 'jayvandam'),
        ('jjhvos', 'nsvanrijn'),
        ('bkempkes', 'pvancasteren'),
    ],
    'TB112-2019 Estafette B 2019':
    [
        ('rmozaffarian', 'yalmoussawi'),
        ('vzuurdeeg', 'josephineschol'),
        ('mjvanwageninge', 'qjapikse'),
        ('skoninkx', 'jvirginia'),
        ('pmoensi', 'yywu'),
        ('jttoet', 'jmschilder'),
        ('tkaal', 'zvanboxtel'),
        ('shelwegen', 'mbjhendriks'),
        ('eterhoeven', 'couwehand'),
        ('jhijlkema', 'jamvanraaij'),
        ('jtilman', 'shoefkens'),
        ('jborhem', 'atjschuurmans'),
        ('cnijenhuis', 'mmbeekman'),
        ('mvaneijck', 'dzevenberg'),
        ('bvanburik', 'smaingay'),
        ('eameeuwsen', 'evanbemmelen'),
        ('tsbos', 'rhavermans'),
        ('ftempelaar', 'mvantienhoven'),
        ('dhulsebos', 'tvandenbogaerd'),
        ('noijevaar', 'bradleyvanegmo'),
        ('hfaraji', 'sgokbekir'),
        ('nbroersen', 'satpijnenburg'),
        ('jwijffels', 'tmvanderschans'),
        ('rfrans', 'svanprooijen'),
        ('florismastenbr', 'mmuter'),
        ('ihall', 'lgijsen'),
        ('bejtimmer', 'dnienhuis'),
        ('wvanrootselaar', 'hpmeijer'),
        ('fhalkes', 'adekoeijer'),
        ('gbommele', 'sgcvos'),
        ('mjkooistra', 'pascalstam'),
        ('zsiliakus', 'agoselink'),
        ('jversantvoort', 'slwdevries'),
        ('rsimonides', 'jlmrebel'),
        ('ldvandijk', 'swielders'),
        ('medejonge', 'vfoekens'),
        ('svanderboon', 'marithuisman'),
        ('musaabahmed', 'oatta'),
        ('dvanderkeur', 'mlkragtwijk'),
        ('jvanderschans', 'nprast'),
        ('lucbos', 'skraaijeveld'),
        ('moavanteeffele', 'movandermost'),
        ('thuijsinga', 'jmndroge'),
        ('jsaoulidis', 'mvervelde'),
        ('emilyvermeulen', 'suzannemeijer'),
        ('bvaneijden', 'fkorthalsaltes'),
        ('cfmartens', 'jbuysschaert'),
        ('mwijn', 'tguleij'),
        ('idedroog', 'svanherwijnen'),
        ('bkraij', 'fboekhorst'),
        ('lwestrikbroeks', 'mmarang'),
        ('berendket', 'jsvanpaassen'),
        ('ubhagole', 'daanmuller'),
        ('esdejong', 'jchansen'),
        ('lvanderwolf', 'jming'),
        ('pzilch', 'sblaas'),
        ('nccornelissen', 'mzvanrooijen'),
        ('hkavelaars', 'lmjroggeveen'),
        ('ngedevreede', 'stektas'),
        ('jnelisse', 'eschepers'),
        ('pmalekiseifar', 'ssabirli'),
        ('vschuurman', 'jsvanreeuwijk'),
        ('spahnke', 'christophdeput'),
        ('cvanhaaff', 'kvanderschans'),
        ('lmolkenboer', 'kengee'),
        ('jlamore', 'dpiket'),
        ('mvandop', 'dahbouman'),
        ('lbsdejonge', 'mlaaraj'),
        ('averspeek', 'dshuizer'),
        ('jelmermerkus', 'spoli'),
        ('phamming', 'szlimburg'),
        ('fvodegel', 'kcsteijger'),
        ('jspbaars', 'bnieuwschepen'),
        ('tkiemeneij', 'luukversteeg'),
        ('lkeppels', 'fmmdeboer'),
        ('rcstorm', 'jkeulen'),
        # ('mberns', 'bagroeneveld'),
        ('jbissumbhar', 'mtavanderzee'),
        ('mddeweerd', 'jrozenberg'),
        ('tvanbeeck', 'fheijermans'),
        ('nvandercamp', 'ozeeman'),
        ('mwilders', 'ewesselink'),
        ('hlvandermeulen', 'vrdeniet'),
        ('auzun', 'rszwetsloot'),
        ('jwspaans', 'shjvandekamp'),
        ('nvanulsen', 'jtterhorst'),
        ('eborst', 'aenvanderhelm'),
        ('pherfkens', 'mdekorver'),
        ('rgravenberch', 'tjcluiten'),
        ('mvankaauwen', 'mtulleken'),
        ('dmurray', 'llmink'),
        ('sclement', 'bbrans'),
        # ('samjacobs', 'ftilro'),
        ('fbcmswinkels', 'nlinssen'),
        ('manonschneider', 'mvanhaften'),
        ('jbruning', 'pvanarkel'),
        ('aavangelder', 'apkamp'),
        ('lrijnbeek', 'milabenschop'),
        ('estoelinga', 'ptreanor'),
        ('mnvanberkum', 'jmvanmaanen'),
        ('sdoerdjan', 'emarts'),
        # ('fdemolvanotter', 'svoskamp'),
        # ('rmalmberg', 'jcederboom'),
        ('hmann', 'sfockemawurfba'),
        ('aquist', 'lximenezbruide'),
        ('jvanlanschot', 'jstubbe'),
        ('lvanwensveen', 'ajanissen'),
        ('jnjahangir', 'vinojbalasubra'),
        ('pgmdekruijff', 'pwetselaar'),
        ('inovakovic', 'esadegh'),
        ('rloos', 'bvanhest'),
        ('rhoogervorst', 'svandekerkhove'),
        # ('mholl', 'amaccreanor'),
        ('pdoeswijk', 'djwvandorp'),
        ('dtabos', 'dbdrenth'),
        ('sweites', 'vmeier'),
        ('mvanschaick', 'suzannewink'),
        ('mokkema', 'nkansouh'),
        ('bvanuitert', 'tvandersluijs'),
        ('adblock', 'imschrama'),
        ('lsteur', 'rjmuller'),
        ('kgerasimovtel', 'pweijland'),
        ('tadeweijer', 'mmallens'),
        ('djsderuijter', 'ajansink'),
        ('salstevens', 'tmjvandijk'),
        # ('ladewild', 'lswillemsen'),
        ('tepsmid', 'dvoskuil'),
        ('aibrahim3', 'malrobayi'),
        ('theutink', 'kurtvanpelt'),
        ('irvanderheide', 'nchangsingpang'),
        ('cwongatjong', 'lwahlen'),
        ('mhrbos', 'lgerbens'),
        # ('sbelali', 'gderonde'),
        ('cgjvandermeer', 'jvgroen'),
        ('iheikoop', 'ohopmans'),
        ('ctaetsvanamero', 'jbulkmans'),
        # ('stijnleussink', 'sbouwknegt'),
        ('wvankints', 'jcrijpma'),
        ('speper', 'mrvanderwerff'),
        ('skuppers', 'avangrotenhuis'),
        ('akoopal', 'kmekes'),
        ('tverwoerd', 'mvanderstichel'),
        ('trvissers', 'avanwijngaarde'),
        ('bklapwijk', 'hscheuer'),
        ('jnordemann', 'sboelhouwer'),
        ('cbgman', 'lcoremans'),
        ('jbussink', 'jpeteri'),
        ('avanlaarhoven', 'jponfoort'),
        ('tsome', 'tatenhave'),
        ('lvonck', 'jayvandam'),
        ('jjhvos', 'nsvanrijn'),
        ('bkempkes', 'pvancasteren'),
        # new teams below this line
        ('wschuit', 'laurensvanveen'),
        ('samjacobs', 'mholl'),
        ('wjevanderveen', 'jklessens'),
        ('fkamal', 'rawvanschaik'),
        ('mbbvermeer', 'hvijverberg'),
        ('ttverkerk', 'tvanzweden'),
        ('mlzegveld', 'jobstevens'),
        ('bvandenakker', 'etacken'),
        ('matteomazza', 'lvankersen'),
        ('emmvandenbrink', 'avietor'),
        ('gderonde', 'snorbart'),
        ('ftilro', 'skeukens'),
    ],

    'TB112-2019 Inhaalestafette 2020':
    [
        ('aavangelder', 'apkamp'),
        ('akoopal', 'kmekes'),
        ('auzun', 'rszwetsloot'),
        ('avanlaarhoven', 'jponfoort'),
        ('averspeek', 'dshuizer'),
        ('bkraij', 'fboekhorst'),
        ('bvanburik', 'smaingay'),
        ('bvandenakker', 'etacken'),
        ('bvaneijden', 'fkorthalsaltes'),
        ('cbgman', 'lcoremans'),
        ('cgjvandermeer', 'jvgroen'),
        ('ctaetsvanamero', 'jbulkmans'),
        #('cvanhaaff', 'kvanderschans'),
        ('dhulsebos', 'tvandenbogaerd'),
        ('dmurray', 'llmink'),
        ('eameeuwsen', 'evanbemmelen'),
        #('esdejong', 'jchansen'),
        ('estoelinga', 'ptreanor'),
        #('fbcmswinkels', 'nlinssen'),
        #('fkamal', 'rawvanschaik'),
        ('florismastenbr', 'mmuter'),
        ('ftempelaar', 'mvantienhoven'),
        ('ftilro', 'skeukens'),
        ('fvodegel', 'kcsteijger'),
        ('gbommele', 'sgcvos'),
        ('gderonde', 'snorbart'),
        ('hfaraji', 'sgokbekir'),
        ('ihall', 'lgijsen'),
        ('iheikoop', 'ohopmans'),
        ('inovakovic', 'esadegh'),
        ('irvanderheide', 'nchangsingpang'),
        ('jbissumbhar', 'ggerrits'),
        ('jbruning', 'pvanarkel'),
        ('jbussink', 'jpeteri'),
        ('jhijlkema', 'jamvanraaij'),
        ('jjhvos', 'nsvanrijn'),
        ('jlamore', 'dpiket'),
        ('jnjahangir', 'vinojbalasubra'),
        ('jnordemann', 'sboelhouwer'),
        ('jsaoulidis', 'mvervelde'),
        ('jspbaars', 'bnieuwschepen'),
        ('jtilman', 'shoefkens'),
        ('jttoet', 'jmschilder'),
        ('jvanderschans', 'nprast'),
        ('jvanlanschot', 'jstubbe'),
        ('jwspaans', 'shjvandekamp'),
        ('kgerasimovtel', 'pweijland'),
        ('ldvandijk', 'swielders'),
        ('lkeppels', 'fmmdeboer'),
        ('lrijnbeek', 'milabenschop'),
        ('lsteur', 'rjmuller'),
        ('lvonck', 'jayvandam'),
        ('lwestrikbroeks', 'mmarang'),
        ('mbbvermeer', 'hvijverberg'),
        ('mddeweerd', 'jrozenberg'),
        ('medejonge', 'vfoekens'),
        ('mhrbos', 'lgerbens'),
        ('mjkooistra', 'pascalstam'),
        ('mjvanwageninge', 'qjapikse'),
        ('mlzegveld', 'jobstevens'),
        ('mnvanberkum', 'jmvanmaanen'),
        ('mokkema', 'nkansouh'),
        ('musaabahmed', 'oatta'),
        ('mvaneijck', 'dzevenberg'),
        ('mwijn', 'tguleij'),
        ('nbroersen', 'satpijnenburg'),
        ('nccornelissen', 'mzvanrooijen'),
        ('noijevaar', 'bradleyvanegmo'),
        ('nvandercamp', 'ozeeman'),
        ('pmalekiseifar', 'ssabirli'),
        ('pmoensi', 'yywu'),
        ('rcstorm', 'jkeulen'),
        ('rgravenberch', 'tjcluiten'),
        ('rhoogervorst', 'svandekerkhove'),
        ('rloos', 'bvanhest'),
        ('rmozaffarian', 'yalmoussawi'),
        ('rsimonides', 'jlmrebel'),
        ('salstevens', 'tmjvandijk'),
        ('samjacobs', 'mholl'),
        ('sclement', 'bbrans'),
        ('sdoerdjan', 'emarts'),
        ('shelwegen', 'mbjhendriks'),
        ('skuppers', 'avangrotenhuis'),
        ('spahnke', 'christophdeput'),
        ('speper', 'mrvanderwerff'),
        ('sweites', 'vmeier'),
        ('tepsmid', 'dvoskuil'),
        ('theutink', 'kurtvanpelt'),
        ('thuijsinga', 'jmndroge'),
        ('tkaal', 'zvanboxtel'),
        ('tkiemeneij', 'luukversteeg'),
        ('trvissers', 'avanwijngaarde'),
        ('tsome', 'tatenhave'),
        #('ttverkerk', 'tvanzweden'),
        ('tvanbeeck', 'fheijermans'),
        ('tverwoerd', 'mvanderstichel'),
        ('vschuurman', 'jsvanreeuwijk'),
        ('wjevanderveen', 'jklessens'),
        ('wschuit', 'laurensvanveen'),
        ('wvanrootselaar', 'hpmeijer'),
        ('zsiliakus', 'agoselink'),
        # new teams below this line
        ('fkamal', 'helmadkouki'),
        ('nlinssen', 'ttverkerk'),
    ],

    'TB112-2020 Estafette A 2020':
    [
        ('aluttik', 'hspelt'),
        ('tcderuiter', 'preyn'),
        #('rsoen', 'rkaaks'),
        ('sdekeyser', 'fgoslings'),
        ('fmaasland', 'jiryjanssens'),
        #('achafanja', 'fvanderzalm'),
        ('fvlierboom', 'mjkolk'),
        ('ftilro', 'bvanhest'),
        ('cvanrijsoort', 'caalders'),
        ('adevosvansteen', 'dvanderaa'),
        ('jklessens', 'jmndroge'),
        ('jvangoch', 'theutink'),
        ('gjveenman', 'lblomvanassend'),
        ('esdejong', 'osiepman'),
        ('tjckrijger', 'kurtvanpelt'),
        ('dtieleman', 'jwjdeboer'),
        ('speper', 'bvanburik'),
        ('agoselink', 'shelwegen'),
        ('tvandenbogaerd', 'rawvanschaik'),
        ('mlklomp', 'pwagenaar'),
        ('lraaijmakers', 'jivanouwerkerk'),
        ('fggmjlafeber', 'romyhuizer'),
        ('akalse', 'mbjhendriks'),
        ('aalmeidalandma', 'aicvanleeuwen'),
        ('cwestenberg', 'svenholleman'),
        ('jwspaans', 'shjvandekamp'),
        ('nvanligten', 'tkeunen'),
        ('bnijsen', 'trveldhoven'),
        ('ddao', 'jnederhof'),
        ('zachatbi', 'vlabrie'),
        ('hvandeloo', 'akaastra'),
        ('mjvos', 'obrouwers'),
        ('fhevermeer', 'mbbvermeer'),
        ('mbouwhuis', 'sdenneboom'),
        ('markderijke', 'seavanos'),
        ('mvervelde', 'jsaoulidis'),
        ('jnordemann', 'wncvanderloo'),
        ('ttilleman', 'kbaan'),
        ('svanproosdij', 'blinders'),
        ('snijhout', 'fmaingay'),
        ('mjfvanderspek', 'pkockmann'),
        ('cvandergun', 'tvannoortwijk'),
        ('plasturm', 'svankuik'),
        ('bnolte', 'trijkens'),
        ('pboucher', 'bagroeneveld'),
        ('dvanbuitenen', 'sboelhouwer'),
        ('askok', 'karlijnjansen'),
        ('avanhooven', 'jmbhatti'),
        ('envandijk', 'yanickschipper'),
        ('cvankuppeveld', 'jdjonker'),
        ('hestourgie', 'larsgroen'),
        ('mevenhuis', 'tverwoerd'),
        ('pamvisser', 'smjleemans'),
        ('nvanstaalduine', 'lavanham'),
        ('ralfgroenendij', 'lddehaas'),
        ('lcadebruijn', 'dqdhuynh'),
        ('fkamal', 'mberns'),
        ('nkansouh', 'mokkema'),
        ('bdegen', 'jvanduerendenh'),
        ('bteeling', 'sboode'),
        ('mjkooistra', 'pascalstam'),
        ('hschuringa', 'baevandenberg'),
        ('svanlange', 'svanasten'),
        ('ckoole', 'sophiehage'),
        ('anbekkering', 'jvanalst'),
        ('bdurkut', 'yolthof'),
        ('shovius', 'kmvanderhulst'),
        ('tomasbisschop', 'sojansen'),
        ('fsoulane', 'skemperink'),
        ('tkukler', 'mvangroos'),
        ('kmekes', 'jobstevens'),
        ('jvanlanschot', 'jstubbe'),
        ('roelofkooijman', 'ovanwijngaarde'),
        ('fdelacourt', 'mpriimagi'),
        ('jkvanbuuren', 'daanvanderhoev'),
        ('mkjvandenheuve', 'srmheemskerk'),
        ('jvanhoeve', 'slagerwey'),
        ('aholt', 'pjdekkers'),
        ('mblankevoort', 'wvanbeusekom'),
        ('bdanshig', 'ihooft'),
        ('flbroekman', 'rhbahadoer'),
        ('cleovos', 'majandela'),
        ('nwolting', 'rpjvandermeule'),
        ('mwesterhout', 'vgoelst'),
        ('jhanekroot', 'dgipouw'),
        ('vvanderzanden', 'lxqkruithof'),
        ('mvennegoor', 'mvoncken'),
        ('jbruning', 'pvanarkel'),
        ('irvanderheide', 'nchangsingpang'),
        ('amijs', 'marittederuite'),
        ('ttvanleeuwen', 'lgunhan'),
        ('abaartman', 'bfderooij'),
        ('qperdijk', 'lennarttimmerm'),
        ('scroonenberg', 'tagstaal'),
        ('fchevalier', 'fvaneijnsberge'),
        ('jtinkhof', 'ymol'),
        ('fvandervegte', 'dnrvos'),
        ('fmverhoeven', 'hblakenburg'),
        ('gvanwijnen', 'ealblas'),
        ('mjgroenendijk', 'fsteenbakkers'),
        ('juliaklapwijk', 'bjjongbloed'),
        ('cdckoning', 'ljfkempen'),
        ('stijnbrons', 'aprovokluit'),
        ('avanwijngaarde', 'tfvanniekerk'),
        ('nveldpaus', 'ticovanwijk'),
        ('mvanderstichel', 'sschlicher'),
        ('nbudel', 'rjchardy'),
        ('yoosterlee', 'mhrbos'),
        ('trvissers', 'skeukens'),
        ('fbeckeringhvan', 'cschoen'),
        ('flaksanadjaja', 'tbousair'),
        ('twaldram', 'bdebok'),
        ('gbultema', 'cwvandenberg'),
        ('mjdenotter', 'thijsmiddendor'),
        #('savlot', 'neckenhausen'),
        ('mqhkuiper', 'tschmeink'),
        ('trleijen', 'rpoelhekke'),
        ('rvandermaden', 'rdeijkers'),
        ('jvaes', 'sikoh'),
        ('sfhoogendijk', 'mcruigrok'),
        ('tzijl', 'hknaven'),
        ('olam', 'jhehenkamp'),
        ('lpomstra', 'sluiken'),
        ('akamerling', 'jsteenstra'),
        ('fvanamersfoort', 'mbeemster'),
        ('rpmolendijk', 'hdmolenaar'),
        ('gnowak', 'advanderlinde'),
        ('eamdevlieger', 'fandringa'),
        ('pfaizi', 'ppishahang'),
        ('lvanderhorn', 'dstek'),
        ('xscherpbier', 'shvanderhorst'),
        ('sbrakele', 'lkapinga'),
        ('mkleintuente', 'jmcbeelen'),
        ('bwilpshaar', 'drozeboom'),
        ('dreuvekamp', 'sennabosman'),
        ('pbylard', 'mogeldof'),
        ('dhawinkels', 'jjcdevogel'),
        ('jcbaldwin', 'aukestreefkerk'),
        ('mmavanbeek', 'lfldejager'),
        ('mniemel', 'hjutte'),
        ('timbentvelsen', 'evoets'),
        ('bmvanbarneveld', 'orussell'),
        ('lrmvanrooijen', 'mludwig'),
        ('javanderark', 'lkwolff'),
        ('bmolder', 'naugustinus'),
        ('fvansteekelenb', 'lavansteekelen'),
        ('wchi', 'sschaaf'),
        ('wjapajoe', 'sharodjmahabie'),
        ('slageman', 'bcival'),
        ('rramdajal', 'ndaswani'),
        ('pbastiaansen', 'rhoek2'),
        ('aeschaeffer', 'tzhong'),
        #('btazegul', 'emete'),
        ('javandersar', 'slinssen'),
        ('tlocher', 'abourayeb'),
        ('davanrhijn', 'rdharmlall'),
        ('tadu', 'matijnniessenn'),
        ('slagerwaard', 'saarpost'),
        ('zvanommeren', 'basvansomeren'),
        ('tepsmid', 'svanwees'),
    ],
    'TB112-2020 Estafette B 2020':
    [
        ('aluttik', 'hspelt'),
        ('tcderuiter', 'preyn'),
        ('sdekeyser', 'fgoslings'),
        ('fmaasland', 'jiryjanssens'),
        ('fvlierboom', 'mjkolk'),
        ('ftilro', 'bvanhest'),
        ('cvanrijsoort', 'caalders'),
        ('adevosvansteen', 'dvanderaa'),
        ('jvangoch', 'theutink'),
        ('gjveenman', 'lblomvanassend'),
        ('esdejong', 'osiepman'),
        ('tjckrijger', 'kurtvanpelt'),
        ('dtieleman', 'jwjdeboer'),
        ('speper', 'bvanburik'),
        ('agoselink', 'shelwegen'),
        #('tvandenbogaerd', 'rawvanschaik'),
        ('mlklomp', 'pwagenaar'),
        ('lraaijmakers', 'jivanouwerkerk'),
        ('fggmjlafeber', 'romyhuizer'),
        ('akalse', 'mbjhendriks'),
        ('aalmeidalandma', 'aicvanleeuwen'),
        ('cwestenberg', 'svenholleman'),
        ('jwspaans', 'shjvandekamp'),
        ('nvanligten', 'tkeunen'),
        ('bnijsen', 'trveldhoven'),
        ('ddao', 'jnederhof'),
        ('zachatbi', 'vlabrie'),
        ('hvandeloo', 'akaastra'),
        ('mjvos', 'obrouwers'),
        ('fhevermeer', 'mbbvermeer'),
        ('mbouwhuis', 'sdenneboom'),
        ('markderijke', 'seavanos'),
        ('mvervelde', 'jsaoulidis'),
        ('jnordemann', 'wncvanderloo'),
        ('kbaan', 'ttilleman'),
        ('svanproosdij', 'blinders'),
        ('snijhout', 'fmaingay'),
        ('mjfvanderspek', 'pkockmann'),
        ('cvandergun', 'tvannoortwijk'),
        ('plasturm', 'svankuik'),
        ('bnolte', 'trijkens'),
        ('pboucher', 'bagroeneveld'),
        ('dvanbuitenen', 'sboelhouwer'),
        ('askok', 'karlijnjansen'),
        ('avanhooven', 'jmbhatti'),
        ('envandijk', 'yanickschipper'),
        ('cvankuppeveld', 'jdjonker'),
        ('hestourgie', 'larsgroen'),
        ('mevenhuis', 'tverwoerd'),
        ('pamvisser', 'smjleemans'),
        ('nvanstaalduine', 'lavanham'),
        ('ralfgroenendij', 'lddehaas'),
        ('lcadebruijn', 'dqdhuynh'),
        #('fkamal', 'mberns'),
        ('mokkema', 'nkansouh'),
        ('bdegen', 'jvanduerendenh'),
        ('bteeling', 'sboode'),
        ('mjkooistra', 'pascalstam'),
        ('baevandenberg', 'orussell'),
        #('svanlange', 'svanasten'),
        ('ckoole', 'sophiehage'),
        ('anbekkering', 'jvanalst'),
        ('bdurkut', 'yolthof'),
        ('shovius', 'kmvanderhulst'),
        ('tomasbisschop', 'sojansen'),
        ('fsoulane', 'skemperink'),
        ('tkukler', 'mvangroos'),
        ('kmekes', 'jobstevens'),
        ('jvanlanschot', 'jstubbe'),
        ('roelofkooijman', 'ovanwijngaarde'),
        ('fdelacourt', 'mpriimagi'),
        ('jkvanbuuren', 'daanvanderhoev'),
        ('mkjvandenheuve', 'srmheemskerk'),
        ('jvanhoeve', 'slagerwey'),
        ('aholt', 'pjdekkers'),
        ('mblankevoort', 'wvanbeusekom'),
        ('flbroekman', 'rhbahadoer'),
        ('cleovos', 'majandela'),
        ('nwolting', 'rpjvandermeule'),
        ('mwesterhout', 'vgoelst'),
        ('jhanekroot', 'dgipouw'),
        ('vvanderzanden', 'lxqkruithof'),
        ('mvennegoor', 'mvoncken'),
        ('jbruning', 'pvanarkel'),
        ('irvanderheide', 'nchangsingpang'),
        ('amijs', 'marittederuite'),
        ('ttvanleeuwen', 'lgunhan'),
        ('abaartman', 'bfderooij'),
        ('qperdijk', 'lennarttimmerm'),
        ('scroonenberg', 'tagstaal'),
        ('fchevalier', 'fvaneijnsberge'),
        #('jtinkhof', 'ymol'),
        ('fvandervegte', 'dnrvos'),
        ('fmverhoeven', 'hblakenburg'),
        ('gvanwijnen', 'ealblas'),
        ('mjgroenendijk', 'jmndroge'),
        ('juliaklapwijk', 'bjjongbloed'),
        ('cdckoning', 'ljfkempen'),
        ('stijnbrons', 'aprovokluit'),
        ('tfvanniekerk', 'avanwijngaarde'),
        ('nveldpaus', 'ticovanwijk'),
        ('mvanderstichel', 'sschlicher'),
        ('nbudel', 'rjchardy'),
        ('yoosterlee', 'mhrbos'),
        ('trvissers', 'skeukens'),
        ('fbeckeringhvan', 'cschoen'),
        ('flaksanadjaja', 'tbousair'),
        ('twaldram', 'bdebok'),
        ('gbultema', 'cwvandenberg'),
        ('mjdenotter', 'thijsmiddendor'),
        ('mqhkuiper', 'tschmeink'),
        ('trleijen', 'rpoelhekke'),
        ('rvandermaden', 'rdeijkers'),
        ('jvaes', 'sikoh'),
        ('sfhoogendijk', 'mcruigrok'),
        ('tzijl', 'hknaven'),
        ('olam', 'jhehenkamp'),
        ('lpomstra', 'sluiken'),
        ('akamerling', 'jsteenstra'),
        ('fvanamersfoort', 'mbeemster'),
        ('rpmolendijk', 'hdmolenaar'),
        ('gnowak', 'advanderlinde'),
        ('eamdevlieger', 'fandringa'),
        ('pfaizi', 'ppishahang'),
        ('lvanderhorn', 'dstek'),
        ('xscherpbier', 'shvanderhorst'),
        ('sbrakele', 'lkapinga'),
        ('mkleintuente', 'jmcbeelen'),
        ('bwilpshaar', 'drozeboom'),
        ('dreuvekamp', 'sennabosman'),
        ('pbylard', 'mogeldof'),
        ('dhawinkels', 'jjcdevogel'),
        ('jcbaldwin', 'aukestreefkerk'),
        ('mmavanbeek', 'lfldejager'),
        ('mniemel', 'hjutte'),
        ('timbentvelsen', 'evoets'),
        ('lrmvanrooijen', 'mludwig'),
        ('bmolder', 'naugustinus'),
        ('fvansteekelenb', 'lavansteekelen'),
        ('wchi', 'sschaaf'),
        ('slageman', 'bcival'),
        ('rramdajal', 'ndaswani'),
        ('pbastiaansen', 'rhoek2'),
        ('aeschaeffer', 'tzhong'),
        ('javandersar', 'slinssen'),
        ('tlocher', 'abourayeb'),
        ('davanrhijn', 'rdharmlall'),
        ('tadu', 'matijnniessenn'),
        ('slagerwaard', 'saarpost'),
        ('zvanommeren', 'basvansomeren'),
        ('tepsmid', 'svanwees'),
        # vanaf hier nieuw geformeerd
        ('hschuringa', 'spleyte'),
        ('rsoen', 'wghani'),
        ('jamvanraaij', 'jhijlkema'),
        ('kvanderschans', 'rawvanschaik'),
        ('rmozaffarian', 'frlfranken'),
        ('bmian', 'sezginyildiz'),
        # matchmaking
        #('jjhpeters', 'helmadkouki'),
        ('battia', 'elont'),
        ('achafanja', 'oabdelmalek'),
        ('fsteenbakkers', 'sharodjmahabie'),
        ('sdvaniperen', 'savlot'),
        #('mhaex', 'wgroenewoud'),
        ('ytalhaoui', 'fkamal'),
    ],
    'TB112-2020 Inhaalestafette 2021':
    [
        ('aluttik', 'hspelt'),
        ('tcderuiter', 'preyn'),
        ('sdekeyser', 'fgoslings'),
        ('fmaasland', 'jiryjanssens'),
        ('fvlierboom', 'mjkolk'),
        ('ftilro', 'bvanhest'),
        ('cvanrijsoort', 'caalders'),
        ('adevosvansteen', 'dvanderaa'),
        ('jvangoch', 'theutink'),
        ('gjveenman', 'lblomvanassend'),
        ('esdejong', 'osiepman'),
        ('tjckrijger', 'kurtvanpelt'),
        ('dtieleman', 'jwjdeboer'),
        ('speper', 'bvanburik'),
        ('agoselink', 'shelwegen'),
        #('tvandenbogaerd', 'rawvanschaik'),
        ('mlklomp', 'pwagenaar'),
        ('lraaijmakers', 'jivanouwerkerk'),
        ('fggmjlafeber', 'romyhuizer'),
        ('akalse', 'mbjhendriks'),
        ('aalmeidalandma', 'aicvanleeuwen'),
        ('cwestenberg', 'svenholleman'),
        ('jwspaans', 'shjvandekamp'),
        ('nvanligten', 'tkeunen'),
        ('bnijsen', 'trveldhoven'),
        ('ddao', 'jnederhof'),
        ('zachatbi', 'vlabrie'),
        ('hvandeloo', 'akaastra'),
        ('mjvos', 'obrouwers'),
        ('fhevermeer', 'mbbvermeer'),
        ('mbouwhuis', 'sdenneboom'),
        ('markderijke', 'seavanos'),
        ('mvervelde', 'jsaoulidis'),
        ('jnordemann', 'wncvanderloo'),
        ('kbaan', 'ttilleman'),
        ('svanproosdij', 'blinders'),
        ('snijhout', 'fmaingay'),
        ('mjfvanderspek', 'pkockmann'),
        ('cvandergun', 'tvannoortwijk'),
        ('plasturm', 'svankuik'),
        ('bnolte', 'trijkens'),
        ('pboucher', 'bagroeneveld'),
        ('dvanbuitenen', 'sboelhouwer'),
        ('askok', 'karlijnjansen'),
        ('avanhooven', 'jmbhatti'),
        ('envandijk', 'yanickschipper'),
        ('cvankuppeveld', 'jdjonker'),
        ('hestourgie', 'larsgroen'),
        ('mevenhuis', 'tverwoerd'),
        ('pamvisser', 'smjleemans'),
        ('nvanstaalduine', 'lavanham'),
        ('ralfgroenendij', 'lddehaas'),
        ('lcadebruijn', 'dqdhuynh'),
        #('fkamal', 'mberns'),
        ('mokkema', 'nkansouh'),
        ('bdegen', 'jvanduerendenh'),
        ('bteeling', 'sboode'),
        ('mjkooistra', 'pascalstam'),
        ('baevandenberg', 'orussell'),
        #('svanlange', 'svanasten'),
        ('ckoole', 'sophiehage'),
        ('anbekkering', 'jvanalst'),
        ('bdurkut', 'yolthof'),
        ('shovius', 'kmvanderhulst'),
        ('tomasbisschop', 'sojansen'),
        ('fsoulane', 'skemperink'),
        ('tkukler', 'mvangroos'),
        ('kmekes', 'jobstevens'),
        ('jvanlanschot', 'jstubbe'),
        ('roelofkooijman', 'ovanwijngaarde'),
        ('fdelacourt', 'mpriimagi'),
        ('jkvanbuuren', 'daanvanderhoev'),
        ('mkjvandenheuve', 'srmheemskerk'),
        ('jvanhoeve', 'slagerwey'),
        ('aholt', 'pjdekkers'),
        ('mblankevoort', 'wvanbeusekom'),
        ('flbroekman', 'rhbahadoer'),
        ('cleovos', 'majandela'),
        ('nwolting', 'rpjvandermeule'),
        ('mwesterhout', 'vgoelst'),
        ('jhanekroot', 'dgipouw'),
        ('vvanderzanden', 'lxqkruithof'),
        ('mvennegoor', 'mvoncken'),
        ('jbruning', 'pvanarkel'),
        ('irvanderheide', 'nchangsingpang'),
        ('amijs', 'marittederuite'),
        ('ttvanleeuwen', 'lgunhan'),
        ('abaartman', 'bfderooij'),
        ('qperdijk', 'lennarttimmerm'),
        ('scroonenberg', 'tagstaal'),
        ('fchevalier', 'fvaneijnsberge'),
        #('jtinkhof', 'ymol'),
        ('fvandervegte', 'dnrvos'),
        ('fmverhoeven', 'hblakenburg'),
        ('gvanwijnen', 'ealblas'),
        ('mjgroenendijk', 'jmndroge'),
        ('juliaklapwijk', 'bjjongbloed'),
        ('cdckoning', 'ljfkempen'),
        ('stijnbrons', 'aprovokluit'),
        ('tfvanniekerk', 'avanwijngaarde'),
        ('nveldpaus', 'ticovanwijk'),
        ('mvanderstichel', 'sschlicher'),
        ('nbudel', 'rjchardy'),
        ('yoosterlee', 'mhrbos'),
        ('trvissers', 'skeukens'),
        ('fbeckeringhvan', 'cschoen'),
        ('flaksanadjaja', 'tbousair'),
        ('twaldram', 'bdebok'),
        ('gbultema', 'cwvandenberg'),
        #('mjdenotter', 'thijsmiddendor'),
        ('mqhkuiper', 'tschmeink'),
        ('trleijen', 'rpoelhekke'),
        ('rvandermaden', 'rdeijkers'),
        ('jvaes', 'sikoh'),
        ('sfhoogendijk', 'mcruigrok'),
        ('tzijl', 'hknaven'),
        ('olam', 'jhehenkamp'),
        ('sluiken', 'lpomstra'),
        ('akamerling', 'jsteenstra'),
        ('fvanamersfoort', 'mbeemster'),
        ('toverduin', 'hdmolenaar'),
        ('gnowak', 'mjdenotter'),
        ('eamdevlieger', 'fandringa'),
        ('pfaizi', 'ppishahang'),
        ('lvanderhorn', 'dstek'),
        ('xscherpbier', 'shvanderhorst'),
        ('sbrakele', 'lkapinga'),
        ('mkleintuente', 'jmcbeelen'),
        ('bwilpshaar', 'drozeboom'),
        ('dreuvekamp', 'sennabosman'),
        ('pbylard', 'mogeldof'),
        ('dhawinkels', 'jjcdevogel'),
        ('jcbaldwin', 'aukestreefkerk'),
        ('mmavanbeek', 'lfldejager'),
        ('mniemel', 'hjutte'),
        ('timbentvelsen', 'evoets'),
        ('lrmvanrooijen', 'mludwig'),
        ('bmolder', 'naugustinus'),
        ('fvansteekelenb', 'lavansteekelen'),
        ('wchi', 'sschaaf'),
        ('slageman', 'bcival'),
        #('rramdajal', 'ndaswani'),
        #('pbastiaansen', 'rhoek2'),
        #('aeschaeffer', 'tzhong'),
        ('javandersar', 'slinssen'),
        ('tlocher', 'abourayeb'),
        ('davanrhijn', 'rdharmlall'),
        ('tadu', 'matijnniessenn'),
        ('slagerwaard', 'saarpost'),
        ('zvanommeren', 'basvansomeren'),
        ('tepsmid', 'svanwees'),
        # vanaf hier nieuw geformeerd
        ('hschuringa', 'spleyte'),
        #('rsoen', 'wghani'),
        ('jhijlkema', 'jamvanraaij'),
        ('kvanderschans', 'rawvanschaik'),
        ('adowlatkhah', 'frlfranken'),
        #('bmian', 'sezginyildiz'),
        # matchmaking
        #('jjhpeters', 'helmadkouki'),
        ('battia', 'elont'),
        ('achafanja', 'oabdelmalek'),
        ('fsteenbakkers', 'sharodjmahabie'),
        ('sdvaniperen', 'savlot'),
        #('mhaex', 'wgroenewoud'),
        ('ytalhaoui', 'fkamal'),
    ],
    'TB112-2021 Conceptualisatie 2021':
    [
        ('ajvermeer', 'ladema'),
        ('alexanderdider', 'mrksonneveld'),
        ('asnow', 'doosterink'),
        ('asverhoeven', 'mdboogers'),
        ('bacikel', 'wboujeddaine'),
        ('bcoppes', 'tiesbrink'),
        ('bheesen', 'svandewaart'),
        ('bparajuli', 'hbrotteveel'),
        ('bstevens2', 'mvanijcken'),
        ('btazegul', 'jhehenkamp'),
        ('cdckoning', 'ljfkempen'),
        #('cheron', 'ksrirangam'),
        ('cmhewitt', 'mmensinga'),
        ('cnmbos', 'mkreukniet'),
        ('cspruit', 'ntiberius'),
        ('cvanneijenhoff', 'dsmeekes'),
        ('dboitelle', 'jwfkoch'),
        ('doriandegroot', 'ivandekamp'),
        ('douwemarsman', 'fcluistra'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('drmeertens', 'tvanknippenber'),
        ('dstijger', 'rbaetens'),
        ('dthijssen', 'fjwdegrefte'),
        ('edschat', 'pleundevriesde'),
        ('eknoeff', 'rvanderwegen'),
        ('elifkeskin', 'sapnaghisai'),
        ('evanholm', 'tmlammers'),
        ('evanoijen', 'lramuz'),
        ('ffmpeters', 'dbeenen'),
        ('fturkcan', 'mrwildeboer'),
        ('ggajapersad', 'vdompig'),
        ('ghooiveld', 'ameliekok'),
        ('gijsdebruijne', 'gkerkvliet'),
        ('guusvandermeer', 'zdequaij'),
        ('hdmolenaar', 'vvanderzanden'),
        ('hmvanbeek', 'jpbrocker'),
        ('hvandeloo', 'ttilleman'),
        ('ihsdriessen', 'cdehorde'),
        ('ipinxt', 'mjverwijs'),
        ('irmooij', 'mmpvankesteren'),
        ('itkuipers', 'wncvanderloo'),
        ('iweidema', 'ccehuisman'),
        ('jahjhuijskens', 'ndorenbos'),
        ('jasperoele', 'rwbrandsma'),
        ('jbvermeulen', 'selouafrassi'),
        ('jeisenburger', 'merijnbrons'),
        ('jfwkock', 'dpoort'),
        ('jhangelbroek', 'bbuitenhuis'),
        ('jjfolkers', 'avanheiningen'),
        ('jkanhai', 'shiralal'),
        ('jkobakiwal', 'msagdur'),
        ('jldegoede', 'sdutilh'),
        ('jmbhatti', 'avanhooven'),
        ('jmolhuysen', 'nielsvandendoo'),
        ('jnjorna', 'smdehaan'),
        ('jrjernst', 'jram'),
        ('kbraad', 'thandgraaf'),
        ('kheijman', 'jrdhuisman'),
        ('kschmoutziguer', 'nvalkhoff'),
        ('kwittekoek', 'fmwarts'),
        ('lamirjalali', 'mzuiker'),
        ('laroeleveld', 'cschut'),
        ('lbmvandoorn', 'toverduin'),
        ('lbuijsrogge', 'hwahedi'),
        ('lennarttimmerm', 'tcderuiter'),
        ('lfranse', 'rmrkasi'),
        ('lhazebroek', 'vparee'),
        ('lhekkenberg', 'aestublier'),
        ('lihoekstra', 'shjengelen'),
        ('lisaverboomver', 'maajacobs'),
        ('llukasse', 'gpschot'),
        ('ltdegraaf', 'mvantreijen'),
        ('lvanderzwaan', 'nmalawau'),
        ('maudremmerswaa', 'nikitajanssen'),
        ('mcanagtegaal', 'mgafoer'),
        ('mcpater', 'mczwaan'),
        ('mdekruijk', 'wjdewaard'),
        ('mdeppenbroek', 'ifmdebie'),
        ('meekelaar', 'johannesdeniet'),
        ('mgeene', 'yramlal'),
        ('mgwvanderkroon', 'bsoenen'),
        ('mjpijnenburg', 'ihulst'),
        ('mkluovska', 'muusburgers'),
        ('mpicaulij', 'tong'),
        ('mrood1', 'tvandenakker'),
        ('mschermerhorn', 'lmsdewit'),
        ('nalthuis', 'wwvandenheuvel'),
        ('ndecastro', 'gmmmazzola'),
        ('nielsvanderhei', 'mvanwolffelaar'),
        ('njager', 'sesimonis'),
        ('nmrogaar', 'pvanwalbeek'),
        ('nwienia', 'hannekebezemer'),
        ('odeboer', 'jbrouwer10'),
        ('olam', 'anbisrie'),
        ('opoelman', 'tslaats'),
        ('oreinoud', 'gdegoederen'),
        ('ovanderwaal', 'rwijnants'),
        ('pbastiaansen', 'jnordemann'),
        ('pjvanveen', 'jjzuidema'),
        ('pmvswuste', 'fgvandijk'),
        ('pvanderkruijk', 'rjderooij'),
        ('qzonneveld', 'wbmolkenboer'),
        ('rbootsma', 'kzuidervaart'),
        ('rbzondag', 'rpzuidgeest'),
        ('reneebreedveld', 'cmvanderzwan'),
        ('rfritz', 'evmwalraven'),
        ('rharakamathlou', 'dalegriaveenem'),
        ('rjderidder', 'lholl'),
        ('rkamper', 'bmvanbarneveld'),
        ('rmhvankesteren', 'iroeleveld'),
        ('rvanbraak', 'kwegerif'),
        ('rvsingh', 'dvanderhaar'),
        ('sabouman', 'fhondeman'),
        ('sbpeeters', 'mebdegroot'),
        ('sbvandenbrekel', 'tfeitz'),
        ('sfijan', 'sjevanleeuwen'),
        ('shmgroeneveld', 'mwmvos'),
        ('sloeb', 'emmscheepers'),
        ('smyvuijk', 'jcstekelenburg'),
        ('sophiekramer', 'fpiperas'),
        ('splaum', 'ilkonig'),
        ('sstroeken', 'bwevermeer'),
        ('sterlouw', 'narensman'),
        ('teichelsheim', 'tboek'),
        ('teunisdebeer', 'phollweg'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('thijskusters', 'mboskamp'),
        ('thjvermeulen', 'wdroste'),
        ('tjtimmerman', 'mgahulsman'),
        ('tklaassens', 'mctstuart'),
        ('tpvanderkolk', 'mlpvanvlijmen'),
        ('trvissers', 'skeukens'),
        ('tspreen', 'lheezen'),
        ('trveldhoven', 'bnijsen'),
        ('tvlak', 'djstoop'),
        ('vnwterlouw', 'stijnvanderlaa'),
        ('wduin', 'mancher'),
        ('welshout', 'akaastra'),
        ('wleliveld', 'mprosee'),
        ('wmuntendam', 'jrupert'),
        ('wvangiffen', 'glensvelt'),
        ('xphilips', 'joukeosinga'),
        ('ylonyuk', 'laavandenberg'),
        ('ysterkenburg', 'kwinthagen'),
        ('yvannimwegen', 'xvis'),
        ('zalkhoury', 'nlantinga'),
    ],
    'TB112-2021 Operationalisatie 2021':
    [
        ('ajvermeer', 'ladema'),
        ('alexanderdider', 'mrksonneveld'),
        ('asnow', 'doosterink'),
        ('asverhoeven', 'mdboogers'),
        ('bacikel', 'wboujeddaine'),
        ('bcoppes', 'tiesbrink'),
        ('bheesen', 'svandewaart'),
        ('bnijsen', 'trveldhoven'),
        ('bparajuli', 'hbrotteveel'),
        ('bstevens2', 'mvanijcken'),
        ('btazegul', 'jhehenkamp'),
        ('cdckoning', 'ljfkempen'),
        #('cheron', 'ksrirangam'),
        ('cmhewitt', 'mmensinga'),
        ('cnmbos', 'mkreukniet'),
        ('cmons', 'tdekousemaeker'),
        ('cspruit', 'ntiberius'),
        ('cvanneijenhoff', 'dsmeekes'),
        ('dboitelle', 'jwfkoch'),
        ('doriandegroot', 'ivandekamp'),
        ('douwemarsman', 'fcluistra'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('drmeertens', 'tvanknippenber'),
        ('dstijger', 'rbaetens'),
        ('dthijssen', 'fjwdegrefte'),
        ('edschat', 'pleundevriesde'),
        ('eknoeff', 'rvanderwegen'),
        ('elifkeskin', 'sapnaghisai'),
        ('evanholm', 'tmlammers'),
        ('evanoijen', 'lramuz'),
        ('ffmpeters', 'dbeenen'),
        ('fturkcan', 'mrwildeboer'),
        ('ggajapersad', 'vdompig'),
        ('ghooiveld', 'ameliekok'),
        ('gijsdebruijne', 'gkerkvliet'),
        ('guusvandermeer', 'zdequaij'),
        ('hdmolenaar', 'vvanderzanden'),
        ('hmvanbeek', 'jpbrocker'),
        ('hvandeloo', 'ttilleman'),
        ('ihsdriessen', 'cdehorde'),
        ('ipinxt', 'mjverwijs'),
        ('irmooij', 'mmpvankesteren'),
        ('itkuipers', 'wncvanderloo'),
        ('iweidema', 'ccehuisman'),
        ('jahjhuijskens', 'ndorenbos'),
        ('jasperoele', 'rwbrandsma'),
        ('jbvermeulen', 'selouafrassi'),
        ('jeisenburger', 'merijnbrons'),
        ('jfwkock', 'dpoort'),
        ('jhangelbroek', 'bbuitenhuis'),
        ('jjfolkers', 'avanheiningen'),
        ('jkanhai', 'shiralal'),
        ('jkobakiwal', 'msagdur'),
        ('jldegoede', 'sdutilh'),
        ('jmbhatti', 'avanhooven'),
        ('jmolhuysen', 'nielsvandendoo'),
        ('jnjorna', 'smdehaan'),
        ('jrjernst', 'jram'),
        ('kbraad', 'thandgraaf'),
        ('kheijman', 'jrdhuisman'),
        ('kschmoutziguer', 'nvalkhoff'),
        ('kwittekoek', 'fmwarts'),
        ('lamirjalali', 'mzuiker'),
        ('laroeleveld', 'cschut'),
        ('lbmvandoorn', 'toverduin'),
        ('lbuijsrogge', 'hwahedi'),
        ('lennarttimmerm', 'tcderuiter'),
        ('lfranse', 'rmrkasi'),
        ('lhazebroek', 'vparee'),
        ('lhekkenberg', 'aestublier'),
        ('lihoekstra', 'shjengelen'),
        ('lisaverboomver', 'maajacobs'),
        ('llukasse', 'gpschot'),
        ('ltdegraaf', 'mvantreijen'),
        ('lvanderzwaan', 'nmalawau'),
        ('maudremmerswaa', 'nikitajanssen'),
        ('mcanagtegaal', 'mgafoer'),
        ('mcpater', 'mczwaan'),
        ('mdekruijk', 'wjdewaard'),
        ('mdeppenbroek', 'ifmdebie'),
        ('meekelaar', 'johannesdeniet'),
        ('mgeene', 'yramlal'),
        ('mgwvanderkroon', 'bsoenen'),
        ('mjpijnenburg', 'ihulst'),
        ('mkluovska', 'muusburgers'),
        ('mpicaulij', 'tong'),
        ('mrood1', 'tvandenakker'),
        ('mschermerhorn', 'lmsdewit'),
        ('nalthuis', 'wwvandenheuvel'),
        ('ndecastro', 'gmmmazzola'),
        ('nielsvanderhei', 'mvanwolffelaar'),
        ('njager', 'sesimonis'),
        ('nmrogaar', 'pvanwalbeek'),
        ('nwienia', 'hannekebezemer'),
        ('odeboer', 'jbrouwer10'),
        ('olam', 'anbisrie'),
        ('opoelman', 'tslaats'),
        ('oreinoud', 'gdegoederen'),
        ('ovanderwaal', 'rwijnants'),
        ('pbastiaansen', 'jnordemann'),
        ('pjvanveen', 'jjzuidema'),
        ('pmvswuste', 'fgvandijk'),
        ('pvanderkruijk', 'rjderooij'),
        ('qzonneveld', 'wbmolkenboer'),
        ('rbootsma', 'kzuidervaart'),
        ('rbzondag', 'rpzuidgeest'),
        ('reneebreedveld', 'cmvanderzwan'),
        ('rfritz', 'evmwalraven'),
        ('rharakamathlou', 'dalegriaveenem'),
        ('rjderidder', 'lholl'),
        ('rkamper', 'bmvanbarneveld'),
        ('rmhvankesteren', 'iroeleveld'),
        ('rvanbraak', 'kwegerif'),
        ('rvsingh', 'dvanderhaar'),
        ('sabouman', 'fhondeman'),
        ('sbpeeters', 'mebdegroot'),
        ('sbvandenbrekel', 'tfeitz'),
        ('sfijan', 'sjevanleeuwen'),
        ('shmgroeneveld', 'mwmvos'),
        ('sloeb', 'emmscheepers'),
        ('smyvuijk', 'jcstekelenburg'),
        ('sophiekramer', 'fpiperas'),
        ('splaum', 'ilkonig'),
        ('sstroeken', 'bwevermeer'),
        ('sterlouw', 'narensman'),
        ('teichelsheim', 'tboek'),
        ('teunisdebeer', 'phollweg'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('thijskusters', 'mboskamp'),
        ('thjvermeulen', 'wdroste'),
        ('tjtimmerman', 'mgahulsman'),
        ('tklaassens', 'mctstuart'),
        ('tpvanderkolk', 'mlpvanvlijmen'),
        ('trvissers', 'skeukens'),
        ('tspreen', 'lheezen'),
        ('tvlak', 'djstoop'),
        ('vnwterlouw', 'stijnvanderlaa'),
        ('wduin', 'mancher'),
        ('welshout', 'akaastra'),
        ('wleliveld', 'mprosee'),
        ('wmuntendam', 'jrupert'),
        ('wvangiffen', 'glensvelt'),
        ('xphilips', 'joukeosinga'),
        ('ylonyuk', 'laavandenberg'),
        ('ysterkenburg', 'kwinthagen'),
        ('yvannimwegen', 'xvis'),
        ('zalkhoury', 'nlantinga'),
    ],
    'TB112-2021 Implementatie 2021':
    [
        ('ajvermeer', 'ladema'),
        ('alexanderdider', 'mrksonneveld'),
        ('asnow', 'doosterink'),
        ('asverhoeven', 'mdboogers'),
        ('bacikel', 'wboujeddaine'),
        ('bcoppes', 'tiesbrink'),
        ('bheesen', 'svandewaart'),
        ('bparajuli', 'hbrotteveel'),
        ('bstevens2', 'mvanijcken'),
        ('btazegul', 'jhehenkamp'),
        ('cdckoning', 'ljfkempen'),
        ('cheron', 'davanrhijn'),
        ('cmhewitt', 'mmensinga'),
        ('cmons', 'tdekousemaeker'),
        ('cnmbos', 'mkreukniet'),
        ('cspruit', 'ntiberius'),
        ('cvanneijenhoff', 'dsmeekes'),
        ('dboitelle', 'jwfkoch'),
        ('doriandegroot', 'ivandekamp'),
        ('douwemarsman', 'fcluistra'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('drmeertens', 'tvanknippenber'),
        ('dstijger', 'rbaetens'),
        ('dthijssen', 'fjwdegrefte'),
        ('edschat', 'pleundevriesde'),
        ('eknoeff', 'rvanderwegen'),
        ('elifkeskin', 'sapnaghisai'),
        ('evanholm', 'tmlammers'),
        ('evanoijen', 'lramuz'),
        ('ffmpeters', 'dbeenen'),
        ('fturkcan', 'mrwildeboer'),
        ('ggajapersad', 'vdompig'),
        ('ghooiveld', 'ameliekok'),
        ('gijsdebruijne', 'gkerkvliet'),
        ('guusvandermeer', 'zdequaij'),
        ('hdmolenaar', 'vvanderzanden'),
        ('hmvanbeek', 'jpbrocker'),
        ('hvandeloo', 'ttilleman'),
        ('ihsdriessen', 'cdehorde'),
        ('ipinxt', 'mjverwijs'),
        ('irmooij', 'mmpvankesteren'),
        ('itkuipers', 'wncvanderloo'),
        ('iweidema', 'ccehuisman'),
        ('jahjhuijskens', 'ndorenbos'),
        ('jasperoele', 'rwbrandsma'),
        ('jbatema', 'bstehmann'),
        ('jbvermeulen', 'selouafrassi'),
        ('jeisenburger', 'merijnbrons'),
        ('jfwkock', 'dpoort'),
        ('jhangelbroek', 'bbuitenhuis'),
        ('jjfolkers', 'avanheiningen'),
        ('jkanhai', 'shiralal'),
        ('jkobakiwal', 'msagdur'),
        ('jldegoede', 'sdutilh'),
        ('jmbhatti', 'avanhooven'),
        ('jmolhuysen', 'nielsvandendoo'),
        ('jnjorna', 'smdehaan'),
        ('jrjernst', 'jram'),
        ('kbraad', 'thandgraaf'),
        ('kheijman', 'jrdhuisman'),
        ('kschmoutziguer', 'nvalkhoff'),
        ('kwittekoek', 'fmwarts'),
        ('lamirjalali', 'mzuiker'),
        ('laroeleveld', 'cschut'),
        ('lbmvandoorn', 'toverduin'),
        ('lbuijsrogge', 'hwahedi'),
        ('lennarttimmerm', 'tcderuiter'),
        ('lfranse', 'rmrkasi'),
        ('lhazebroek', 'vparee'),
        ('lhekkenberg', 'aestublier'),
        ('lihoekstra', 'shjengelen'),
        ('lisaverboomver', 'maajacobs'),
        ('llukasse', 'gpschot'),
        ('ltdegraaf', 'mvantreijen'),
        ('lvanderzwaan', 'nmalawau'),
        ('maudremmerswaa', 'nikitajanssen'),
        ('mcanagtegaal', 'mgafoer'),
        ('mcpater', 'mczwaan'),
        ('mdekruijk', 'wjdewaard'),
        ('mdeppenbroek', 'ifmdebie'),
        ('meekelaar', 'johannesdeniet'),
        ('mgeene', 'yramlal'),
        ('mgwvanderkroon', 'bsoenen'),
        ('mjpijnenburg', 'ihulst'),
        ('mkluovska', 'muusburgers'),
        ('mkraakman', 'jtiessing'),
        ('mpicaulij', 'tong'),
        ('mrood1', 'tvandenakker'),
        ('mschermerhorn', 'lmsdewit'),
        ('nalthuis', 'wwvandenheuvel'),
        ('ndecastro', 'gmmmazzola'),
        ('nielsvanderhei', 'mvanwolffelaar'),
        ('njager', 'sesimonis'),
        ('nmrogaar', 'pvanwalbeek'),
        ('nwienia', 'hannekebezemer'),
        ('odeboer', 'jbrouwer10'),
        ('okhalif', 'mgeerling'),
        ('olam', 'anbisrie'),
        ('opoelman', 'tslaats'),
        ('oreinoud', 'gdegoederen'),
        ('ovanderwaal', 'rwijnants'),
        ('pbastiaansen', 'jnordemann'),
        ('pjvanveen', 'jjzuidema'),
        ('pmvswuste', 'fgvandijk'),
        ('pvanderkruijk', 'rjderooij'),
        ('qzonneveld', 'wbmolkenboer'),
        ('rbootsma', 'kzuidervaart'),
        ('rbzondag', 'rpzuidgeest'),
        ('reneebreedveld', 'cmvanderzwan'),
        ('rfritz', 'evmwalraven'),
        ('rharakamathlou', 'dalegriaveenem'),
        ('rjderidder', 'lholl'),
        ('rkamper', 'bmvanbarneveld'),
        ('rmhvankesteren', 'iroeleveld'),
        ('rstengs', 'nsteinmetz'),
        ('rvanbraak', 'kwegerif'),
        ('rvanommeren', 'meikevleugel'),
        ('rvsingh', 'dvanderhaar'),
        ('sabouman', 'fhondeman'),
        ('sbpeeters', 'mebdegroot'),
        ('sbvandenbrekel', 'tfeitz'),
        ('sfijan', 'sjevanleeuwen'),
        ('shmgroeneveld', 'mwmvos'),
        ('sloeb', 'emmscheepers'),
        ('smyvuijk', 'jcstekelenburg'),
        ('sophiekramer', 'fpiperas'),
        ('splaum', 'ilkonig'),
        ('sstroeken', 'bwevermeer'),
        ('sterlouw', 'narensman'),
        ('svanhout', 'nfhendriks'),
        ('tadu', 'samuelboersma'),
        ('teichelsheim', 'tboek'),
        ('teunisdebeer', 'phollweg'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('thijskusters', 'mboskamp'),
        ('thjvermeulen', 'wdroste'),
        ('tjtimmerman', 'mgahulsman'),
        ('tklaassens', 'mctstuart'),
        ('tpodt', 'dlvanlent'),
        ('tpvanderkolk', 'mlpvanvlijmen'),
        ('trvissers', 'skeukens'),
        ('tspreen', 'lheezen'),
        ('tvlak', 'djstoop'),
        ('twentink', 'kbouhuijzen'),
        ('vnwterlouw', 'stijnvanderlaa'),
        ('wduin', 'mancher'),
        ('welshout', 'akaastra'),
        ('wleliveld', 'mprosee'),
        ('wmuntendam', 'jrupert'),
        ('wvangiffen', 'glensvelt'),
        ('xphilips', 'joukeosinga'),
        ('ylonyuk', 'laavandenberg'),
        ('ysterkenburg', 'kwinthagen'),
        ('yvannimwegen', 'xvis'),
        ('zalkhoury', 'nlantinga'),
    ],
    'TB112-2021 Modeltoepassing en interpretatie 2021':
    [
        ('ajvermeer', 'ladema'),
        ('alexanderdider', 'mrksonneveld'),
        ('asnow', 'doosterink'),
        ('asverhoeven', 'mdboogers'),
        ('bacikel', 'wboujeddaine'),
        ('bcoppes', 'tiesbrink'),
        ('bheesen', 'svandewaart'),
        ('bparajuli', 'hbrotteveel'),
        ('bstevens2', 'mvanijcken'),
        ('btazegul', 'jhehenkamp'),
        ('cdckoning', 'ljfkempen'),
        ('cheron', 'davanrhijn'),
        ('cmhewitt', 'mmensinga'),
        ('cmons', 'tdekousemaeker'),
        ('cnmbos', 'mkreukniet'),
        ('cspruit', 'ntiberius'),
        ('cvanneijenhoff', 'dsmeekes'),
        ('dboitelle', 'jwfkoch'),
        ('doriandegroot', 'ivandekamp'),
        ('douwemarsman', 'fcluistra'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('drmeertens', 'tvanknippenber'),
        ('dstijger', 'rbaetens'),
        ('dthijssen', 'fjwdegrefte'),
        ('edschat', 'pleundevriesde'),
        ('eknoeff', 'rvanderwegen'),
        ('elifkeskin', 'sapnaghisai'),
        ('evanholm', 'tmlammers'),
        ('evanoijen', 'lramuz'),
        ('ffmpeters', 'dbeenen'),
        ('fturkcan', 'mrwildeboer'),
        ('ggajapersad', 'vdompig'),
        ('ghooiveld', 'ameliekok'),
        ('gijsdebruijne', 'gkerkvliet'),
        ('guusvandermeer', 'zdequaij'),
        ('hdmolenaar', 'vvanderzanden'),
        ('hmvanbeek', 'jpbrocker'),
        ('hvandeloo', 'ttilleman'),
        ('ihsdriessen', 'cdehorde'),
        ('ipinxt', 'mjverwijs'),
        ('irmooij', 'mmpvankesteren'),
        ('itkuipers', 'wncvanderloo'),
        ('iweidema', 'ccehuisman'),
        ('jahjhuijskens', 'ndorenbos'),
        ('jasperoele', 'rwbrandsma'),
        ('jbatema', 'bstehmann'),
        ('jbvermeulen', 'selouafrassi'),
        ('jeisenburger', 'merijnbrons'),
        ('jfwkock', 'dpoort'),
        ('jhangelbroek', 'bbuitenhuis'),
        ('jjfolkers', 'avanheiningen'),
        ('jkanhai', 'shiralal'),
        ('jkobakiwal', 'msagdur'),
        ('jldegoede', 'sdutilh'),
        ('jmbhatti', 'avanhooven'),
        ('jmolhuysen', 'nielsvandendoo'),
        ('jnjorna', 'smdehaan'),
        ('jrjernst', 'jram'),
        ('kbraad', 'thandgraaf'),
        ('kheijman', 'jrdhuisman'),
        ('kschmoutziguer', 'nvalkhoff'),
        ('kwittekoek', 'fmwarts'),
        ('lamirjalali', 'mzuiker'),
        ('laroeleveld', 'cschut'),
        ('lbmvandoorn', 'toverduin'),
        ('lbuijsrogge', 'hwahedi'),
        ('lennarttimmerm', 'tcderuiter'),
        ('lfranse', 'rmrkasi'),
        ('lhazebroek', 'vparee'),
        ('lhekkenberg', 'aestublier'),
        ('lihoekstra', 'shjengelen'),
        ('lisaverboomver', 'maajacobs'),
        ('llukasse', 'gpschot'),
        ('ltdegraaf', 'mvantreijen'),
        ('lvanderzwaan', 'nmalawau'),
        ('maudremmerswaa', 'nikitajanssen'),
        ('mcanagtegaal', 'mgafoer'),
        ('mcpater', 'mczwaan'),
        ('mdekruijk', 'wjdewaard'),
        ('mdeppenbroek', 'ifmdebie'),
        ('meekelaar', 'johannesdeniet'),
        ('mgeene', 'yramlal'),
        ('mgwvanderkroon', 'bsoenen'),
        ('mjpijnenburg', 'ihulst'),
        ('mkluovska', 'muusburgers'),
        ('mkraakman', 'jtiessing'),
        ('mpicaulij', 'tong'),
        ('mrood1', 'tvandenakker'),
        ('mschermerhorn', 'lmsdewit'),
        ('nalthuis', 'wwvandenheuvel'),
        ('ndecastro', 'gmmmazzola'),
        ('nielsvanderhei', 'mvanwolffelaar'),
        ('njager', 'sesimonis'),
        ('nmrogaar', 'pvanwalbeek'),
        ('nwienia', 'hannekebezemer'),
        ('odeboer', 'jbrouwer10'),
        ('okhalif', 'mgeerling'),
        ('olam', 'anbisrie'),
        ('opoelman', 'tslaats'),
        ('oreinoud', 'gdegoederen'),
        ('ovanderwaal', 'rwijnants'),
        ('pbastiaansen', 'jnordemann'),
        ('pjvanveen', 'jjzuidema'),
        ('pmvswuste', 'fgvandijk'),
        ('pvanderkruijk', 'rjderooij'),
        ('qzonneveld', 'wbmolkenboer'),
        ('rbootsma', 'kzuidervaart'),
        ('rbzondag', 'rpzuidgeest'),
        ('reneebreedveld', 'cmvanderzwan'),
        ('rfritz', 'evmwalraven'),
        ('rharakamathlou', 'dalegriaveenem'),
        ('rjderidder', 'lholl'),
        ('rkamper', 'bmvanbarneveld'),
        ('rmhvankesteren', 'iroeleveld'),
        ('rstengs', 'nsteinmetz'),
        ('rvanbraak', 'kwegerif'),
        ('rvanommeren', 'meikevleugel'),
        ('rvsingh', 'dvanderhaar'),
        ('sabouman', 'fhondeman'),
        ('sbpeeters', 'mebdegroot'),
        ('sbvandenbrekel', 'tfeitz'),
        ('sfijan', 'sjevanleeuwen'),
        ('shmgroeneveld', 'mwmvos'),
        ('sloeb', 'emmscheepers'),
        ('smyvuijk', 'jcstekelenburg'),
        ('sophiekramer', 'fpiperas'),
        ('splaum', 'ilkonig'),
        ('sstroeken', 'bwevermeer'),
        ('sterlouw', 'narensman'),
        ('svanhout', 'nfhendriks'),
        ('tadu', 'samuelboersma'),
        ('teichelsheim', 'tboek'),
        ('teunisdebeer', 'phollweg'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('thijskusters', 'mboskamp'),
        ('thjvermeulen', 'wdroste'),
        ('tjtimmerman', 'mgahulsman'),
        ('tklaassens', 'mctstuart'),
        ('tpodt', 'dlvanlent'),
        ('tpvanderkolk', 'mlpvanvlijmen'),
        ('trvissers', 'skeukens'),
        ('tspreen', 'lheezen'),
        ('tvlak', 'djstoop'),
        ('twentink', 'kbouhuijzen'),
        ('stijnvanderlaa', 'vnwterlouw'),
        ('wduin', 'mancher'),
        ('welshout', 'akaastra'),
        ('wleliveld', 'mprosee'),
        ('wmuntendam', 'jrupert'),
        ('wvangiffen', 'glensvelt'),
        ('xphilips', 'joukeosinga'),
        ('ylonyuk', 'laavandenberg'),
        ('ysterkenburg', 'kwinthagen'),
        ('yvannimwegen', 'xvis'),
        ('zalkhoury', 'nlantinga'),
    ],
    'TB112-2021 Estafette B 2021':
    [
        ('ajvermeer', 'ladema'),
        ('alexanderdider', 'mrksonneveld'),
        ('asnow', 'doosterink'),
        ('asverhoeven', 'mdboogers'),
        ('bacikel', 'wboujeddaine'),
        ('bcoppes', 'tiesbrink'),
        ('bheesen', 'svandewaart'),
        ('bnijsen', 'trveldhoven'),
        ('bparajuli', 'hbrotteveel'),
        ('bstevens2', 'mvanijcken'),
        ('btazegul', 'jhehenkamp'),
        ('cdckoning', 'ljfkempen'),
        ('cheron', 'davanrhijn'),
        ('cmhewitt', 'mmensinga'),
        ('cmons', 'tdekousemaeker'),
        ('cnmbos', 'mkreukniet'),
        ('cspruit', 'ntiberius'),
        ('cvanneijenhoff', 'dsmeekes'),
        ('dboitelle', 'jwfkoch'),
        ('doriandegroot', 'ivandekamp'),
        ('douwemarsman', 'fcluistra'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('drmeertens', 'tvanknippenber'),
        ('dstijger', 'rbaetens'),
        ('dthijssen', 'fjwdegrefte'),
        ('edschat', 'pleundevriesde'),
        ('eknoeff', 'rvanderwegen'),
        ('elifkeskin', 'sapnaghisai'),
        ('evanholm', 'tmlammers'),
        ('evanoijen', 'lramuz'),
        ('ffmpeters', 'dbeenen'),
        ('fturkcan', 'mrwildeboer'),
        ('ggajapersad', 'vdompig'),
        ('ghooiveld', 'ameliekok'),
        ('gijsdebruijne', 'gkerkvliet'),
        ('guusvandermeer', 'zdequaij'),
        ('hdmolenaar', 'vvanderzanden'),
        ('hmvanbeek', 'jpbrocker'),
        ('hvandeloo', 'ttilleman'),
        ('ihsdriessen', 'cdehorde'),
        ('ipinxt', 'mjverwijs'),
        ('irmooij', 'mmpvankesteren'),
        ('itkuipers', 'wncvanderloo'),
        ('iweidema', 'ccehuisman'),
        ('jahjhuijskens', 'ndorenbos'),
        ('jasperoele', 'rwbrandsma'),
        ('jbatema', 'bstehmann'),
        ('jbvermeulen', 'selouafrassi'),
        ('jeisenburger', 'merijnbrons'),
        ('jfwkock', 'dpoort'),
        ('jhangelbroek', 'bbuitenhuis'),
        ('jjfolkers', 'avanheiningen'),
        ('jkanhai', 'shiralal'),
        ('jkobakiwal', 'msagdur'),
        ('jldegoede', 'sdutilh'),
        ('jmbhatti', 'avanhooven'),
        ('jmolhuysen', 'nielsvandendoo'),
        ('jnjorna', 'smdehaan'),
        ('jrjernst', 'jram'),
        ('kbraad', 'thandgraaf'),
        ('kheijman', 'jrdhuisman'),
        ('kschmoutziguer', 'nvalkhoff'),
        ('kwittekoek', 'fmwarts'),
        ('lamirjalali', 'mzuiker'),
        ('laroeleveld', 'cschut'),
        #('lbmvandoorn', 'toverduin'),
        ('lbuijsrogge', 'hwahedi'),
        ('lennarttimmerm', 'tcderuiter'),
        ('lfranse', 'rmrkasi'),
        ('lhazebroek', 'vparee'),
        ('lhekkenberg', 'aestublier'),
        ('lihoekstra', 'shjengelen'),
        ('lisaverboomver', 'maajacobs'),
        ('llukasse', 'gpschot'),
        ('ltdegraaf', 'mvantreijen'),
        ('lvanderzwaan', 'nmalawau'),
        ('maudremmerswaa', 'nikitajanssen'),
        ('mcanagtegaal', 'mgafoer'),
        ('mcpater', 'mczwaan'),
        ('mdekruijk', 'wjdewaard'),
        ('mdeppenbroek', 'ifmdebie'),
        ('meekelaar', 'johannesdeniet'),
        ('mgeene', 'yramlal'),
        ('mgwvanderkroon', 'bsoenen'),
        ('mjpijnenburg', 'ihulst'),
        ('mkluovska', 'muusburgers'),
        ('mkraakman', 'jtiessing'),
        ('mpicaulij', 'tong'),
        ('mrood1', 'tvandenakker'),
        ('mschermerhorn', 'lmsdewit'),
        ('nalthuis', 'wwvandenheuvel'),
        ('ndecastro', 'gmmmazzola'),
        ('nielsvanderhei', 'mvanwolffelaar'),
        ('njager', 'sesimonis'),
        ('nmrogaar', 'pvanwalbeek'),
        ('nwienia', 'hannekebezemer'),
        ('odeboer', 'jbrouwer10'),
        #('olam', 'anbisrie'),
        ('opoelman', 'tslaats'),
        ('oreinoud', 'gdegoederen'),
        ('ovanderwaal', 'rwijnants'),
        ('pbastiaansen', 'jnordemann'),
        ('pjvanveen', 'jjzuidema'),
        ('pmvswuste', 'fgvandijk'),
        ('pvanderkruijk', 'rjderooij'),
        ('qzonneveld', 'wbmolkenboer'),
        ('rbootsma', 'kzuidervaart'),
        ('rbzondag', 'rpzuidgeest'),
        ('reneebreedveld', 'cmvanderzwan'),
        ('rfritz', 'evmwalraven'),
        #('rharakamathlou', 'dalegriaveenem'),
        ('dalegriaveenem', 'lbmvandoorn'),
        ('rjderidder', 'lholl'),
        ('rkamper', 'bmvanbarneveld'),
        ('rmhvankesteren', 'iroeleveld'),
        ('rstengs', 'nsteinmetz'),
        ('rvanbraak', 'kwegerif'),
        ('rvanommeren', 'meikevleugel'),
        ('rvsingh', 'dvanderhaar'),
        ('sabouman', 'fhondeman'),
        ('sbpeeters', 'mebdegroot'),
        ('sbvandenbrekel', 'tfeitz'),
        ('sfijan', 'sjevanleeuwen'),
        ('shmgroeneveld', 'mwmvos'),
        ('sloeb', 'emmscheepers'),
        ('smyvuijk', 'jcstekelenburg'),
        ('sophiekramer', 'fpiperas'),
        ('splaum', 'ilkonig'),
        ('sstroeken', 'bwevermeer'),
        ('sterlouw', 'narensman'),
        ('svanhout', 'nfhendriks'),
        ('tadu', 'anbisrie'),
        ('teichelsheim', 'tboek'),
        ('teunisdebeer', 'phollweg'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('thijskusters', 'mboskamp'),
        ('thjvermeulen', 'wdroste'),
        ('tjtimmerman', 'mgahulsman'),
        ('tklaassens', 'mctstuart'),
        ('tpodt', 'dlvanlent'),
        ('tpvanderkolk', 'mlpvanvlijmen'),
        ('trvissers', 'skeukens'),
        ('tspreen', 'lheezen'),
        ('tvlak', 'djstoop'),
        ('twentink', 'kbouhuijzen'),
        ('vnwterlouw', 'stijnvanderlaa'),
        ('wduin', 'mancher'),
        ('welshout', 'akaastra'),
        ('wleliveld', 'mprosee'),
        ('wmuntendam', 'jrupert'),
        ('wvangiffen', 'glensvelt'),
        ('xphilips', 'joukeosinga'),
        ('ylonyuk', 'laavandenberg'),
        ('ysterkenburg', 'kwinthagen'),
        ('yvannimwegen', 'xvis'),
        ('zalkhoury', 'nlantinga'),
    ],
    'TB112-2021 Inhaalestafette 2022':
    [
        ('cheron', 'davanrhijn'),
        ('dqlnguyenphuc', 'thijsmiddendor'),
        ('dthijssen', 'fjwdegrefte'),
        ('fmwarts', 'kwittekoek'),
        ('fpiperas', 'yramlal'),
        ('guusvandermeer', 'zdequaij'),
        ('irmooij', 'mancher'),
        ('mdboogers', 'asverhoeven'),
        ('mdekruijk', 'wjdewaard'),
        ('mqhkuiper', 'tschmeink'),
        ('rwijnants', 'ovanderwaal'),
        ('sabouman', 'fhondeman'),
        ('sapnaghisai', 'elifkeskin'),
        ('shmgroeneveld', 'mwmvos'),
        ('sophiekramer', 'cvanneijenhoff'),
        ('tfnicolai', 'mtjinthamsjin'),
        ('wduin', 'tpodt'),
    ]

}


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
        un = (tpl[0] + '__' + tpl[2]) if tpl[2] > 0 else tpl[0]
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
                dt = tz.localize(datetime.strptime(tpl[2], SHORT_DATE_TIME))
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
                    return tz.localize(datetime.strptime(tpl[2], SHORT_DATE_TIME))
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


