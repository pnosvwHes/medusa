from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from django.contrib.auth.models import User
# Create your models here.

class UserProfile(AbstractBaseUser):
    pass

class Personnel(models.Model):

    ON_SITE_CHOICES =[
        ('بله', 'yes'),
        ('خیر', 'no'),
    ]

    fname = models.CharField(max_length=1000)
    lname = models.CharField(max_length=1000)
    mobile = models.CharField(max_length=1000)
    comment = models.TextField(blank=True)
    on_site = models.CharField(max_length=3, choices=ON_SITE_CHOICES, default='بله')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.fname+'-'+self.lname

class Customer(models.Model):
    name = models.CharField(max_length=200)
    mobile = models.CharField(max_length=11)
    black_list = models.BooleanField(default=False)
    black_list_reason = models.CharField(max_length=2000, blank=True)

    def __str__(self):
        return self.name
    
    @property
    def sale_count(self):
        return self.sale_set.count()

class Sale(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    personnel = models.ForeignKey("Personnel", on_delete=models.CASCADE)
    price = models.IntegerField(default=0)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    work = models.ForeignKey("Work" , on_delete=  models.CASCADE)
    commission_percentage = models.IntegerField(default=60)
    commission_amount = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.pk:  
            commission = PersonnelCommission.objects.filter(
                personnel=self.personnel,
                work=self.work,
                start_date__lte=self.date.date(),
                end_date__gte=self.date.date()
            ).first()

            if commission:
                self.commission_percentage = commission.percentage
                self.commission_amount = int(self.price * commission.percentage / 100)
            else:
                self.commission_percentage = 0
                self.commission_amount = 0

        super().save(*args, **kwargs)




class Work(models.Model):
    work_name = models.CharField(max_length=1000)

    def __str__(self):
        return self.work_name
    
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    requires_bank = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Bank(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Payment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class TransactionType(models.Model):
    name = models.CharField(max_length=50)  # مثل دریافت یا پرداخت
    effect = models.SmallIntegerField(
        choices=[
            (1, 'افزایش موجودی'),
            (-1, 'کاهش موجودی'),
        ],
        default=1
    )

    def __str__(self):
        return self.name

class Transaction(models.Model):
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.CASCADE)  # دریافت یا پرداخت
    source_type = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)  # نقدی یا بانکی
    bank = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.transaction_type} - {self.source_type} - {self.amount} -{self.date}-{self.description}"
    

class PersonnelCommission(models.Model):
    personnel = models.ForeignKey("Personnel", on_delete=models.CASCADE)
    work = models.ForeignKey("Work" , on_delete=  models.CASCADE)
    percentage = models.IntegerField(default=60)
    start_date = models.DateField()
    end_date = models.DateField()


class PersonnelUser(models.Model):
    personnel = models.OneToOneField(Personnel, on_delete=models.CASCADE, related_name='user_profile')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personnel_profile')
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.personnel} - {self.user.username}"
    
    def get_personnel(self):
        return self.personnel
    
class Appointment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.end_time and hasattr(self.work, 'duration'):
            self.end_time = self.start_time + timezone.timedelta(minutes=self.work.duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - {self.work.work_name} ({self.start_time})"