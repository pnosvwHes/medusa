from django import forms
import jdatetime
from app.models import  *
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from django.utils.formats import localize
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
import datetime
from django.forms.widgets import Select
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class SaleForm(forms.ModelForm):
    date = JalaliDateField(
        label='تاریخ',
        widget=AdminJalaliDateWidget(
            attrs={'class': 'border p-2 rounded w-full jalali-datepicker'}
        ),
        initial=timezone.now().date(),    
    )
    time = forms.TimeField(
        label='ساعت',
        widget=forms.TimeInput(
            attrs={'class': 'border p-2 rounded w-full', 'type': 'time'}
        ),
        initial=timezone.now().time().strftime('%H:%M'),
    )
    class Meta:
        model = Sale
        fields = ['customer', 'personnel', 'work', 'price']  # حذف date از اینجا
        labels = {
            'customer': 'مشتری',
            'personnel': 'پرسنل',
            'work': 'خدمت',
            'price': 'مبلغ',
            
        }
        widgets = {
            'customer': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'personnel': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'work': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'price': forms.NumberInput(attrs={'class': 'border p-2 rounded w-full'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        jdate = self.cleaned_data['date']
        time = self.cleaned_data['time']

        # g_date = jdate.to_gregorian()
        instance.date = datetime.datetime.combine(jdate, time)

        if commit:
            instance.save()
        return instance



class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction
        fields = ['date','transaction_type', 'source_type', 'bank', 'amount', 'description']  # حذف date از اینجا
        labels = {
            'date': 'تاریخ',
            'transaction_type': 'نوع تراکنش',
            'source_type': 'از/به',
            'bank': 'حساب بانکی',
            'amount': 'مبلغ',
            'description':'توضیحات'
        }
        widgets = {
            'date': AdminJalaliDateWidget(attrs={'class': 'border p-2 rounded w-full'}),
            'transaction_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'source_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'bank': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'amount': forms.NumberInput(attrs={'class': 'border p-2 rounded w-full'}),
            'description': forms.Textarea(attrs={'class': 'border p-2 rounded w-full'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance



class PaymentMethodSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        # اگر value یک ModelChoiceIteratorValue است، باید .instance بگیریم
        try:
            # اگر value خودش آبجکت نیست
            pm_instance = value.instance
        except AttributeError:
            pm_instance = None

        if pm_instance:
            option['attrs']['data-requires-bank'] = str(pm_instance.requires_bank).lower()
        else:
            option['attrs']['data-requires-bank'] = 'false'

        return option
    
class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='رمز عبور')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="تکرار رمز عبور")
    personnel = forms.ModelChoiceField(
        queryset=Personnel.objects.filter(user_profile__isnull=True),
        required=False,
        label="پرسنل مرتبط"
    )
    is_admin = forms.BooleanField(required=False, label="ادمین است؟")

    class Meta:
        model = User
        fields = ['username', 'password', "personnel", "is_admin"]
        labels = {
            'username':'نام کاربری',
            'password': 'رمز عبور'
        }
        help_texts = {  # این بخش تمام help_text های پیش‌فرض رو حذف می‌کنه
            'username': '',
            'password': '',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password != password_confirm:
            self.add_error('password_confirm', "رمز عبور با تکرار آن مطابقت ندارد")
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        personnel = self.cleaned_data.get("personnel")
        is_admin = self.cleaned_data.get("is_admin", False)

        if personnel:
            PersonnelUser.objects.create(
                personnel=personnel,
                user=user,
                is_admin=is_admin
            )

        return user


class PayForm(forms.ModelForm):
    class Meta:
        model = Pay
        fields = ['date', 'pay_type', 'personnel', 'source_type', 'bank', 'amount', 'description']
        labels = {
            'date': 'تاریخ',
            'pay_type': 'نوع پرداخت',
            'personnel': 'پرسنل',
            'source_type': 'از',
            'bank': 'حساب بانکی',
            'amount': 'مبلغ',
            'description': 'توضیحات'
        }
        widgets = {
            'date': AdminJalaliDateWidget(attrs={'class': 'border p-2 rounded w-full autocomplete="new-password'}),
            'pay_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'personnel': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'source_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'bank': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'amount': forms.NumberInput(attrs={'class': 'border p-2 rounded w-full'}),
            'description': forms.Textarea(attrs={'class': 'border p-2 rounded w-full'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['date', 'receipt_type', 'customer', 'source_type', 'bank', 'amount', 'description']
        labels = {
            'date': 'تاریخ',
            'receipt_type': 'نوع دریافت',
            'customer': 'مشتری',
            'source_type': 'به',
            'bank': 'حساب بانکی',
            'amount': 'مبلغ',
            'description': 'توضیحات'
        }
        widgets = {
            'date': AdminJalaliDateWidget(attrs={'class': 'border p-2 rounded w-full'}),
            'receipt_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'customer': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'source_type': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'bank': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
            'amount': forms.NumberInput(attrs={'class': 'border p-2 rounded w-full'}),
            'description': forms.Textarea(attrs={'class': 'border p-2 rounded w-full'}),
        }

    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False)
    bank = forms.ModelChoiceField(queryset=Bank.objects.all(), required=False)


    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
    


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['fname', 'lname', 'mobile', 'birth_day', 'region', 'referrer']
        labels = {
            'fname': 'نام ',
            'lname': 'نام خانوادگی',
            'mobile': 'موبایل',
            'birth_day': 'تاریخ تولد', 
            'region': 'محله', 
            'referrer': 'معرف',
        }
        widgets = {
            'lname': forms.TextInput(attrs={'class': 'input'}),
            'fname': forms.TextInput(attrs={'class': 'input'}),
            'mobile': forms.TextInput(attrs={'class': 'input'}),
            'birth_day': AdminJalaliDateWidget(attrs={'class': 'border p-2 rounded w-full'}),
            'region': forms.TextInput(attrs={'class': 'input'}),
            'referrer': forms.Select(attrs={'class': 'select2 border p-2 rounded w-full'}),
        }
        referrer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False)


