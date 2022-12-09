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

# this module defines user interface phrases
# presently, two languages are supported: English and Dutch
UI_LANGUAGE_CODES = ['en-US', 'nl-NL']
UI_LANGUAGE_NAMES = ['English', 'Nederlands']

# English names of weekdays and months used when translating datetime strings:
CALENDAR_NAMES = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Sunday', 'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'
    ]

# UI phrases are stored in a dict that associates keys with tuples
# (English phrase, Dutch translation).
# NOTE: Keys must be a valid identifier (alphanumerics + underscore) because
#       they are typically used in Django templates as {{ dict.key }} 

UI_PHRASE_DICT = {
    # general words
    'and': ('and', 'en'),
    
    # student dropdown menu
    'Go_to': ('Go to', 'Ga naar'),
    'Home': ('Home', 'Startpagina'),
    'Announcements': ('Announcements', 'Berichten'),
    'History': ('History', 'Geschiedenis'),
    'Settings': ('Settings', 'Instellingen'),

    # date-related terms
    'Monday': ('Monday', 'maandag'),
    'Tuesday': ('Tuesday', 'dinsdag'),
    'Wednesday': ('Wednesday', 'woensdag'),
    'Thursday': ('Thursday', 'donderdag'),
    'Friday': ('Friday', 'vrijdag'),
    'Saturday': ('Saturday', 'zaterdag'),
    'Sunday': ('Sunday', 'zondag'),
    'January': ('January', 'januari'),
    'February': ('February', 'februari'),
    'March': ('March', 'maart'),
    'April': ('April', 'april'),
    'May': ('May', 'mei'),
    'June': ('June', 'juni'),
    'July': ('July', 'juli'),
    'August': ('August', 'augustus'),
    'October': ('October', 'oktober'),
    'November': ('November', 'november'),
    'December': ('December', 'december'),

    # general project relay properties
    'Runs_from': ('Runs from', 'Loopt van'),
    'through': ('through', 't/m'),
    'Deadline_for_assignments': (
        'Deadline for assignments',
        'Deadline voor opdrachten'
        ),
    'Deadline_for_reviews': ('Deadline for reviews', 'Deadline voor reviews'),
    'Deadline_for_responses': (
        'Deadline for responses',
        'Deadline voor reacties'
        ),
    'Relay_is_closed': ('Relay closed on', 'Estafette afgesloten op'),
    'Day': ('Day', 'Dag'),
    'Steps_completed': ('steps{} completed', 'stappen{} afgerond'),
    'Reviews': ('/reviews', '/reviews'),
    'Step': ('Step', 'Stap'),
    'Case': ('Case', 'Vraagstuk'),
    'Archived': ('This work has been archived', 'Dit werk is gearchiveerd'),

    # informational messages (to be displayed in blue)
    'Started': ('You have started', 'Je bent gestart'),
    'Godspeed': (
        'Lots of success (and fun) with the assignments!',
        'Veel succes (en hopelijk ook plezier) met de opdrachten!'
        ),
    'Joined_relay': ('Welcome to the team!', 'Welkom bij het team!'),
    'You_just_joined': (
        'You just joined the team for {relay}.',
        'Je bent nu lid van het team voor {relay}.'
        ),
    'Started_on': (
        'You started with {relay} on {time}.',
        'Je bent met {relay} gestart op {time}.'
        ),
    'Enrollment_succeeded': ('Enrollment succeeded', 'Inschrijving geslaagd'),
    'You_have_enrolled': (
        'You have been enrolled for the course {course}.',
        'Je bent ingeschreven voor de cursus {course}.'
        ),
    'Team_has_assignment': (
        'Your team has an assignment',
        'Je team heeft een opdracht'
        ),
    'Please_coordinate': (
        """Please coordinate your team activities well.
           Consult with your team members before you submit any work.""",
        """Stem als team onderling goed af.
           Overleg met je teamleden voordat je werk indient."""
        ),
    'Upload_successful': ('Upload successful', 'Uploaden geslaagd'),
    'Required_files_received': (
        'The required files have been received.',
        'De vereiste bestanden zijn opgeslagen.'
        ),
    'Predecessor_invited': (
        'Your predecessor will be invited to respond to your review.',
        'Je voorganger krijgt een uitnodiging om te reageren op jouw review.'),
    'You_have_declined': ('You have declined the case assignment',
        'Je hebt gepast voor dit vraagstuk'),
    'Try_again_later': (
        'Please wait at least a few hours before you proceed to get a new assignment!',
        'Wacht ten minste een paar uur voordat je verder gaat met een nieuwe opdracht!'
        ),
    'Review_received': ('Review received', 'Review ontvangen'),
    'Half_point_bonus': (
        'Your timely submission has earned you half a star bonus!',
        'Door je werk zo tijdig in te dienen heb je een halve ster extra verdiend!'
        ),
    'New_predecessor': (
        'Since you rejected the work, you must recommence this step.',
        'Aangezien je het werk hebt verworpen, moet je opnieuw beginnen met deze stap.'
        ),
    'Appeal_filed': (
        'Your appeal has been noted.',
        'Je hebt bezwaar aangetekend.'
        ),
    'Objection_filed': (
        'Your objection has been noted.',
        'Je hebt beroep aangetekend.'
        ),
    'Response_received': ('Response received', 'Reactie ontvangen'),
    'Will_see_response': (
        'Your successor will see your response the next time s/he logs on.',
        'Je opvolger zal je reactie zien zodra hij/zij weer inlogt.'
        ),
    'Will_see_appraisal': (
        'The referee will see your response the next time s/he logs on.',
        'De scheidsrechter zal je reactie zien zodra hij/zij weer inlogt.'
        ),
    'Frontrunner': ('You\'re a frontrunner!', 'Je bent een koploper!'),
    'Continue_own_work': (
        """This means that there is no work by others for you to build on.
           Therefore, please build on your own work on the previous step.<br>
           Alternatively, you can decline and wait until other work becomes available.""",
        """Dit betekent dat er geen werk van anderen is waar je op kunt voortbouwen.
           Je mag daarom verdergaan met je eigen uitwerking van de vorige stap.<br>
           Het alternatief is dat je nu past en wacht tot het werk van iemand anders
           beschikbaar komt."""
        ),
    'Appeal_assigned': ('Appeal assigned', 'Bezwaarschrift toegewezen'),
    'Objection_assigned': ('Objection assigned', 'Beroepszaak toegewezen'),
    'You_have_been_appointed': (
        'You have been appointed as referee for this case.',
        'Je bent aangesteld als scheidsrechter in deze zaak.'
        ),
    'Decision_pronounced': ('Decision pronounced', 'Besluit bekendgemaakt'),
    'Parties_will_be_informed': (
        """All parties will be informed, and invited to give their opinion on your decision.""",
        """Alle partijen krijgen hierover bericht, en worden uitgenodigd hun mening te geven
           over jouw besluit."""
        ),
    'Relay_suspended': ('This relay has been put on hold',
        'Deze estafette is tijdelijk stilgezet'),
    'No_uploads_or_reviews': (
        'You cannot upload work or submit reviews.',
        'Je kunt geen werk of reviews indienen.'),

    # warning messages (to be displayed in orange)
    'Already_enrolled': ('Already enrolled', 'Reeds ingeschreven'),
    'Already_started': ('Already started', 'Reeds gestart'),
    'Invalid_file': ('Invalid file', 'Onbruikbaar bestand'),
    'File_is_not_type': (
        'The <tt>{file}</tt> file is not of type <tt>{type}</tt>.',
        'Het <tt>{file}</tt>-bestand is geen <tt>{type}</tt>-bestand.'
        ),
    'Already_submitted': ('Already submitted', 'Al eerder ingediend'),
    'You_cannot_upload_yet': (
        'You cannot upload yet',
        'Je kunt nog niet indienen'
        ),
    'Minimum_working_time': (
        'The minimum time you should work on this step has not passed yet.',
        'De tijd die je minimaal aan deze stap moet besteden is nog niet verstreken'
        ),
    'Peer_review_incomplete': (
        'Review still incomplete',
        'Review nog niet volledig'
        ),
    'Incomplete_peer_review': (
        'The review of your predecessor\'s work appears to be incomplete.',
        'De review van het werk van je voorganger lijkt nog niet volledig te zijn.'
        ),
    'Review_not_submitted': (
        """Your review appears to have been re-opened, possibly by one of
           your team members. Please reload this page.""",
        """Je review lijkt opnieuw te zijn geopend, mogelijk door een van
           je teamgenoten. Laad deze pagina opnieuw."""
        ),
    'Review_submitted_by_team': (
        'This review has meanwhile been submitted, possibly by one of your team members.',
        'Deze review is inmiddels ingediend, mogelijk door een van je teamgenoten.'
        ),
    'You_already_uploaded': (
        'You have already uploaded the required files for this step.',
        'Je hebt voor deze stap vereiste bestanden reeds geupload.'
        ),
    'Upload_failed': ('Upload failed', 'Uploaden niet geslaagd'),
    'Missing_or_invalid_files': (
        'Some required files were missing or not of the correct type.',
        'Sommige vereiste bestanden ontbraken of waren niet van het juiste type.'
        ),
    'Review_resubmission': (
        'Review already submitted',
        'Review reeds ingediend'
        ),
    'Review_submitted_on': (
        'You already sumbitted a review for this work on {time}.',
        'Je hebt al een review ingediend op {time}.'
        ),
    'Review_can_be_revised': (
        'Review already editable',
        'Review stond al weer open'
        ),
    'Could_not_decline': (
        'You can not decline the assignment',
        'Je kunt niet (meer) passen voor dit vraagstuk'
        ),
    'Downloaded_or_old_URL': (
        'You have already downloaded your predecessor\'s work, or used an old URL.',
        'Je hebt het werk van je voorganger al gedownload, of een oude URL gebruikt.'
        ),
    'Used_old_URL': (
        'You probably used an old URL.',
        'Waarschijnlijk heb je een oude URL gebruikt.'
        ),
    'Response_resubmission': (
        'Response already submitted',
        'Reactie reeds ingediend'
        ),
    'Response_submitted_on': (
        'You already submitted your response on {time}.',
        'Je hebt al gereageerd op {time}.'
        ),
    'Appraisal_already_acknowledged': (
        'Response already acknowledged',
        'Reactie reeds bevestigd'
        ),
    'Appraisal_acknowledged_on': (
        'You already confirmed having read your sucessor\'s response on {time}.',
        'Je hebt al op {time} doorgegeven dat je de reactie van je voorganger hebt gelezen.'
        ),
    'Appeal_already_assigned': (
        'Case already assigned',
        'Zaak reeds toegewezen'
        ),
    'You_already_confirmed_to_referee': (
        'You already confirmed to act as referee this case.',
        'Je hebt al toegezegd als scheidsrechter over dit bezwaarschrift te oordelen.'
        ),
    'Assigned_to_other_referee': (
        'This case has been assigned to some other qualified referee.',
        'Deze zaak wordt door een andere gekwalificeerde scheidsrechter behandeld.'
        ),
    'Decision_already_pronounced': (
        'Decision already pronounced',
        'Besluit al bekend gemaakt'
        ),
    'Decision_pronounced_on': (
        'You already pronounced your decision on {time}.',
        'Je hebt je beslissing al op {time} bekend gemaakt.'
        ),
    'Final_review_failed': ('No suitable work for final review available (yet)',
        'Er is (nog) geen geschikt werk voor afrondende review beschikbaar'),
    'Missing_key_words': ('Missing key words', 'Trefwoorden ontbreken'),
    'Document_should_mention': (
        """The <tt>{doc}</tt> document should also mention {terms}.<br>
           Please check whether it is complete.""",
        """Het <tt>{doc}</tt> document zou ook moeten gaan over {terms}.<br>
           Controleer a.j.b. of het wel volledig is."""
        ),
    'Document_incomplete': (
        'The <tt>{doc}</tt> document appears to be incomplete',
        'Het <tt>{doc}</tt>-document lijkt onvolledig te zijn'
        ),
    'Section_missing': (
        '&sect;{nr}. <em>{ttl}</em> appears to be missing.',
        '&sect;{nr}. <em>{ttl}</em> lijkt te ontbreken.'
        ),
    'Section_too_short': (
        """&sect;{nr}. <em>{ttl}</em> appears to be too short
            ({cnt} words &lt; {min} minimum)""",
        """&sect;{nr}. <em>{ttl}</em> lijkt niet lang genoeg
            ({cnt} woorden &lt; {min} minimum)"""
        ),
    'File_too_big': ('File is too large', 'Bestand is te groot'),
    'File_exceeds_limit': (
        'File size ({size:3.2f} MB) exceeds upload limit of {max:2.1f} MB.',
        'Bestandsgrootte ({size:3.2f} MB) overschrijdt de limiet van {max:2.1f} MB.'
        ),
    'File_contains_comments': (
        'File contains "comments"',
        'Bestand bevat "opmerkingen"'
        ),
    'How_to_remove_comments': (
        """These comments contain author information, hence your work is not anonymous.
           Please remove all comments and then save your work as a new document as follows:
           <ol><li>Create a new (blank) document.</li>
           <li>Copy/paste your work into this new document.</li>
           <li>Save this document under a new name.</li></ol>""",
        """Opmerkingen (<em>Comments</em>) bevatten auteursinformatie waardoor je werk niet
           anoniem is. Verwijder a.j.b. alle opmerkingen en sla je werk als volgt op als een nieuw document:
           <ol><li>Maak een nieuw (leeg) document aan.</li>
           <li>Kopieer/plak je werk in dit nieuwe document.</li>
           <li>Sla dit document op onder een nieuwe naam.</li></ol>"""
        ),
    
    # phrases not related to estafette steps
    'Enroll': ('Enroll', 'Inschrijven'),
    'Enroll_in_course': ('Enroll in course', 'Inschrijven voor vak'),
    'Enrolled_on': (
        'You enrolled for {course} on {time}.',
        'Je hebt je voor {course} ingeschreven op {time}.'
        ),
    'About_to_enroll': (
        'You are about to enroll in course {course}.',
        'Je staat op het punt je in te schrijven voor {course}.'
        ),
    'Cancel': ('Cancel', 'Annuleren'),
    'Confirm': ('Confirm', 'Bevestigen'),
    'No_tasks_to_do': (
        'Presently, no tasks to do',
        'Momenteel geen taken om te doen'
        ),
    'Never_started': (
        'You did not start with this estafette',
        'Je bent in deze estafette niet van start gegaan'
        ),
    'You_are_referee': (
        'You are qualified to referee {n} steps of this relay.',
        'Je mag voor {n} stappen van deze estafette als scheidsrechter optreden.'
        ),
    'Project_Relay': ('Project Relay', 'ProjectEstafette'),
    'Progress_chart': ('Relay progress chart', 'Voortgangsgrafiek'),
    'Developed_at_TUD': (
        'Developed at Delft University of Technology',
        'Ontwikkeld aan de Technische Universiteit Delft'
        ),

    # headers, field and button labels, etc. (grouped by estafette task)

    # progress bar popup texts
    'Step_not_assigned': (
        '(proceed with step {})',
        '(doorgaan met stap {})'
        ),
    'Step_not_downloaded': (
        '(download predecessor\'s step {})',
        '(voorgangers stap {} downloaden)'
        ),
    'Step_not_reviewed': (
        '(review predecessor\'s step {})',
        '(voorgangers stap {} reviewen)'
        ),
    'Step_not_uploaded': (
        '(upload step {})',
        '(stap {} indienen)'
        ),
    'Review_not_downloaded': (
        '(download work for final review #{})',
        '(werk voor {}e afrondende review downloaden)'
        ),
    'Review_not_uploaded': (
        '(submit final review #{})',
        '({}e afrondende review indienen)'
        ),
    'Step_assigned': (
        'Step {nr} started on {time}',
        'Stap {nr} begonnen op {time}'
        ),
    'Step_downloaded': (
        'Predecessor\'s step {nr} downloaded on {time}',
        'Voorgangers stap {nr} gedownload op {time}'
        ),
    'Step_reviewed': (
        'Predecessor\'s step {nr} reviewed on {time}',
        'Voorgangers stap {nr} gereviewed op {time}'
        ),
    'Step_uploaded': (
        'Step {nr} uploaded on {time}',
        'Stap {nr} ingediend op {time}'
        ),
    'Review_downloaded': (
        'Work for final review #{nr} downloaded on {time}',
        'Werk voor {nr}e afrondende review gedownload op {time}'
        ),
    'Review_reviewed': (
        'Final review #{nr} submitted on {time}',
        'Afrondende review #{nr} ingediend op {time}'
        ),

    # past deadline and not finished
    'Past_deadline': (
        'The deadline for submissions is past',
        'De deadline voor het indienen van stappen is voorbij'
        ),
    'Past_review_deadline': (
        'The deadline for final reviews is past',
        'De deadline voor het indienen van eindreviews is voorbij'
        ),
    'Cannot_finish': (
        'This means that you cannot finish this relay.',
        'Dit betekent dat je deze estafette niet kunt uitlopen.'
        ),

    # start of relay
    'Commit_to_rules': (
        'I understand these principles and rules, and declare that I will respect and observe them.',
        'Ik begrijp deze principes en spelregels, en verklaar dat ik ze zal respecteren en er naar zal handelen.'
        ),

    # pose question to instructor (optional)
    'Pose_question': ('Pose a question', 'Stel een vraag'),
    'Can_pose_question': (
        'You can ask your instructor questions about this assignment',
        'Je kunt de docent vragen stellen over deze opdracht'
        ),
    'Question_submitted': ('Question submitted', 'Vraag ingediend'),
    'It_can_take_a_while': (
        'It may take some time, but you will receive an answer <strong>by e-mail</strong> a.s.a.p.',
        'Het kan even duren, maar je krijgt z.s.m. <strong>per e-mail</strong> antwoord.'
        ),

    # new assignment
    'Your_task': ('Your task for this step', 'Je opdracht voor deze stap'),
    'Case_has_attachment': (
        'Please also consider the attachment for this case.',
        'Bekijk a.j.b. ook de bijlage bij dit vraagstuk.'
        ),
    'Too_late_to_complete': (
        """Sorry, but for you the relay ends here. The minimum time for this
           step is {min} minutes, so by then you would not be allowed to
           submit your work.""",
        """Helaas! Je kunt deze estafette niet meer uitlopen. De minimumtijd
           voor deze stap is {min} minuten, dus zou je straks je werk niet
           meer mogen indienen."""
        ),
    'Download_header': (
        'Download your predecessor\'s Step {nr} &ndash; {name}',
        'Stap {nr} &ndash; {name} van je voorganger downloaden'
        ),
    'Final_download_header': (
        'Download Step {nr} &ndash; {name} &ndash; for final review',
        'Stap {nr} &ndash; {name} &ndash; downloaden voor afrondende review'
        ),
    'Download': ('Download', 'Downloaden'),
    'Download_all': ('Download all', 'Alles downloaden'),
    'You_may_decline': (
        """Since you have worked on this case before, you have the option to
           decline, and then wait until work on a different case becomes
           available.""",
        """Aangezien je al eerder aan dit vraagstuk hebt gewerkt, mag je ook
           passen en wachten tot werk m.b.t. een ander vraagstuk beschikbaar
           komt."""
        ),
    'Selfie_decline': (
        """Being a "frontrunner", you have the option: build on your own work,
           or decline and wait until work on a different case becomes
           available.""",
        """Als "koploper" heb je de keuze: voortbouwen op je eigen werk, of nu
           passen en wachten tot werk m.b.t. een ander vraagstuk beschikbaar
           komt."""
        ),
    'Decline_caution': (
        'NOTE: After viewing the present work, you can no longer decline!',
        'LET OP: Als je het nu aangeboden werk bekijkt kun je niet meer passen!'
        ),
    'Decline': ('Decline', 'Passen'),

    # submit own work
    'Submit_work': ('To submit your work', 'Je werk indienen'),
    'Upload_header': (
        'Upload step {nr} &ndash; {name}',
        'Stap {nr} &ndash; {name} &ndash; uploaden'
        ),
    'Upload': ('Upload', 'Uploaden'),
    'Steady_pace_bonus': (
        """If you upload before {time}, you gain half a star as bonus!""",
        """Als je je werk indient v&oacute;&oacute;r {time} win je een halve
           ster als bonus"""
        ),
    'View_review_instructions': (
        """You can use the review instructions for this step as a checklist
           for your own work.""",
        """Je kunt de review-instructies voor deze stap gebruiken als checklist
           voor je eigen werk."""
        ),
    'Show': ('Show', 'Tonen'),
    'Hide': ('Hide', 'Verbergen'),
    'Can_still_modify': (
        'Note that you can still modify your review!',
        'Je kunt je review nog steeds aanpassen!'
        ),
    'Modify_review': ('Modify review', 'Review aanpassen'),

    # proceed to next step
    'Proceed_header': (
        'Move on to step {nr} &ndash; {name}',
        'Nu verder naar stap {nr} &ndash; {name}'
        ),
    'Steps_ahead': (
        'You still have {nr} steps ahead!',
        'Je hebt nog {nr} stappen te gaan!'
        ),
    'One_more_step': (
        'You have only one more step to go!',
        'Je hebt nog maar &eacute;&eacute;n stap te gaan!'
        ),
    'Only_when_you_can': (
        """You should do this only if you intend to start working on the next
           step right away. If not, please wait until you <em>do</em> have the
           time, because this will keep the time that your predecessor will
           have for feedback as short as possible.""",
        """Doe dit a.j.b. alleen als je nu ook echt aan de volgende stap gaat
           werken. Zo niet, wacht dan tot je daar w&eacute;l de tijd voor hebt,
           want anders moet je voorganger onnodig lang wachten op feedback."""
        ),
    'Proceed': ('Proceed', 'Doorgaan'),

    # review predecessor's work
    'Review_header': (
        'Review your predecessor\'s step {nr} &ndash; {name}',
        'Stap {nr} &ndash; {name} &ndash; van je voorganger reviewen'
        ),
    'Final_review_header': (
        'Final review: Step {nr} &ndash; {name}',
        'Afrondende review: Stap {nr} &ndash; {name}'
        ),
    'Review_work': (
        'Review and appraise your predecessor\'s work',
        'Review en beoordeel het werk van je voorganger'
        ),
    'Specific_review_items': (
        'Specific review items',
        'Specifieke review items'
        ),
    'Overall_review': ('Overall review', 'Overall review'),
    'Self_review': ('self-review', 'zelfbeoordeling'),
    'View_pred_work': (
        'View your predecessor\'s work',
        'Werk van je voorganger bekijken'
        ),
    'Download_first': (
        """Note that you must view your predecessor's work
           before you can start writing your review.""",
        """Je moet het werk van je voorganger bekijken
           v&oacute;&oacute;rdat je je review kunt schrijven."""
        ),
    'Your_feedback': (
        'Feedback for your predecessor',
        'Feedback voor jouw voorganger'
        ),
    'Wordcount_left': (
        'You need to write at least ',
        'Minimaal '
        ),
    'Wordcount_right': (
        ' words before you can submit.',
        ' woorden, anders kun je niet indienen.'
        ),
    'Submit_review': ('Submit review',  'Review indienen'),
    'Reject': ('Reject', 'Verwerpen'),
    'Edit': ('Edit','Wijzigen'),
    'Save': ('Save','Opslaan'),
    'Please_save_this': (
        'Please save this text first',
        'Deze tekst eerst opslaan a.j.b.'
        ),
    'Minutes_to_submit': (
        'min. until you may submit',
        'min. voordat je mag indienen'
        ),
    'Your_rating': ('Your rating', 'Jouw beoordeling'),
    'Should_be_three_stars': (
        'NOTE: You must rate your own work with 3 stars.',
        'N.B. Je moet je eigen werk met 3 sterren waarderen.'
        ),
    'Rejection_rule': (
        'NOTE: For this step, you may choose to reject work of poor quality.',
        'N.B. Bij deze stap mag je werk van onvoldoende kwaliteit verwerpen.'
        ),
    'Predecessor_task': (
        'Your predecessor\'s task',
        'Je voorgangers opdracht'
        ),
    'Really_reject': (
        'Really reject your predecessor\'s work?',
        'Wil je je voorgangers werk inderdaad verwerpen?'
        ),
    'Reject_caution': (
        """If you do, you will be assigned another predecessor, and you will
           have to review his/her work before you can proceed.""",
        """In dat geval krijg je een andere voorganger toegewezen en moet je
           zijn/haar werk reviewen voordat je verder kunt."""
           ),

    # respond to review received from successor
    'Respond_header': (
        'Respond to review of your step {nr} &ndash; {name}',
        'Reageren op review van jouw stap {nr} &ndash; {name}'
        ),
    'Evaluated_by_successor': (
        'The work you submitted for this step has been evaluated by your successor.',
        'Het door jou ingeleverde werk is door je opvolger bekeken.'
        ),
    'Read_comments': (
        'Please read his/her comments attentively and with an open mind.',
        'Lees zijn/haar commentaar goed door. Sta daarbij open voor kritiek.'
        ),
    'Review_own_work': (
        'Then review your own work to verify your successor\'s critique.',
        'Bekijk vervolgens je eigen werk en ga na op welke punten je voorganger gelijk heeft.'
        ),
    'Compose_response': (
        'Finally, compose your response, and appraise the review.',
        'Formuleer je reactie zorgvuldig, en geef tenslotte je oordeel over de review.'
        ),
    'Appeal_rule': (
        'NOTE: You may appeal against an unfair review.',
        'N.B. Tegen een oneerlijke review kun je bezwaar aantekenen.'
        ),
    'Appeal_if_unfair': (
        'Should you consider the review to be unfair, you can appeal against it.',
        'Als je de review unfair vindt kun je er bezwaar tegen aantekenen.'
        ),
    'Your_task_was': (
        'Your task for this step was:',
        'Jouw opdracht voor deze stap was:'
        ),
    'View_own_work': ('View your own work', 'Bekijk je eigen werk'),
    'Successor_feedback': (
        'Feedback from your successor',
        'Feedback van je opvolger'
        ),
    'Successor_rating': (
        'Your successor\'s rating of your work',
        'Je opvolgers beoordeling van jouw werk'
        ),
    'Your_response': ('Your response', 'Jouw reactie'),
    'Your_appraisal': (
        'Your appraisal of the review',
        'Jouw beoordeling van de review'
        ),    
    'Appraise_review': (
        'Appraise your successor\'s review',
        'Beoordeel de review van je voorganger'
        ),
    'Respond': ('Submit response', 'Reactie indienen'),
    'Save_response': ('Save response', 'Reactie opslaan'),
    'Edit_response': ('Edit response', 'Reactie wijzigen'),
    'Submit_response': ('Submit response', 'Reactie indienen'),
    'Appeal': ('Appeal', 'Bezwaar aantekenen'),
    'Really_appeal': (
        """Really appeal against your successor\'s rating of your work?""",
        """Wil je inderdaad bezwaar aantekenen tegen de beooordeling van jouw
           werk door je opvolger?"""
        ),
    'Appeal_caution': (
        """If you do, your work, your successor\'s review, and your response
           will be assigned to a referee, who will judge whether your appeal
           is justified. If so, the rating may be adjusted, and your successor
           may incur a penalty point. If not, <strong>you</strong> may incur
           a penalty point.""",
        """In dat geval wordt jouw werk, de review door je voorganger, en jouw
           reactie daarop toegewezen aan een scheidsrechter die zal vaststellen
           of je bezwaar terecht is. Zo ja, dan wordt de beoordeling mogelijk
           aangepast en riskeert je opvolger een strafpunt. Zo niet, dan
           riskeer <strong>jijzelf</strong> een strafpunt."""
           ),
    'Has_been_rejected': (
        'Your successor has rejected your work',
        'Je opvolger heeft jouw werk verworpen'
        ),
    'No_follow_up': (
        'Hence there is no follow-up work for you to download.',
        'Vandaar dat je geen vervolgwerk is dat je kunt downloaden.'
        ),
    'Optional': ('(this is optional)', '(dit is optioneel)'),
    'View_successors_work': (
        'View your successor\'s work',
        'Bekijk werk van je opvolger'
        ),
    'Optional_comments': (
        'Your comments on the improvements made',
        'Jouw commentaar op de aangebrachte verbeteringen'
        ),
    'Your_opinion': (
        'What\'s your opinion on how your successor improved your work?',
        'Hoe vind je dat je opvolger je werk heeft verbeterd?'
        ),
    'Pass': ('Pass <em>(no comment)</em>', 'Geen commentaar'),
    'No_improvement': ('No improvement', 'Niet verbeterd'),
    'Minor_changes': ('Minor changes', 'Marginaal aangepast'),
    'Good_job': ('Good job', 'Goed werk'),
    'Does_not_invalidate': (
        """NOTE: If your successor did not improve your work, this does
           <strong>not</strong> imply that his/her critique is invalid!
           Hence do not use such lack of improvement as counter-argument or
           reason to appeal.""",
        """N.B. Als je opvolger je werk niet verbeterd heeft, betekent dat
           <strong>niet</strong> dat zijn/haar kritiek onjuist is! Gebruik
           het niet-verbeterd-hebben dus niet als tegenargument of als reden
           om bezwaar aan te tekenen."""
    ),
    'Word_count_for_appeal': (
        'Minimum of 30 words only applies when you appeal',
        'Minimum van 30 woorden geldt alleen indien je bezwaar aantekent'
        ),

    # acknowledge reception of predecessor's response to one's review
    'Acknowledge_header': (
        """Read your predecessor\'s response to your review of step {nr}
           &ndash; {name}""",
        """Reactie lezen van je voorganger op jouw review van stap {nr}
           &ndash; {name}"""
        ),
    'Details_in_history': (
        'You can find the case description in your project relay history.',
        'De casusbeschrijving vind je in je estafettegeschiedenis.'
        ),
    'Please_confirm_read': (
        'Please confirm that you have read your predecessor\'s response',
        'Bevestig a.j.b. dat je de reactie van je voorganger hebt gelezen.'
        ),
    'Predecessor_appealed': (
        """Note that your predecessor has appealed against your rating of
           his/her work.""",
        """N.B. Je voorganger heeft bezwaar aangetekend tegen jouw beoordeling
           van zijn/haar werk."""
        ),
    'Appraisal_acknowledged': ('Response acknowledged', 'Reactie bevestigd.'),
    'Step_is_history': (
        """You can review your interaction with your predecessor in your project
           relay history.""",
        """De interactie met je voorganger kun je terugzien in je
           estafettegeschiedenis."""
        ),
    'No_comment': (
        'Your predecessor made no comment on how you improved his/her work.',
        'Je voorganger gaf geen commentaar op hoe je zijn/haar werk hebt verbeterd.'
        ),
    'Opinion_on_sucessor_version': (
        'Your predecessor\'s opinion on your version of his/her work:',
        'Je voorganger\'s mening over jouw versie van zijn/haar werk:'
        ),
    'Unhappy': ('was unhappy with', 'was niet blij met'),
    'Mixed_feelings': (
        'had mixed feelings about',
        'had gemengde gevoelens over'
        ),
    'Quite_happy': ('was quite happy with', 'was blij met'),
    'Appraisal_header': (
        'Your predecessor {opinion} your review',
        'Je voorganger {opinion} jouw review'
        ),
    'Your_review': ('Your feedback', 'Jouw feedback'),
    'You_rejected': (
        'You rejected your predecessor\'s work',
        'Je hebt het werk van je voorganger verworpen'
        ),

    # appraise referee's decision on an appeal
    'Appraise_appeal_decision': (
        'Appraise referee decision',
        'Scheidsrechterbesluit beoordelen'
        ),
    'As_predecessor': ('as predecessor', 'als voorganger'),
    'As_successor': ('as successor', 'als opvolger'),
    'Appraise_appeal_header': (
        'Referee decision concerning step {nr} &ndash; {name}',
        'Besluit van scheidsrechter inzake stap {nr} &ndash; {name}'
        ),
    'Appeal_made_on': (
        'Predecessor appealed on',
        'Voorganger tekende bezwaar aan op'
        ),
    'Appeal_assigned_on': (
        'Assigned to referee on',
        'Aan scheidsrechter toegewezen op'
        ),
    'Appeal_first_viewed_on': (
        'Case opened on',
        'In behandeling genomen op'
        ),
    'Appeal_decided_on': (
        'Decision pronounced on',
        'Besluit bekend gemaakt op'
        ),
    'Duplicate_assigned_to': (
        'Same work has been assigned to referee {name}',
        'Ditzelfde werk eerder toegewezen aan scheidsrechter {name}'
        ),
    'Referee_prior_rating': (
        'Referee rating of prior steps the predecessor built on',
        'Scheidsrechterbeoordeling van eerdere stappen waar de voorganger op heeft voortgebouwd'
        ),
    'Referee_rating': (
        'Referee rating of the predecessor\'s work',
        'Scheidsrechterbeoordeling van het werk van de voorganger'
        ),
    'Appeal_review_in_history': (
        """NOTE: You can find the details on this appeal case in your
           project relay history.""",
        """N.B. Je kunt de details m.b.t. dit bezwaarschrift teruglezen in
           je estafette-geschiedenis."""
        ),
    'Please_appraise_decision': (
        'Please indicate how well you are satisfied with the referee\'s decision.',
        'Geef a.j.b. aan hoe tevreden je bent met het besluit van de scheidsrechter.'
        ),
    'Objection_rule': (
        'NOTE: You may object against an unjust decision.',
        'N.B. Tegen een onrechtvaardig besluit kun je beroep aantekenen.'
        ),
    'Object_if_unfair': (
        """Should you consider the referee\'s decision to be unjust, you can
           object against it.""",
        """Als je het besluit van de scheidsrechter onrechtvaardig vindt kun
           je ertegen in beroep gaan."""
        ),
    'No_objection_possible': (
        'NOTE: Formal objection is not possible, but your instructor values your opinion.',
        'N.B. Beroep is niet mogelijk, maar je docent stelt je mening op prijs.'
        ),
    'Refereed_by_instructor': (
        """NOTE: This decision has been made by your instructor. Please do
           appraise it, even if formal objection is now not possible.""",
        """N.B. Dit besluit is door je docent genomen. Geef a.j.b. je mening,
           ook al is hoger beroep nu niet mogelijk."""
        ),
    'Really_object': (
        'Really object against the referee\'s decision?',
        'Wil je inderdaad in beroep gaan tegen het besluit van de scheidsrechter?'
        ),
    'Objection_caution': (
        """If you do, your case will be reviewed by your instructor, who will
           make a final decision. If your objection is not justified, you may
           incur additional penalty points.""",
        """In dat geval wordt jouw beroep beoordeeld door je docent, die dan
           een bindende uitspraak zal doen. Als je ten onrechte beroep hebt
           aangetekend kan dat je extra strafpunten kosten."""
        ),
    'Referee_on_your_prior_work': (
        'Referee\'s rating of prior steps you built on',
        'Scheidsrechterbeoordeling van eerdere stappen waarop jij hebt voortgebouwd'
        ),
    'Referee_on_your_work': (
        'Referee\'s rating of your work',
        'Scheidsrechterbeoordeling van jouw werk'
        ),
    'Referee_on_pred_prior_work': (
        'Referee\'s rating of prior steps your predecessor built on',
        'Scheidsrechterbeoordeling van eerdere stappen waarop je voorganger heeft voortgebouwd'
        ),
    'Referee_on_pred_work': (
        'Referee\'s rating of your predecessor\'s work',
        'Scheidsrechterbeoordeling van het werk van je voorganger'
        ),
    'Referee_motivation': (
        'Referee\'s motivation',
        'Motivatie van de scheidsrechter'
        ),
    'Your_dec_appraisal': (
        'Your appraisal of this decision',
        'Jouw beoordeling van dit besluit'
        ),
    'Other_dec_appraisal': (
        'Appraisal by the other party',
        'Beoordeling door de andere partij'
        ),
    'Pred_dec_appraisal': (
        'Predecessor\'s appraisal of this decision',
        'Beoordeling van dit besluit door de voorganger'
        ),
    'Succ_dec_appraisal': (
        'Successor\'s appraisal of this decision',
        'Beoordeling van dit besluit door de opvolger'
        ),
    'Object': ('Make objection', 'Beroep aantekenen'),
    'Word_count_for_objection': (
        'Minimum of 30 words only applies when you object',
        'Minimum van 30 woorden geldt alleen indien je in beroep gaat'
        ),

    # phrases used in referee-appeal section
    'Referee_task': (
        'You volunteered to referee for ',
        'Je hebt je aangemeld als scheidsrechter voor '
        ),
    'Estafette_runs_from': (
        'This estafette runs from',
        'Deze estafette loopt van'
        ),
    'Deadline_for_decision': (
        'Deadline for decision',
        'Deadline voor besluit'
        ),
    'Decide_on_this_appeal': (
        'Decide on this appeal case',
        'Beslis inzake onderstaand bezwaar'
        ),
    'Decide_on_this_objection': (
        'Decide on this objection case',
        'Beslis over onderstaande beroepszaak'
        ),
    'Predecessors_task': ('Predecessor\'s task', 'Taak van de voorganger'),
    'Predecessor_work': ('Predecessor\'s work', 'Werk van de voorganger'),
    'Successor_review': (
        'Feedback written by the successor',
        'Feedback geschreven door de opvolger'
        ),
    'Successor_rejected': (
        'The successor rejected the predecessor\'s work',
        'De opvolger heeft het werk van de voorganger verworpen'
        ),
    'Feedback_appraisal_header': (
        'The predecessor {opinion} this review',
        'De voorganger {opinion} deze review'
        ),
    'Review_rating': ('Rating of the work', 'Beoordeling van het werk'),
    'Review_prior_rating': (
        'Rating of prior steps the predecessor built on',
        'Beoordeling van eerdere stappen waar de voorganger op heeft voortgebouwd'
        ),
    'Predecessor_appealed_on': (
        'The predecessor appealed on',
        'De voorganger heeft bezwaar aangetekend op'
        ),
    'Pred_opinion_succ_work': (
        'Predecessor\'s opinion on successor\'s work:',
        'Mening van voorganger over werk van opvolger:'
        ),
    'No_pred_comment': (
        'The predecessor made no comment on the successor\'s work.',
        'De voorganger heeft geen commentaar gegeven op het werk van de opvolger.'
        ),
    'Appeal_decision_task': (
        'You must decide wisely on this case',
        'Jij moet verstandig oordelen over deze zaak'
        ),
    'Pronounce_decision': ('Pronounce decision', 'Besluit bekend maken'),
    'Your_consideration': ('Your consideration', 'Jouw overweging'),
    'Save_decision': ('Save decision', 'Besluit opslaan'),
    'Edit_decision': ('Edit decision', 'Besluit wijzigen'),
    'Your_rating_of_pred_prior_work': (
        'Your rating of prior steps the predecessor built on',
        'Jouw beoordeling van eerdere stappen waar de voorganger op heeft voortgebouwd'
        ),
    'Your_rating_of_pred_work': (
        'Your rating of the predecessor\'s work',
        'Jouw beoordeling van het werk van de voorganger'
        ),
    'Motivation_instruction': (
        '(your motivation -- at least 20 words)',
        '(jouw overweging -- minimaal 20 woorden)'
        ),
    'Half_point_scale': (
        """Note that you can also give half point penalties (e.g., 0.5 or 1.5),
           and that negative numbers indicate bonus points.""",
        """N.B. Je kunt ook halve strafpunten opleggen (bijv. 0,5 of 1,5).
           Negatieve getallen geven bonuspunten weer."""
        ),
    'Predecessor_penalty': (
        'Predecessor&nbsp;penalty',
        'Strafpunten&nbsp;voorganger'
        ),
    'Successor_penalty': (
        'Successor&nbsp;penalty',
        'Strafpunten&nbsp;opvolger'
        ),
    'Penalty_for_predecessor': (
        '{pts}&nbsp;penalty point for the predecessor',
        '{pts}&nbsp;strafpunt voor de voorganger'
        ),
    'Bonus_for_predecessor': (
        '{pts}&nbsp;bonus point for the predecessor',
        '{pts}&nbsp;bonuspunt voor de voorganger'
        ),
    'Penalty_for_successor': (
        '{pts}&nbsp;penalty point for the successor',
        '{pts}&nbsp;strafpunt voor de opvolger'
        ),
    'Bonus_for_successor': (
        '{pts}&nbsp;bonus point for the successor',
        '{pts}&nbsp;bonuspunt voor de opvolger'
        ),
    'Sanctions': (
        '<strong>Sanctions:</strong> ',
        '<strong>Sancties:</strong> '
        ),
    'No_sanctions': (
        '<em>No sanctions.</em>',
        '<em>Geen sancties.</em>'
        ),
    'Appeal_case_decision': (
        'Appeal case decision',
        'Besluit inzake een bezwaarschrift'
        ),
    'Your_referee_decisions': (
        'Your referee decisions',
        'Jouw beslissingen als scheidsrechter'
        ),
    'Show_hide': ('Show/hide', 'Tonen/verbergen'),
    
    # phrases related to instructor reviews
    'Invite_to_post_review': (
        'Some assignments still need to be reviewed',
        'Sommige opdrachten moeten nog worden gereviewd'
        ),
    'Unassigned_assignments': (
        'Assignments requiring an instructor review',
        'Opdrachten die een docent-review nodig hebben'
        ),
    'Confirm_post_review': (
        'Do you indeed want to review this assignment?',
        'Wil je inderdaad deze opdracht reviewen?'
        ),
    'Post_review_info': (
        """Please do, because all assignments need to be (instructor) reviewed
           to compute the participant scores.""",
        """Dat zou fijn zijn, want alle opdrachten moeten een (docent)review
           hebben om de deelnemerscores te kunnen bepalen."""
        ),
    'Post_review_assigned': (
        'Instructor review assigned',
        'Docentreview toegewezen'
        ),
    'You_can_post_review': (
        'The new instructor review has been added to your task list.',
        'De nieuwe docentreview is aan je takenlijst toegevoegd.'
        ),
    'Assignment_under_review': (
        'Assignment already (being) reviewed by an instructor',
        'Opdracht wordt/is reeds gereviewd door een docent'
        ),
    'Instructor_review_header': (
        'Instructor review: Step {nr} &ndash; {name}',
        'Docentreview: Stap {nr} &ndash; {name}'
        ),
    
    # phrases used in student.py related to appeal assignment to referee
    'Invite_to_referee': (
        'You are invited to act as referee',
        'Je wordt uitgenodigd om als scheidsrechter op te treden'
        ),
    'Unassigned_appeals': (
        'Appeal cases that still need a referee',
        'Bezwaarschriften waar een scheidsrechter voor wordt gezocht'
        ),
    'Confirm_referee': (
        'Do you indeed volunteer to referee this case?',
        'Wil je inderdaad scheidsrechter zijn in deze zaak?'
        ),
    'Referee_caution': (
        """<strong>Note:</strong> By confirming this, you commit to seriously
           reviewing the work, and then justly deciding on this case within
           48 hours!""",
        """<strong>Let op:</strong> Door dit te bevestigen verplicht je je tot
           het serieus bekijken van het werk, en vervolgens binnen 48 uur een
           eerlijk oordeel uit te spreken over deze zaak!"""
        ),
    'Appeal_list_caution': (
        """<strong>Note:</strong> You should only commit to refereeing an
           appeal if you can do this within 48 hours!""",
        """<strong>Let wel:</strong> Je moet een zaak alleen op je nemen
           indien je er binnen 48 uur over kunt oordelen!"""
        ),

    # phrases used in student.py related to objection assignment to instructor
    'You_may_decide': (
        'You may decide on objections',
        'Je kunt beslissen over beroepszaken'
        ),
    'Unassigned_objections': (
        'Objections that still need to be decided',
        'Beroepszaken waarover nog besloten moet worden'
        ),
    'Confirm_decide': (
        'Do you indeed want to decide on this objection?',
        'Wil je inderdaad beslissen over deze beroepszaak?'
        ),
    'Decide_caution': (
        """<strong>Note:</strong> By confirming this, you commit to seriously
           reviewing the work and the referee's decision, and then justly
           deciding on this case within 48 hours!""",
        """<strong>Let op:</strong> Door dit te bevestigen verplicht je je
           tot het serieus bekijken van het werk en de uitspraak van de
           scheidsrechter, en vervolgens binnen 48 uur een eerlijk oordeel
           uit te spreken over deze zaak!"""
        ),
    'Objection_list_caution': (
        """<strong>Note:</strong> You should only commit to deciding on an
           objection if you can do this within 48 hours!""",
        """<strong>Let wel:</strong> Je moet een beroepszaak alleen op je
           nemen indien je er binnen 48 uur over kunt oordelen!"""
        ),

    # additional phrases used in the History view
    'History_of': ('History of', 'Geschiedenis van'),
    'Your_last_action': ('Your last action was on', 'Je laatste actie was op'),
    'Step_header': ('Step {nr} &ndash; {name}',  'Stap {nr} &ndash; {name}'),
    'Assigned_to_you': (
        'Assigned to you on ',
        'Opdracht aan jou toegewezen op '
        ),
    'Review_instructions_for_prior_steps': (
        'Review instructions for prior steps',
        'Reviewinstructies voor eerdere stappen'
        ),
    'Review_instructions_for_step': (
        'Review instructions for this step',
        'Reviewinstructies voor deze stap'
        ),
    'You_uploaded': (
        'You uploaded your work on ',
        'Je hebt je werk ingediend op '
        ),
    'You_downloaded_on': (
        'You first downloaded your predecessor\'s work on',
        'Je hebt je voorganger\'s werk voor het eerst gedownload op'
        ),
    'You_reviewed_on': (
        'You reviewed your predecessor\'s work on',
        'Je hebt je voorganger\'s werk gereviewd op'
        ),
    'Your_opinion_on_improvement': (
        'Your opinion on your successor\'s work: ',
        'Jouw mening over het werk van je voorganger: '
        ),
    'Your_appraisal_header': (
        'You {opinion} your successor\'s review',
        'Jij {opinion} de review door jouw opvolger'
        ),
    'You_unhappy': ('were unhappy with', 'was niet blij met'),
    'You_quite_happy': ('were quite happy with', 'was blij met'),
    'You_must_respond': (
        'You still need to respond to this review.',
        'Je moet nog op deze review reageren.'
        ),
    'You_responded_on': ('You responded on', 'Je hebt gereageerd op'),
    'You_have_appealed': (
        'You have appealed against your successor\'s review',
        'Je hebt tegen deze review bezwaar aangetekend'
        ),
    'Optional_comment': (
        '(optional comment)',
        '(toelichting is niet verplicht)'
        ),
    'You_acknowledged_on': (
        'You acknowledged having read this response on',
        'Je heb bevestigd dat je deze reactie hebt gelezen op'
        ),
    'Final_reviews_after_step': (
        'Final review phase starts after the deadline for the last step',
        'Afrondende reviewfase start pas na de deadline voor de laatste stap'
        ),
    'Explain_final_reviews_after_step': (
        """To give all participants the same amount of time to write final
           reviews, work comes available only after the assignments
           deadline.""",
        """Om alle deelnemers dezelfde hoeveelheid tijd voor het schrijven van
           eindreviews te geven komt werk pas beschikbaar nadat de deadline
           voor opdrachten is verstreken."""
        ),
    'No_final_reviews': (
        'No work available for final review',
        'Nog geen werk beschikbaar voor laatste review'
        ),
    'One_final_review': (
        'You still need to write one final review',
        'Je moet nog &eacute;&eacute;n afrondende review schrijven'
        ),
    'Several_final_reviews': (
        'You still need to write {n} final reviews',
        'Je moet nog {n} afrondende reviews schrijven'
        ),
    'Please_wait': (
        """It may take some time before suitable work of a predecessor comes
           available. Please wait.""",
        """Het kan even duren voordat geschikt werk van een voorganger
           beschikbaar komt. Nog even geduld a.j.b."""
        ),
    'Finished': ('Finished!', 'Gehaald!'),
    'Congratulations': (
        'You\'ve reached the finish! Congratulations!',
        'Je hebt de eindstreep gehaald! Gefeliciteerd!'
        ),
    'You_have_finished': (
        'You completed all assignments for this project relay in time.',
        'Je hebt alle estafette-opdrachten binnen de gestelde termijn uitgevoerd.'
        ),
    'Keep_logging_on': (
        """<em><strong>Please note</strong>: You should still check in
           regularly to see whether you need to respond to reviews,
           etcetera.</em>""",
        """<em><strong>Let op</strong>: Log a.j.b. nog wel regelmatig in om te
           zien of je nog moet reageren op reviews en dergelijke.</em>"""
        ),
    'Instructor_judgement': (
        'Instructor\'s judgement',
        'Oordeel van de docent'
        ),
    'Instructor_prior_rating': (
        'Instructor\'s rating of prior steps',
        'Beoordeling door de docent van eerdere stappen'
        ),
    'Instructor_rating': (
        'Instructor\'s rating',
        'Beoordeling door de docent'
        ),
    
    # phrases related to partnerships
    'Teamed_up_with': ('Teamed up with:', 'Werkt samen met:'),
    'Leads_team_with': ('Leads team with:', 'Leidt team met:'),
    'Until': ('Until', 'Tot'),
    'Team_rules': (
"""
<h4>You have formed a team with other participants</h4>
<ul>
<li>
  As team member, you must contribute to the team work to the best of your ability, and
  ensure that your contribution is indeed your fair share of the assigned work load.
</li>
<li>
  As team, you jointly bear the responsibility for ALL actions you and/or your fellow
  team members perform in this relay. This means that if you fail to comply with the
  principles and rules stated above, this will also affect your fellow team members.
</li>
</ul>
""",
"""
<h4>Je hebt samen met andere deelnemers een team gevormd</h4>
<ul>
<li>
  Als teamlid moet je naar beste vermogen bijdragen aan het in te leveren werk, en
  ervoor zorgen dat jouw bijdrage een eerlijk aandeel vormt van dat werk.
</li>
<li>
  Als team dragen jullie gezamenlijk de verantwoordelijkheid voor alle handelingen
  die je in deze estafette verricht. Dit betekent dat indien je je niet houdt aan de
  hierboven beschreven principes en regels, dit ook gevolgen heeft voor je teamgenoten.
</li>
</ul>
"""
        ),

    # rules of the game as multi-line strings
    'Rules_of_the_game': (
"""
<h2>Rules concerning participation in a Project Relay</h2>
<p>
  To start with this relay, you must first declare yourself to be bound by the following
  principles and rules:
</p>
<ol>
<li>
  <em>Do what you must do.</em> The work that you submit must fulfill the assignment.
  In each step, you should not do more than the specific task that is assigned to you
  (leave that to your successors). But neither should you submit a sloppy
  or incomplete elaboration of that step (because that puts a double load on your successor).
  No time or inspiration? Then quit (i.e., do not upload any files) because in that way, you
  harm nobody. Uploading an &quot;empty&quot; step (i.e., with nothing meaningful added to the
  predecessors' work) will lead to disqualification!
</li>
<li>
  <em>Do not plagiarize.</em> The work that you submit must be your own work. Insofar as you build
  on the work of someone else, this must be the work of your immediate predecessor in the relay,
  not that of any other participant. Any work you upload should contain a significant part written
  by you alone. When citing other sources, you should provide full references (in APA style). 
</li>
<li>
  <em>Respect anonimity.</em> You must take care that your successor does not find out on whose work
  s/he is building. You must not attempt to find out the identity of your predecessors or your
  successors.
</li>
<li>
  <em>Appraise fairly.</em> Your appraisal of other participants' work should match the quality of
  that work as closely as possible. The feedback that you give to motivate your appraisal must be
  constructive, and politely phrased.
</li>
<li>
  <em>Do not sabotage.</em> The software system that supports this project relay is still in
   development, and vulnerable. Follow instructions, and report errors immediately to your
   course instructor.
</li>
</ol>
""",

"""
<h2>Regels m.b.t. deelname aan de Project-Estafette</h2>
<p>
  Om met deze estafette te kunnen starten moet je je eerst verbinden aan de
  volgende principes en spelregels:
</p>
<ol>
<li>
  <em>Doen wat je moet doen.</em> Het werk dat je indient moet (in elk geval in jouw ogen) aan de
  opdracht voldoen. Ga niet verder dan de jou opgedragen projectstap (dat is werk voor je opvolgers)
  maar dien ook geen halfbakken uitwerking in (want dan zadel je je opvolger op met een dubbele
  opdracht). Geen tijd, zin of inspiratie? Stap dan gewoon uit (d.w.z. upload geen bestanden).
  Wie een &quot;lege&quot; stap indient diskwalificeert zich voor de estafette als werkvorm.
</li>
<li>
  <em>Niet plagi&euml;ren.</em> Het werk dat je indient is moet je eigen werk zijn. Als je
  voortbouwt op het werk van een ander, dan is dat het werk van je directe voorganger in de
  estafette, en heb je daar een significante bijdrage aan geleverd. Als je informatie (tekst,
  figuren, foto's) van derden gebruikt, dan moet je de bron correct en volledig vermelden.
</li>
<li>
  <em>Anonimiteit respecteren.</em> Je moet er voor zorgdragen dat je opvolger niet te weten komt
  op wiens werk hij voortbouwt. Je mag niet proberen om de identiteit van je voorgangers of
  opvolgers te achterhalen.
</li>
<li>
  <em>Fair beoordelen.</em> Je beoordeling van andermans werk moet de kwaliteit van dat werk zo goed
  mogelijk weergeven. De kritiek die je ter onderbouwing van je oordeel moet geven moet opbouwend
  en beleefd gesteld zijn.
</li>
<li>
  <em>Niet saboteren.</em> Het softwaresysteem dat de projectestafette mogelijk maakt is beperkt
  getest en kwetsbaar. Houd je aan de instructies en meld storingen meteen bij je docent.
</li>
</ol>
"""
        ),
    
    'Appeal_decision_rules': (
"""
<p>Please observe these guidelines when deciding on this case:</p>
<ol>
<li>
  <em>You must <strong>always</strong> appraise the predecessor's work.</em> Your rating must
  reflect the quality of the predecessor's work, independent of any comments made by either party.
</li>
<li>
  <em>An appeal must be duly motivated.</em> If the predecessor provides no substantive arguments,
  s/he loses the case and incurs a penalty point.
</li>
<li>
  <em>The successor's judgement must be reasoned and fair.</em> If the successor's critique does
  not warrant the rating (e.g., because the critique is incorrect, incomplete, or unclear),
  the successor loses the case, and incurs a penalty point.
</li>
<li>
  <em>Demonstration of knowledge should be rewarded</em>. Penalty points may be waived if
  participants by their argumentation show good understanding of the subject matter.
</li>
<li>
  <em>Strategic behavior should be discouraged.</em> If a rating is evidently unfair, you may
  impose an additional penalty point. 
</li>
</ol>
""",

"""
<p>Richtlijnen voor besluitvorming over een bezwaarschrift:</p>
<ol>
<li>
  <em>Je moet het werk van de voorganger <strong>altijd</strong> inhoudelijk beoordelen.</em>
  Je beoordeling (1-5 sterren) moet recht doen aan de kwaliteit van dat werk, geheel los van
  de opmerkingen van de bij het bezwaar betrokken partijen.
</li>
<li>
  <em>Een bezwaar moet voldoende gemotiveerd zijn.</em> Indien de voorganger geen inhoudelijke
  argumenten aanvoert, verliest hij/zij de zaak en krijgt een strafpunt.
</li>
<li>
  <em>De beoordeling door de opvolger moet argumentatief en fair zijn.</em> Als de kritiek van de
  opvolger de gegeven sterrenbeoordeling niet rechtvaardigt (bijv. omdat die kritiek onjuist,
  onvolledig of onduidelijk is), verliest de opvolger de zaak en krijgt een strafpunt.
</li>
<li>
  <em>Kennis van zaken moet worden beloond.</em> Als deelnemers met hun argumentatie laten zien dat
  ze de vakinhoud goed beheersen, is dat reden om geen (of minder) strafpunten toe te kennen.
</li>
<li>
  <em>Strategisch gedrag moet ontmoedigd worden.</em> Als een beoordeling apert oneerlijk is, mag
  je een extra strafpunt opleggen. 
</li>
</ol>
"""
        )

# END OF PHRASE_DICT
}

# Content is scanned for phrases that may indicate abusive content:
UI_BLACKDICT = {
    'en-US': [
        
    ],
    'nl-NL': [
        'aansteller', 'achterlijk',
        'bash', 'bitch', 'b1tch', 'b!tch', ' but',
        ' duf', ' dom ', 'domm', ' donder ',
        'eikel',
        'fakki', 'flikker', ' fok', 'fokken', 'fokking', 'fuck', 'f*ck', ' fck',
        'geil ', 'geile', 'godver',
        'hoer', 'homo', 'hufter',
        'idioot', 'idiote', 'imbeciel', 'infantiel',
        'jank',
        'kanker', 'kech', 'kinderachtig', 'kinderlijk', 'kletsen', 'klere',
            'kloot', 'klote', 'kl0te', 'kl*te', 'kolere', 'kramen '
            'kut', 'k*t', 'ktt', 'k&#', 'kwijl',
        'leuter', 'lous', 'luiz', 'lul', '!u!', '1u1',
        'mekker', ' miere', 'mongool',
        'naaid', 'naaie', 'neuk', ' nicht',
        ' onzin ', 'ophoepel',
        ' pest', ' pis',
        'queer',
        '5h1t', 'schijt', 'shit', 'sh!t', 'sh1t', 'slakken', 'slap', 'slijm',
            'stom', 'stront', 'suf',
        ' takke', 'teef', ' tering', 'tjeef', 'tsjeef', ' trol', 'trut', 'tyfus',
        'uitslov',
        ' vies ', ' vieze',
        'wauwel',
        'een zak ', 'zakkerig', 'zakkig', 'zanik', 'zeik', 'ze!k''z31k', 'zemel', 'zeur',
            ' ziek', 'zielig', 'zijk '
    ]
}
