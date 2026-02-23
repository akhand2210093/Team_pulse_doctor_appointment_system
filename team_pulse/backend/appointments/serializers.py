from rest_framework import serializers
from .models import *


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'


class DoctorSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)
    
    class Meta:
        model = Doctor
        fields = '__all__'


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'

    def validate(self, data):
        doctor = data['doctor']
        schedule = data['schedule']
        mode = data['mode']

        # Mode-doctor validation
        if doctor.mode != mode:
            raise serializers.ValidationError("Mode-doctor mismatch.")

        # Slot availability
        if schedule.is_booked:
            raise serializers.ValidationError("Slot already booked.")

        return data

    def create(self, validated_data):
        schedule = validated_data['schedule']

        # lock slot
        schedule.is_booked = True
        schedule.save()

        appointment = Appointment.objects.create(**validated_data)
        return appointment