from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone

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
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.transaction_type} - {self.source_type} - {self.amount} -{self.date}-{self.description}"