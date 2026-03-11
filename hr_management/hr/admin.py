from django.contrib import admin
from django.db import transaction
from .models import (
    Employee, Designation, Shift, 
    DailySalaryEntry, AdvancePayment, 
    MonthlySalarySummary
)

# --- INLINES (Show related data inside another model's page) ---

class AdvanceInline(admin.TabularInline):
    model = AdvancePayment
    extra = 0
    fields = ('date_given', 'amount', 'is_deducted')
    can_delete = False

class DailyEntryInline(admin.TabularInline):
    model = DailySalaryEntry
    extra = 0
    fields = ('date', 'shift_value', 'worked_hours', 'ot_hours', 'amount_earned')
    readonly_fields = ('amount_earned',)
    max_num = 10  # Show only the last 10 entries to keep it clean

# --- ADMIN CLASSES ---

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'employee_name', 'designation', 'contact_number', 'has_esi_pf')
    list_filter = ('designation', 'has_esi_pf', 'date_of_joining')
    search_fields = ('employee_name', 'employee_id', 'contact_number')
    readonly_fields = ('employee_id',)

    inlines = [AdvanceInline, DailyEntryInline]

    fieldsets = (
        ("Personal Details", {
            'fields': (
                ('employee_id', 'employee_name'),
                ('date_of_birth', 'blood_group'),
                'contact_number',
                'address',
                'district',
                'education_qualification',
                'photo',
            )
        }),
        ("Company Info", {
            'fields': ('designation', 'date_of_joining', 'end_date', 'has_esi_pf')
        }),
        ("Documents", {
            'classes': ('collapse',),
            'fields': (
                'aadhaar_pdf',
                'pan_pdf',
                'passbook_pdf',
                'appointment_order',
                'experience',
            ),
        }),
    )

@admin.register(DailySalaryEntry)
class DailySalaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'employee', 'shift_value', 'worked_hours', 'ot_hours', 'amount_earned')
    list_filter = ('date', 'employee__designation')
    search_fields = ('employee__name', 'employee__employee_id')
    date_hierarchy = 'date' # Adds a calendar navigation bar at the top
    readonly_fields = ('worked_hours','amount_earned',)
    list_editable = ('shift_value', 'ot_hours')

@admin.register(AdvancePayment)
class AdvanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'amount', 'date_given', 'is_active')
    list_filter = ('is_active', 'date_given')
    search_fields = ('employee__name',)

@admin.register(MonthlySalarySummary)
class MonthlySummaryAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'date', 'total_shifts_worked', 
        'total_hours_worked', 'gross_salary', 'net_payable', 'status'
    )
    list_filter = ('status', 'date')
    search_fields = ('employee__name', 'employee__employee_id')
    
    # These fields are auto-calculated by the model's save() method
    readonly_fields = (
        'total_days', 'total_shifts_worked', 
        'total_hours_worked', 'gross_salary', 
        'advance_deducted', 'net_payable'
    )
    
    actions = ['mark_as_paid']

    @admin.action(description="Mark selected summaries as Paid")
    def mark_as_paid(self, request, queryset):
        queryset.update(status='PAID')

# Simple registrations
admin.site.register(Designation)
admin.site.register(Shift)