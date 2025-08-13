from django.test import TestCase, Client
from django.urls import reverse
from app.models import Customer, Personnel, Work, User, Appointment
from datetime import datetime, timedelta
from django.utils import timezone

class BookingURLsTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.customer = Customer.objects.create(name="مشتری تست", mobile="09123456789")
        self.user = self.personnel = Personnel.objects.create(
            fname="مشتری تست",
            lname="مشتری تست",
            mobile="09123456789")
        # پرسنل
        self.work = Work.objects.create(work_name="خدمت تست")
        
        self.start_time = timezone.now() + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=1)
        # رزرو اولیه
        self.appointment = Appointment.objects.create(
            customer=self.customer,
            work=self.work,
            personnel=self.user,
            start_time=self.start_time,
            end_time=self.end_time
        )

    def test_create_appointment(self):
        url = reverse('create_appointment')
        data = {
            'customer_id': self.customer.id,
            'work_id': self.work.id,
            'personnel_id': self.user.id,
            'start_time': (self.start_time + timedelta(days=1)).isoformat(),
            'end_time': (self.end_time + timedelta(days=1)).isoformat(),
        }
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [200, 201])
