from django import forms
from app.models import PaymentMethod, Sale,Customer,Personnel,Work,Transaction
from jalali_date.fields import SplitJalaliDateTimeField
from jalali_date.widgets import AdminSplitJalaliDateTime
from django.utils.formats import localize
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator

class CreateSaleForm(forms.Form):


    customer = forms.ChoiceField(label="مشتری")
    personnel = forms.ChoiceField(label="پرسنل")
    work = forms.ChoiceField(label="خدمت")
    price = forms.IntegerField(label="قیمت")
    date = SplitJalaliDateTimeField(
        label="تاریخ و ساعت",
        widget=AdminSplitJalaliDateTime,
    )
    def __init__(self, *args, **kwargs):
        super(CreateSaleForm, self).__init__(*args, **kwargs)
 
        self.fields['customer'].choices = [(c.id, str(c)) for c in Customer.objects.all()]
        self.fields['personnel'].choices = [(p.id, str(p)) for p in Personnel.objects.all()]
        self.fields['work'].choices = [(w.id, str(w)) for w in Work.objects.all()]





class TransactionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Format amount field with intcomma
        if 'amount' in self.initial:
            self.initial['amount'] = localize(self.initial['amount'], use_l10n=True)
        
        # Make bank field required if payment method requires bank
        if 'source_type' in self.data:
            try:
                payment_method_id = int(self.data.get('source_type'))
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
                if payment_method.requires_bank:
                    self.fields['bank'].required = True
            except (ValueError, PaymentMethod.DoesNotExist):
                pass
    
    date = forms.DateTimeField(
        label=_("Date"),
        input_formats=['%Y-%m-%d %H:%M:%S'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'data-jdp': '',
            'placeholder': _('Select date and time')
        }),
        initial=timezone.now
    )
    
    amount = forms.DecimalField(
        label=_("Amount"),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(1)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'data-mask': 'number',
            'placeholder': _('Enter amount')
        })
    )
    
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'date', 'source_type', 'bank', 'amount', 'description']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'source_type': forms.Select(attrs={'class': 'form-control'}),
            'bank': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        bank = cleaned_data.get('bank')
        
        if source_type and source_type.requires_bank and not bank:
            self.add_error('bank', _("This payment method requires selecting a bank."))
        
        return cleaned_data