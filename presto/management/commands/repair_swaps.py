# Software developed for the PrESTO project -- see http://presto.tudelft.nl/wiki
# Copyright (c) 2017-2022 by Pieter Bots. All rights reserved.

from django.conf import settings
from django.core.management.base import BaseCommand

from presto.models import PeerReview, DEFAULT_DATE

# find peer reviews with invalid swaps
class Command(BaseCommand):

    def handle(self, *args, **options):
        # switch off, as this script has served its purpose (more or less)
        return

        revs_to_repair = []
        assignments = []
        for pr in PeerReview.objects.filter(reviewer__estafette__id=27,
            assignment__successor__isnull=False).exclude(
            assignment__successor__participant__student__id=643
        ):
            if (pr.assignment.successor.participant != pr.reviewer):
                revs_to_repair.append(pr)
                assignments.append(pr.assignment)
                # NOTE: the assignment key of a flawed review is incorrect;
                #       the correct assignment is the one having the reviewer
                #       as successor participant (and the same step!)
        print(len(revs_to_repair), 'flawed reviews')
        pairs = []
        for pr in revs_to_repair:
            for a in assignments:
                if a.successor.participant == pr.reviewer and a.leg == pr.assignment.leg:   
                    print(
                        'MATCH: review {} now pointing to {} should point to assignment {}\n'.format(
                            pr,
                            pr.assignment,
                            a
                            )
                        )
                    pairs.append((pr, a))
                    break
        quartets = []
        for pr in revs_to_repair:
            for p in pairs:
                if pr.assignment == p[1]:
                    quartets.append((p[0], pr, p[1], p[0].assignment))
                    break
        print(len(quartets), 'swaps envisioned\n\n')
        # filter out doubles
        to_undo = []
        for q in quartets:
            # if both reviewers have uploaded THEIR step, then UNDO the original clone swap
            if (q[0].assignment.successor.time_uploaded != DEFAULT_DATE
                and q[1].assignment.successor.time_uploaded != DEFAULT_DATE
            ):
                double = False
                for tu in to_undo:
                    if tu[0] == q[1] and tu[1] == q[0]:
                        double = True
                        break
                if not double:
                    to_undo.append(q)
           
        print(len(to_undo), 'UNDOs envisioned\n\n')
        
        for tu in to_undo:
            print('Swap to UNDO:\n')
            print('A) {} DID review {}'.format(tu[0].reviewer, tu[0].assignment))
            print('B) {} DID review {}'.format(tu[1].reviewer, tu[1].assignment))
            print('So we restore the successor pointers:')
            s0 = tu[0].assignment.successor
            s1 = tu[1].assignment.successor
            print('A) {} will point again to {}'.format(tu[0].assignment, s1))
            print('B) {} will point again to {}'.format(tu[1].assignment, s0))
            tu[0].assignment.successor = s1
            tu[0].assignment.save()
            tu[1].assignment.successor = s0
            tu[1].assignment.save()
