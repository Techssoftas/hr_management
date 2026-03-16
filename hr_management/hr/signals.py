from django.db.models import Sum, F, Min, Max
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import DailySalaryEntry, MonthlySalarySummary, AdvancePayment, Employee
from decimal import Decimal


def update_monthly_summary_for_entry(employee, year, month):
    """
    Recalculate and save MonthlySalarySummary for this employee and month.

    - Finds ALL DailySalaryEntry rows for that employee in that year+month.
    - Ensures exactly ONE MonthlySalarySummary row for that employee+month.
    - Sets MonthlySalarySummary.date to the LAST worked date in that month.
    """
    from datetime import date

    # All daily entries for this employee in that month (no monthrange needed)
    entries = DailySalaryEntry.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month,
        is_active=True,
    )

    # Find existing summary for that month (regardless of current date value)
    summary = MonthlySalarySummary.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month,
    ).first()

    # Track whether we are creating a brand-new summary in this call.
    is_new_summary = summary is None

    # If none exists yet, create one with a temporary date = first day of month
    if is_new_summary:
        first_day = date(year, month, 1)
        summary = MonthlySalarySummary(
            employee=employee,
            date=first_day,
            is_paid=False,  # or just rely on default
        )

    if entries.exists():
        stats = entries.aggregate(
            s_shifts=Sum('shift_value'),
            s_hours=Sum(F('worked_hours') + F('ot_hours')),
            s_money=Sum('amount_earned'),
        )
        summary.total_days = entries.count()
        summary.total_shifts_worked = stats['s_shifts'] or 0
        summary.total_hours_worked = stats['s_hours'] or 0
        summary.gross_salary = stats['s_money'] or 0

        # Range of worked dates in this month
        date_range = entries.aggregate(min_date=Min('date'), max_date=Max('date'))
        min_date, max_date = date_range['min_date'], date_range['max_date']

        if min_date is not None and max_date is not None:
            # Set summary.date = LAST worked date (e.g. 3rd)
            summary.date = max_date

            # For a brand-new summary, initialize advance_deducted from
            # all existing advances in that month. Afterwards, only the
            # AdvancePayment signals will adjust it incrementally.
            if is_new_summary:
                first_day = date(year, month, 1)
                advances_sum = AdvancePayment.objects.filter(
                    employee=employee,
                    date_given__gte=first_day,
                    date_given__lte=max_date,
                    is_active=True,
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                summary.advance_deducted = advances_sum
        # Pull ESI/PF amounts from the employee into the monthly summary
        if not summary.is_paid:
            summary.esi_amount = employee.esi_amount or 0
            summary.pf_amount = employee.pf_amount or 0

        # Only compute net_payable automatically when creating a new summary.
        # After that, AdvancePayment signals and manual edits may adjust it.
        if is_new_summary:
            raw_net = (summary.gross_salary or 0) - (summary.advance_deducted or 0)
            summary.net_payable = max(Decimal("0"), raw_net)
    else:
        # No entries in that month: zero out fields
        summary.total_days = 0
        summary.total_shifts_worked = 0
        summary.total_hours_worked = 0
        summary.gross_salary = 0
        # Do not touch advance_deducted or net_payable here, because
        # they may already reflect prior advances and manual adjustments.
        summary.esi_amount = 0
        summary.pf_amount = 0
        # date can stay as first_day or whatever it had; no entries anyway

    summary.save()


@receiver(post_save, sender=DailySalaryEntry)
def on_daily_entry_save(sender, instance, created, **kwargs):
    """When a daily entry is added or updated, refresh the monthly summary."""
    update_monthly_summary_for_entry(
        instance.employee,
        instance.date.year,
        instance.date.month,
    )


@receiver(post_delete, sender=DailySalaryEntry)
def on_daily_entry_delete(sender, instance, **kwargs):
    """When a daily entry is deleted, refresh the monthly summary."""
    update_monthly_summary_for_entry(
        instance.employee,
        instance.date.year,
        instance.date.month,
    )


def _get_monthly_summary_for_advance(advance: AdvancePayment):
    """
    Find the MonthlySalarySummary for the same employee and month
    as this advance (if it exists).
    """
    return MonthlySalarySummary.objects.filter(
        employee=advance.employee,
        date__year=advance.date_given.year,
        date__month=advance.date_given.month,
        is_active=True,
    ).first()


@receiver(pre_save, sender=AdvancePayment)
def store_old_advance_amount(sender, instance, **kwargs):
    """
    Before saving an advance, remember its previous amount and active flag (if any)
    so post_save can apply only the difference when updating, and detect soft deletes.
    """
    from decimal import Decimal as _D

    if instance.pk:
        try:
            old = AdvancePayment.objects.get(pk=instance.pk)
            instance._old_amount = old.amount or _D("0")
            instance._old_is_active = old.is_active
        except AdvancePayment.DoesNotExist:
            instance._old_amount = _D("0")
            instance._old_is_active = False
    else:
        instance._old_amount = _D("0")
        instance._old_is_active = False


@receiver(post_save, sender=AdvancePayment)
def on_advance_save(sender, instance, created, **kwargs):
    """
    When an advance is added, increase advance_deducted and
    recompute net_payable from gross_salary - advance_deducted.
    """
    summary = _get_monthly_summary_for_advance(instance)
    if not summary:
        return

    # Detect soft delete: was active, now set to inactive.
    if not created:
        old_is_active = getattr(instance, "_old_is_active", True)
        if old_is_active and not instance.is_active:
            # Treat this as a delete: reverse the full old amount.
            delta_del = getattr(instance, "_old_amount", None)
            if delta_del is None:
                delta_del = Decimal("0")

            # Reduce advance_deducted (not below 0)
            current_adv = summary.advance_deducted or Decimal("0")
            new_adv = current_adv - delta_del
            if new_adv < 0:
                new_adv = Decimal("0")
            summary.advance_deducted = new_adv

            # Increase net_payable by the deleted amount, preserving manual edits.
            current_net = summary.net_payable or Decimal("0")
            summary.net_payable = current_net + delta_del

            summary.save()
            return

    new_amount = instance.amount or Decimal("0")

    if created:
        # First time this advance is created: whole amount is the delta.
        delta = new_amount
    else:
        # Update: apply only the difference between new and old amount.
        old_amount = getattr(instance, "_old_amount", None)
        if old_amount is None:
            old_amount = Decimal("0")
        delta = new_amount - old_amount

    # Adjust advance_deducted by the delta
    current_adv = summary.advance_deducted or Decimal("0")
    new_adv = current_adv + delta
    summary.advance_deducted = new_adv

    # Recompute net_payable from scratch so it doesn't depend on any
    # previous net_payable value that might have been 0 or manually edited.
    raw_net = (summary.gross_salary or 0) - new_adv
    summary.net_payable = max(Decimal("0"), raw_net)

    summary.save()


@receiver(post_delete, sender=AdvancePayment)
def on_advance_delete(sender, instance, **kwargs):
    """
    When an advance is deleted, reduce advance_deducted and
    increase net_payable by the deleted amount.
    This preserves any manual edits the user made to net_payable.
    """
    summary = _get_monthly_summary_for_advance(instance)
    if not summary:
        return

    delta = instance.amount or Decimal("0")

    # Reduce advance_deducted (not below 0)
    current_adv = summary.advance_deducted or Decimal("0")
    new_adv = current_adv - delta
    if new_adv < 0:
        new_adv = Decimal("0")
    summary.advance_deducted = new_adv

    # Increase net_payable by the deleted advance amount,
    # so that any manual changes to net_payable are respected.
    current_net = summary.net_payable or Decimal("0")
    summary.net_payable = current_net + delta

    summary.save()


@receiver(post_save, sender=Employee)
def on_employee_save(sender, instance, **kwargs):
    """
    When an employee's ESI/PF amounts change, update all unpaid monthly
    summaries for that employee to reflect the new amounts and recompute
    net_payable.
    """
    unpaid_summaries = MonthlySalarySummary.objects.filter(
        employee=instance,
        is_paid=False,
    )
    for summary in unpaid_summaries:
        summary.esi_amount = instance.esi_amount or 0
        summary.pf_amount = instance.pf_amount or 0
        # Net payable after advances only (no ESI/PF deduction) and never negative
        raw_net = (summary.gross_salary or 0) - (summary.advance_deducted or 0)
        summary.net_payable = max(Decimal("0"), raw_net)
        summary.save()