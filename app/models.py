from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.models import User

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        related_name="%(class)s_created",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        User,
        related_name="%(class)s_updated",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        abstract = True

class UserProfile(AbstractBaseUser):
    pass

class Personnel(BaseModel):

    ON_SITE_CHOICES = [
        ('بله', 'yes'),
        ('خیر', 'no'),
    ]

    fname = models.CharField("نام", max_length=1000)
    lname = models.CharField("نام خانوادگی", max_length=1000)
    mobile = models.CharField("موبایل", max_length=1000)
    comment = models.TextField("توضیحات", blank=True)
    on_site = models.CharField("حضور در محل", max_length=3, choices=ON_SITE_CHOICES, default='بله')
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    modified_at = models.DateTimeField("آخرین تغییر", auto_now=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "پرسنل"
        verbose_name_plural = "پرسنل‌ها"

    @property
    def name(self):
        return f"{self.fname} {self.lname}"

    def __str__(self):
        return self.name()


class Customer(BaseModel):
    fname = models.CharField(max_length=200)
    lname = models.CharField(max_length=200, default="")
    mobile = models.CharField(max_length=11)
    birth_day = models.DateField(blank=True, null=True)
    region = models.CharField(max_length=200, blank=True)
    referrer = models.ForeignKey(
        "self",                  
        null=True, blank=True,   
        on_delete=models.SET_NULL,
        related_name="referrals", 
        verbose_name="معرف"
    )
    black_list = models.BooleanField(default=False)
    black_list_reason = models.CharField(max_length=2000, blank=True)
    @property
    def name(self):
        return f"{self.fname}-{self.lname}"
    def __str__(self):
        return f"{self.fname}-{self.lname}"
    
    @property
    def sale_count(self):
        return self.sale_set.count()

class Sale(BaseModel):
    customer = models.ForeignKey("Customer", on_delete=models.PROTECT)
    personnel = models.ForeignKey("Personnel", on_delete=models.PROTECT)
    price = models.IntegerField(default=0)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    work = models.ForeignKey("Work" , on_delete=  models.PROTECT)
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

class SaleImage(models.Model):
    BEFORE = "before"
    AFTER = "after"
    IMAGE_TYPES = [
        (BEFORE, "قبل"),
        (AFTER, "بعد"),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="sale_images/")
    image_type = models.CharField(max_length=10, choices=IMAGE_TYPES)  # 👈 اضافه شد
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sale} - {self.get_image_type_display()}"



class Work(BaseModel):
    work_name = models.CharField("نام خدمت", max_length=1000)

    class Meta:
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"

    def __str__(self):
        return self.work_name

    
class PaymentMethod(BaseModel):
    name = models.CharField(max_length=100)
    requires_bank = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Bank(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Payment(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="payments")
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    bank = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class TransactionType(BaseModel):
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

class Transaction(BaseModel):
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.PROTECT)  # دریافت یا پرداخت
    source_type = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)  # نقدی یا بانکی
    bank = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.transaction_type} - {self.source_type} - {self.amount} -{self.date}-{self.description}"
    

class PersonnelCommission(BaseModel):
    personnel = models.ForeignKey("Personnel", on_delete=models.PROTECT, verbose_name="پرسنل")
    work = models.ForeignKey("Work", on_delete=models.PROTECT, verbose_name="خدمت")
    percentage = models.IntegerField("درصد کمیسیون", default=60)
    start_date = models.DateField("تاریخ شروع")
    end_date = models.DateField("تاریخ پایان")

    class Meta:
        verbose_name = "کمیسیون پرسنل"
        verbose_name_plural = "کمیسیون‌ها"

    def __str__(self):
        return f"{self.personnel} - {self.work} ({self.percentage}%)"


class PersonnelUser(BaseModel):
    personnel = models.OneToOneField(Personnel, on_delete=models.PROTECT, related_name='user_profile')
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='personnel_profile')
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.personnel} - {self.user.username}"
    
    def get_personnel(self):
        return self.personnel
    
class Appointment(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='appointments')
    work = models.ForeignKey(Work, on_delete=models.PROTECT)
    personnel = models.ForeignKey(Personnel, on_delete=models.PROTECT)
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
    

from django.db import models

# نوع پرداخت
class PayType(BaseModel):
    name = models.CharField(max_length=50)  # پرسنل، هزینه سالن، هزینه منزل، سایر
    is_personnel = models.BooleanField(default=False)  # اگر انتخاب پرسنل باشد

    def __str__(self):
        return self.name


# مدل پرداخت
class Pay(BaseModel):
    source_type = models.ForeignKey("PaymentMethod", on_delete=models.PROTECT)
    bank = models.ForeignKey("Bank", null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT)
    personnel = models.ForeignKey(
        "Personnel",
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="payments_received"
    )

    def __str__(self):
        return f"پرداخت به {self.pay_type} - {self.amount} - {self.date}"


# نوع دریافت
class ReceiptType(BaseModel):
    name = models.CharField(max_length=50)  # مشتری، سایر
    is_customer = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# مدل دریافت
class Receipt(BaseModel):
    source_type = models.ForeignKey("PaymentMethod", on_delete=models.PROTECT)
    bank = models.ForeignKey("Bank", null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    sale = models.ForeignKey("Sale", on_delete=models.CASCADE, blank=True, null=True)
    receipt_type = models.ForeignKey(ReceiptType, on_delete=models.PROTECT)
    customer = models.ForeignKey(
        "Customer",
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="receipts_made"        
    )

    def __str__(self):
        return f"دریافت از {self.receipt_type} - {self.amount} - {self.date}"
