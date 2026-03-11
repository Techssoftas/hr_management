from rest_framework import serializers
from .models import *

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            'id', 'shift_value', 'standard_hours', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = [
            'id', 'name', 'salary_type', 'base_salary', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_active', 'created_at', 'updated_at']



class EmployeeSummarySerializer(serializers.ModelSerializer):
    """Minimal fields when filtering by employee_id: id, name, base salary, designation, salary type."""
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    base_salary = serializers.DecimalField(
        source='designation.base_salary', max_digits=10, decimal_places=2, read_only=True
    )
    salary_type = serializers.CharField(source='designation.salary_type', read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'employee_name', 'designation_name', 'base_salary', 'salary_type']


class EmployeeSerializer(serializers.ModelSerializer):
    # Flattening Designation data for easier frontend access
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    designation_salary_type = serializers.CharField(source='designation.salary_type', read_only=True)
    designation_base_salary = serializers.DecimalField(
        source='designation.base_salary', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'employee_name', 'designation', 'designation_name', 'designation_salary_type', 'designation_base_salary',
            'date_of_joining', 'date_of_birth', 'age', 'end_date', 'experience',
            'contact_number', 'blood_group', 'address', 'district', 'state', 'education_qualification',
            'gender',
            'emergency_contact_number', 'emergency_relation', 'emergency_relation_name',
            'bank_name', 'bank_branch', 'ifsc_code', 'account_number',
            'about', 'country', 'aadhaar_number', 'pan_number', 'esi_account_number', 'pf_account_number',
            'has_esi_pf', 'esi_amount', 'pf_amount','is_active', 'photo', 'aadhaar_pdf', 'pan_pdf',
            'passbook_pdf', 'appointment_order', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'employee_id', 'is_active', 'created_at', 'updated_at',
            'designation_base_salary', 'designation_salary_type', 'age'
        ]


class AdvancePaymentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.employee_name', read_only=True)
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = AdvancePayment
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display',
            'amount', 'date_given',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']



class DailySalaryEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.employee_name', read_only=True)
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)
    worked_hours = serializers.DecimalField(max_digits=4, decimal_places=1, required=False, default=0)
    amount_earned = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=0)
    total_hours = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)

    class Meta:
        model = DailySalaryEntry
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display',
            'day', 'date', 'shift_value', 'ot_hours',
            'worked_hours', 'total_hours', 'amount_earned',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'day']


class MonthlySalarySummarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.employee_name', read_only=True)
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = MonthlySalarySummary
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display',
            'date', 'total_days', 'total_shifts_worked', 'total_hours_worked',
            'gross_salary', 'advance_deducted', 'net_payable',
            'status',"esi_amount", "pf_amount",
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'employee', 'date', 'total_days', 'total_shifts_worked',
            'total_hours_worked', 'gross_salary', 'advance_deducted', 'net_payable',
            'is_active', 'created_at', 'updated_at',
        ]        



class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'name', 'date', 'file', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']