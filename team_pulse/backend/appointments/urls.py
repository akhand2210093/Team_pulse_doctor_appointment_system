from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include

router = DefaultRouter()
router.register(r'specialties', SpecialtyViewSet)
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'patients', PatientViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'appointments', AppointmentViewSet)

urlpatterns = router.urls + [
    path('daily-summary/', daily_summary),
]