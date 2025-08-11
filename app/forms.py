from django import forms
from app.models import PaymentMethod, Sale,Customer,Personnel,Work,Transaction
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from django.utils.formats import localize
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
import datetime

class SaleForm(forms.ModelForm):
    date = JalaliDateField(
        label='تاریخ',
        widget=AdminJalaliDateWidget(
            attrs={'class': 'border p-2 rounded w-full'}
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

        g_date = jdate.to_gregorian()
        instance.date = datetime.datetime.combine(g_date, time)

        if commit:
            instance.save()
        return instance




from django import forms
from .models import Transaction, PaymentMethod, TransactionType, Bank
from django.utils import timezone
from jalali_date.fields import JalaliDateTimeField
from jalali_date.widgets import AdminJalaliDateWidget

from django.forms.widgets import Select

class PaymentMethodSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                pm = PaymentMethod.objects.get(pk=value)
                option['attrs']['data-requires-bank'] = str(pm.requires_bank).lower()
            except PaymentMethod.DoesNotExist:
                option['attrs']['data-requires-bank'] = 'false'
        return option


class TransactionForm(forms.ModelForm):
    date = JalaliDateField(widget=AdminJalaliDateWidget, initial=timezone.now)

    class Meta:
        model = Transaction
        fields = ['date', 'transaction_type', 'source_type', 'bank', 'amount', 'description']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'source_type': PaymentMethodSelect(attrs={'class': 'form-control', 'id': 'id_source_type'}),
            'bank': forms.Select(attrs={'class': 'form-control', 'id': 'id_bank'}),
            'amount': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_amount'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
