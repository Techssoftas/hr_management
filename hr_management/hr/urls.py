from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'advances', AdvancePaymentViewSet, basename='advance')
router.register(r'daily-salary-entries', DailySalaryEntryViewSet, basename='daily-salary-entry')
router.register(r'monthly-summaries', MonthlySalarySummaryViewSet, basename='monthly-summary')
router.register(r'certificates', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('', include(router.urls)),
]