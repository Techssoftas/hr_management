from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Shift
from .serializers import *
from .permissions import IsHRorAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

# Create your views here.
class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    queryset = Shift.objects.filter(is_active=True)
    permission_classes =[IsAuthenticated, IsHRorAdmin]
    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False instead of removing the record."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    


class DesignationViewSet(viewsets.ModelViewSet):
    serializer_class = DesignationSerializer
    queryset = Designation.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsHRorAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsHRorAdmin]
    def destroy(self, request, *args, **kwargs):
        """Soft delete: set is_active=False instead of removing the record."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

    @action(detail=False, methods=['get'], url_path='lists')
    def lists(self, request):
        """
        Lightweight list: joining date, id, employee_id, employee_name,
        designation name, contact number.
        URL: /hr/employees/lists/
        """
        qs = self.get_queryset().select_related('designation')
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