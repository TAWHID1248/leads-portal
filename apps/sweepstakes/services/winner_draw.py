"""Pick a winner from a sweepstakes' entry pool. Honors min_age (from DOB,
if known) and target_state. Skips leads that already won another sweepstakes."""

import random
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.leads.models import Lead
from apps.sweepstakes.models import Sweepstakes


def _age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_entry(lead, sweepstakes):
    if lead.sweepstakes_id != sweepstakes.id:
        return False
    if sweepstakes.target_state and lead.state.upper() != sweepstakes.target_state.upper():
        return False
    age = _age(lead.date_of_birth)
    if age is None:
        # DOB unknown — accept (some campaigns don't collect DOB)
        return True
    return age >= (sweepstakes.min_age or 18)


@transaction.atomic
def draw_winner(sweepstakes_id):
    sweepstakes = Sweepstakes.objects.select_for_update().get(pk=sweepstakes_id)
    if sweepstakes.winner_lead_id:
        return sweepstakes.winner_lead

    pool = list(
        Lead.objects
        .filter(sweepstakes_id=sweepstakes.id, won_sweepstakes__isnull=True)
        .only('id', 'date_of_birth', 'state', 'sweepstakes_id')
    )
    eligible = [lead for lead in pool if validate_entry(lead, sweepstakes)]
    if not eligible:
        return None

    winner = random.choice(eligible)
    sweepstakes.winner_lead = winner
    sweepstakes.winner_drawn_at = timezone.now()
    sweepstakes.status = Sweepstakes.Status.DRAWN
    sweepstakes.save(update_fields=['winner_lead', 'winner_drawn_at', 'status'])
    return winner
