from django.db.models import Sum, F, Min, Max
from django.db.models.signals import post_save, post_delete
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

    # If none exists yet, create one with a temporary date = first day of month
    if not summary:
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

            # Advances for the whole month up to the last worked date
            first_day = date(year, month, 1)
            advances_sum = AdvancePayment.objects.filter(
                employee=employee,
                date_given__gte=first_day,
                date_given__lte=max_date,
                is_active=True,
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            summary.advance_deducted = advances_sum
        else:
            summary.advance_deducted = 0
        # Pull ESI/PF amounts from the employee into the monthly summary
        if not summary.is_paid:
            summary.esi_amount = employee.esi_amount or 0
            summary.pf_amount = employee.pf_amount or 0

        # Net payable after advances only (no ESI/PF deduction) and never negative
        raw_net = (summary.gross_salary or 0) - (summary.advance_deducted or 0)
        summary.net_payable = max(Decimal("0"), raw_net)
    else:
        # No entries in that month: zero out fields
        summary.total_days = 0
        summary.total_shifts_worked = 0
        summary.total_hours_worked = 0
        summary.gross_salary = 0
        summary.advance_deducted = 0
        summary.esi_amount = 0
        summary.pf_amount = 0
        summary.net_payable = 0
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