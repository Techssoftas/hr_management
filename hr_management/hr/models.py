from django.db import models
import calendar
from decimal import Decimal
from .utils import *
from django.db.models import Q, Sum, F, Max,Min
from datetime import date
from calendar import monthrange
from datetime import date as dt_date



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
        constraints = [models.UniqueConstraint(fields=['shift_value'],condition=Q(is_active=True),name='unique_active_shift_value',),]

    def __str__(self):
        return f"{self.shift_value} ({self.standard_hours} hrs)"

class Designation(BaseModel):
    SALARY_TYPE_CHOICES = [('DAILY', 'Daily'), ('MONTHLY', 'Monthly')]
    name = models.CharField(max_length=100)
    salary_type = models.CharField(max_length=10, choices=SALARY_TYPE_CHOICES)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name'],condition=Q(is_active=True),name='unique_active_designation_name',),]

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
    state = models.CharField(max_length=100, blank=True)  # NEW


    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)  # NEW
    education_qualification = models.CharField(max_length=255, blank=True)
    end_date = models.DateField(null=True, blank=True)

    contact_number = models.CharField(max_length=15)
    emergency_contact_number = models.CharField(max_length=15, blank=True)  # NEW
    emergency_relation = models.CharField(max_length=50, blank=True)        # NEW
    emergency_relation_name = models.CharField(max_length=150, blank=True)  # NEW
    blood_group = models.CharField(max_length=5, blank=True)
    has_esi_pf = models.BooleanField(default=False)
    esi_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)   # e.g. monthly ESI deduction
    pf_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)    # e.g. monthly PF deduction


    bank_name = models.CharField(max_length=100, blank=True)         # NEW
    bank_branch = models.CharField(max_length=100, blank=True)       # NEW
    ifsc_code = models.CharField(max_length=20, blank=True)          # NEW
    account_number = models.CharField(max_length=30, blank=True)     # NEW

    # Files with size validation
    # Media & Docs (Condensed)
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True, validators=[validate_photo_size])
    
    # All PDFs on single lines
    aadhaar_pdf = models.FileField(upload_to='employee_docs/aadhaar/', null=True, blank=True, validators=[validate_pdf_size])
    pan_pdf = models.FileField(upload_to='employee_docs/pan/', null=True, blank=True, validators=[validate_pdf_size])
    passbook_pdf = models.FileField(upload_to='employee_docs/passbook/', null=True, blank=True, validators=[validate_pdf_size])
    appointment_order = models.FileField(upload_to='employee_docs/appointment_orders/', null=True, blank=True, validators=[validate_pdf_size])
    experience = models.TextField(blank=True)
    # After address, district, etc. in the Employee class:
    about = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    aadhaar_number = models.CharField(max_length=20, blank=True)   # Aadhaar is 12 digits, allow spaces/dashes
    pan_number = models.CharField(max_length=20, blank=True)      # PAN is 10 chars
    esi_account_number = models.CharField(max_length=50, blank=True)
    pf_account_number = models.CharField(max_length=50, blank=True)

    class Meta: 
        constraints = [
            models.UniqueConstraint(fields=['employee_id'],condition=Q(is_active=True),name='unique_active_employee_id',),]

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
    day = models.PositiveIntegerField(default=1, help_text="Day (default 1)")
    # HR Input: Just numbers
    shift_value = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text="1.0, 0.5, 1.5, etc.")
    ot_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    worked_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, editable=False)  # add this
    total_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, editable=False)
    amount_earned = models.DecimalField(max_digits=8, decimal_places=2, default=0, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date'],
                condition=Q(is_active=True),
                name='unique_active_daily_entry_per_employee_per_day',
            ),
        ]









class AdvancePayment(BaseModel):
    """Tracks money given in advance to be deducted from salary."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advances')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_given = models.DateField()

    class Meta:
        # For each active employee, allow only one advance record per date.
        # If they need to change, they should edit the existing record.
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date_given'],
                condition=Q(is_active=True),
                name='unique_active_advance_per_employee_per_day',
            ),
        ]


    def __str__(self):
        return f"Advance ₹{self.amount} - {self.employee.name}"
    



class MonthlySalarySummary(BaseModel):
    """
    Final Payroll: Summarizes shifts, hours, advances and net pay
    for one employee in one month.
    - `date` will be set to the LAST worked date in that month
      (e.g. 2026-03-03 if there are entries on 1,2,3).
    - One row per (employee, month) is enforced by unique_together.
    """
    # STATUS_CHOICES = [
    #     ('UNPAID', 'Unpaid'),
    #     ('PAID', 'Paid'),
    # ]
    employee = models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='monthly_summaries',)
    # Will be updated to the last worked date for that month
    date = models.DateField()
    # Summarized Data
    total_shifts_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    total_hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    total_days = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    # Financials
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    advance_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    net_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    esi_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    pf_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    # status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee_id']
        constraints = [
            models.CheckConstraint(
                check=Q(net_payable__gte=0),
                name='net_payable_non_negative',
            ),
        ]
    # No custom save: signals do all calculations.
    def __str__(self):
         return f"{self.employee.employee_name} - {self.date.strftime('%d-%m-%Y')} - {'Paid' if self.is_paid else 'Unpaid'}"
    


class Certificate(BaseModel):
    """
    Stores uploaded certificates as PDFs (max 2 MB).
    """
    name = models.CharField(max_length=255)
    date  = models.DateField()  # the day the certificate is relevant/issued
    file = models.ImageField(upload_to='certificates/' ,
validators=[validate_photo_size_certificate],)  # 500 KB validation from utils

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'date'],
                condition=Q(is_active=True),
                name='unique_active_certificate_per_date'
            ),
        ]


    def __str__(self):
        return f"{self.name} - {self.date}"    
    


class Bonus(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='bonuses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_given = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date_given'],
                condition=Q(is_active=True),
                name='unique_active_bonus_per_employee_per_day',
            ),
        ]

    def __str__(self):
        return f"Bonus ₹{self.amount} - {self.employee.employee_name}"    