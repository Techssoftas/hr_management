from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from .models import Shift
from .serializers import *
from .permissions import IsHRorAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db import transaction


# Create your views here.
class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    queryset = Shift.objects.filter(is_active=True)
    permission_classes =[IsAuthenticated, IsHRorAdmin]


    def get_queryset(self):
        qs = Shift.objects.filter(is_active=True)
        shift_value = self.request.query_params.get('shift_value')
        if shift_value is not None:
            qs = qs.filter(shift_value=shift_value)
        return qs
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False instead of removing the record."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
    {"detail": "Deleted successfully"},
    status=status.HTTP_200_OK
)
    


class DesignationViewSet(viewsets.ModelViewSet):
    serializer_class = DesignationSerializer
    queryset = Designation.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsHRorAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
    {"detail": "Deleted successfully"},
    status=status.HTTP_200_OK
)
    


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsHRorAdmin]

    def get_queryset(self):
        qs = Employee.objects.filter(is_active=True).select_related('designation')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee_id__iexact=employee_id.strip())
        return qs

    def get_serializer_class(self):
        # When filtering by employee_id, return only summary fields
        if self.action == 'list' and self.request.query_params.get('employee_id'):
            return EmployeeSummarySerializer
        return EmployeeSerializer

    def destroy(self, request, *args, **kwargs):
        """Soft delete employee and cascade to daily entries, monthly summaries, and advances."""
        instance = self.get_object()
        with transaction.atomic():
            instance.is_active = False
            instance.save()
            DailySalaryEntry.objects.filter(employee=instance).update(is_active=False)
            MonthlySalarySummary.objects.filter(employee=instance).update(is_active=False)
            AdvancePayment.objects.filter(employee=instance).update(is_active=False)
        return Response(
            {"detail": "Deleted successfully"},
            status=status.HTTP_200_OK
        )
    

    @action(detail=False, methods=['get'], url_path='lists')
    def lists(self, request):
        """
        Lightweight list: joining date, id, employee_id, employee_name,
        designation name, contact number. Paginated like normal list.
        URL: /hr/employees/lists/
        """
        qs = self.get_queryset().select_related('designation')
        page = self.paginate_queryset(qs)
        if page is not None:
            data = [
                {
                    "id": emp.id,
                    "employee_id": emp.employee_id,
                    "employee_name": emp.employee_name,
                    "joining_date": emp.date_of_joining,
                    "designation_name": emp.designation.name if emp.designation else None,
                    "contact_number": emp.contact_number,
                    "district": emp.district,
                }
                for emp in page
            ]
            return self.get_paginated_response(data)
        data = [
            {
                "id": emp.id,
                "employee_id": emp.employee_id,
                "employee_name": emp.employee_name,
                "joining_date": emp.date_of_joining,
                "designation_name": emp.designation.name if emp.designation else None,
                "contact_number": emp.contact_number,
                "district": emp.district,
            }
            for emp in qs
        ]
        return Response(data)
    



class AdvancePaymentViewSet(viewsets.ModelViewSet):
    serializer_class = AdvancePaymentSerializer
    queryset = AdvancePayment.objects.filter(is_active=True).select_related('employee')
    permission_classes = [IsAuthenticated, IsHRorAdmin]

    def get_queryset(self):
        qs = AdvancePayment.objects.filter(is_active=True).select_related('employee')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({"detail": "Deleted successfully"},status=status.HTTP_200_OK)    
    


class DailySalaryEntryViewSet(viewsets.ModelViewSet):
    serializer_class = DailySalaryEntrySerializer
    queryset = DailySalaryEntry.objects.filter(is_active=True).select_related('employee')
    permission_classes = [IsAuthenticated, IsHRorAdmin]

    def get_queryset(self):
        qs = DailySalaryEntry.objects.filter(is_active=True).select_related('employee', 'employee__designation')

        # Filter by employee_id (string like K001)
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee__employee_id__iexact=employee_id.strip())

        # Filter by designation (id)
        designation_id = self.request.query_params.get('designation_id')
        if designation_id:
            qs = qs.filter(employee__designation_id=designation_id)

        # Date range filters (YYYY-MM-DD)
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Latest dates first
        return qs.order_by('-date', 'employee__employee_id')

    def perform_create(self, serializer):
        """
        Wrap create in a transaction and turn DB integrity errors
        (e.g. duplicate employee+date) into a clean 400 response.
        """
        try:
            with transaction.atomic():
                serializer.save()
        except Exception as exc:
            # Let explicit DRF validation errors bubble through unchanged
            if isinstance(exc, ValidationError):
                raise
            raise APIException("Could not create daily salary entry.") from exc

    def perform_update(self, serializer):
        """
        Same pattern as create: keep the transaction and provide
        a consistent error surface for unexpected failures.
        """
        try:
            with transaction.atomic():
                serializer.save()
        except Exception as exc:
            if isinstance(exc, ValidationError):
                raise
            raise APIException("Could not update daily salary entry.") from exc

    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False."""
        with transaction.atomic():
            instance = self.get_object()
            instance.is_active = False
            instance.save()
        return Response({"detail": "Deleted successfully"},status=status.HTTP_200_OK)
    
class MonthlySalarySummaryViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlySalarySummarySerializer
    queryset = MonthlySalarySummary.objects.filter(is_active=True).select_related('employee')
    permission_classes = [IsAuthenticated, IsHRorAdmin]
    http_method_names = ['get', 'head', 'patch', 'options']

    def get_queryset(self):
        qs = MonthlySalarySummary.objects.filter(is_active=True).select_related('employee', 'employee__designation')

        # Filter by employee_id (string like K001)
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee__employee_id__iexact=employee_id.strip())

        # Filter by designation (id)
        designation_id = self.request.query_params.get('designation_id')
        if designation_id:
            qs = qs.filter(employee__designation_id=designation_id)

        # Date range filters (summary.date is a DateField)
        # You can treat it as "month date" or exact date, depending on how you store it
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Replace the status_param block with:
        is_paid_param = self.request.query_params.get('is_paid')
        if is_paid_param is not None:
            is_paid = str(is_paid_param).strip().lower() in ('true', '1', 'yes')
            qs = qs.filter(is_paid=is_paid)

        # Latest first
        return qs.order_by('-date', 'employee__employee_id')

    def perform_update(self, serializer):
        instance = serializer.save()
        # Recalculate net_payable after any update
        instance.net_payable = (
            (instance.gross_salary or 0)
            - (instance.advance_deducted or 0)
            - (instance.esi_amount or 0)
            - (instance.pf_amount or 0)
        )
        instance.save()


class CertificateViewSet(viewsets.ModelViewSet):
    serializer_class = CertificateSerializer
    queryset = Certificate.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsHRorAdmin]
    def get_queryset(self):
        qs = Certificate.objects.filter(is_active=True)
        name = self.request.query_params.get('name')
        if name:
            qs = qs.filter(name__icontains=name.strip())

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        # Let Django/DB handle parsing; if an invalid date is passed it will
        # result in a 400 from DRF rather than a silent failure.
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs.order_by('-date', '-created_at')
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False instead of removing."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({"detail": "Deleted successfully"}, status=status.HTTP_200_OK)

