from django.shortcuts import render
from rest_framework import viewsets, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils.timezone import now

from .models import *
from .serializers import *


class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.select_related('specialty').all()
    serializer_class = DoctorSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(active=True)

        mode = self.request.query_params.get('mode')
        specialty = self.request.query_params.get('specialty')

        if mode:
            queryset = queryset.filter(mode=mode)

        if specialty:
            queryset = queryset.filter(specialty_id=specialty)

        return queryset


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = DoctorSchedule.objects.all()
    serializer_class = DoctorScheduleSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_booked=False)

        doctor_id = self.request.query_params.get('doctor')
        date = self.request.query_params.get('date')

        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        if date:
            queryset = queryset.filter(date=date)

        return queryset


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer


# Daily Summary API
@api_view(['GET'])
def daily_summary(request):
    today = now().date()

    data = (
        Appointment.objects
        .filter(created_at__date=today, status='completed')
        .values('mode')
        .annotate(total_appointments=Count('id'), revenue=Sum('fee'))
    )

    return Response(data)