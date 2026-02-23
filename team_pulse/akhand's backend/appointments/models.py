from django.db import models


class Specialty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    name = models.CharField(max_length=100)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    clinic_address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.mode})"


class Patient(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    dob = models.DateField()
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    time_slot = models.TimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('doctor', 'date', 'time_slot')

    def __str__(self):
        return f"{self.doctor.name} - {self.date} {self.time_slot}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no-show', 'No Show'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    schedule = models.ForeignKey(DoctorSchedule, on_delete=models.CASCADE)
    mode = models.CharField(max_length=10)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='confirmed')
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    video_link = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} → {self.doctor} ({self.mode})"