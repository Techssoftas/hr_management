from django.db import models
import calendar
from decimal import Decimal
from .utils import *
from django.db.models import Q
from datetime import date

# 1. This is a "Base Class". It won't create a table itself, 
# but it adds these 3 columns to every other table.
class BaseModel(models.Model):
    is_active = models.BooleanField(default=True, help_text="Uncheck this if the employee leaves or the record is disabled.")
    created_at = models.DateTimeField(auto_now_add=True) # Automatically set when created
    updated_at = models.DateTimeField(auto_now=True)     # Automatically updates every time you save

    class Meta:
        abstract = True

# 2. Now, all your tables "Inherit" from BaseModel
class Shift(BaseModel):
    shift_value = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    standard_hours = models.PositiveIntegerField(default=8)

    class Meta:
        ordering = ["shift_value"]
        constraints = [
            models.UniqueConstraint(
                fields=['shift_value'],
                condition=Q(is_active=True),
                name='unique_active_shift_value',
            ),
        ]

    def __str__(self):
        return f"{self.shift_value} ({self.standard_hours} hrs)"

class Designation(BaseModel):
    SALARY_TYPE_CHOICES = [('DAILY', 'Daily'), ('MONTHLY', 'Monthly')]
    name = models.CharField(max_length=100)
    salary_type = models.CharField(max_length=10, choices=SALARY_TYPE_CHOICES)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=Q(is_active=True),
                name='unique_active_designation_name',
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_salary_type_display()})"

class Employee(BaseModel):
    employee_id = models.CharField(max_length=10, unique=True, blank=True)
    employee_name = models.CharField(max_length=150)
    designation = models.ForeignKey(
        Designation, on_delete=models.RESTRICT, related_name='employees'
    )
    date_of_joining = models.DateField()

    # Extra personal / HR info
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    education_qualification = models.CharField(max_length=255, blank=True)
    end_date = models.DateField(null=True, blank=True)

    contact_number = models.CharField(max_length=15)
    blood_group = models.CharField(max_length=5, blank=True)
    has_esi_pf = models.BooleanField(default=False)

    # Files with size validation
    # Media & Docs (Condensed)
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True, validators=[validate_photo_size])
    
    # All PDFs on single lines
    aadhaar_pdf = models.FileField(upload_to='employee_docs/aadhaar/', null=True, blank=True, validators=[validate_pdf_size])
    pan_pdf = models.FileField(upload_to='employee_docs/pan/', null=True, blank=True, validators=[validate_pdf_size])
    passbook_pdf = models.FileField(upload_to='employee_docs/passbook/', null=True, blank=True, validators=[validate_pdf_size])
    appointment_order = models.FileField(upload_to='employee_docs/appointment_orders/', null=True, blank=True, validators=[validate_pdf_size])
    experience = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee_id'],
                condition=Q(is_active=True),
                name='unique_active_employee_id',
            ),
        ]

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        years = today.year - self.date_of_birth.year
        # subtract one year if birthday hasn’t occurred yet this year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years
    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_emp = Employee.objects.all().order_by('id').last()
            if not last_emp:
                self.employee_id = 'K001'
            else:
                last_id_num = int(last_emp.employee_id[1:])
                self.employee_id = f'K{last_id_num + 1:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.employee_name}"

class DailySalaryEntry(BaseModel):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='daily_entries')
    date = models.DateField()
    
    # HR Input: Just numbers
    shift_value = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text="1.0, 0.5, 1.5, etc.")
    ot_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    worked_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, editable=False)  # add this
    amount_earned = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    class Meta:
        unique_together = ('employee', 'date')

    






class AdvancePayment(models.Model):
    """Tracks money given in advance to be deducted from salary."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advances')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_given = models.DateField()
    is_deducted = models.BooleanField(default=False)

    def __str__(self):
        return f"Advance ₹{self.amount} - {self.employee.name}"

class MonthlySalarySummary(models.Model):
    """Final Payroll: Summarizes Shifts, Hours, and Net Pay."""
    STATUS_CHOICES = [('UNPAID', 'Unpaid'), ('PAID', 'Paid')]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='monthly_summaries')
    month_year = models.DateField(help_text="Select the 1st day of the month")
    
    # Summarized Data
    total_days_present = models.IntegerField(default=0)
    total_shifts_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    total_hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    
    # Financials
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    advance_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    net_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')

    class Meta:
        unique_together = ('employee', 'month_year')

    def save(self, *args, **kwargs):
        from django.db.models import Sum, F
        entries = DailySalaryEntry.objects.filter(
            employee=self.employee, 
            date__month=self.month_year.month, 
            date__year=self.month_year.year
        )
        if entries.exists():
            stats = entries.aggregate(
                s_shifts=Sum('shift_value'),
                s_hours=Sum(F('worked_hours') + F('ot_hours')),
                s_money=Sum('amount_earned')
            )
            self.total_days_present = entries.count()
            self.total_shifts_worked = stats['s_shifts'] or 0.0
            self.total_hours_worked = stats['s_hours'] or 0.0
            self.gross_salary = stats['s_money'] or 0.0
            
            # Substract Advances
            advances = AdvancePayment.objects.filter(employee=self.employee, is_deducted=False)
            self.advance_deducted = advances.aggregate(Sum('amount'))['amount__sum'] or 0.0
            self.net_payable = self.gross_salary - self.advance_deducted
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.month_year.strftime('%B %Y')}"