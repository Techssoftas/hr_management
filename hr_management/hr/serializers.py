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
            'id', 'employee_id', 'employee_name', 'designation', 'designation_name','designation_salary_type', 'designation_base_salary',
            'date_of_joining', 'date_of_birth','age', 'end_date', 'experience',
            'contact_number', 'blood_group', 'address', 'district', 'education_qualification',
            'has_esi_pf', 'is_active', 'photo', 'aadhaar_pdf', 'pan_pdf', 
            'passbook_pdf', 'appointment_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['employee_id', 'is_active', 'created_at', 'updated_at',  'designation_base_salary','designation_salary_type','age', 'experience']