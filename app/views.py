import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render,redirect
from django.urls import reverse_lazy
from app.models import Payment, Sale,Customer,Personnel, Transaction, TransactionType,Work,PaymentMethod,Bank
from django.views.generic import CreateView,ListView,UpdateView,DeleteView
from django.contrib import messages
from django.db.models.query import QuerySet,Q
from django.utils import timezone
from jdatetime import datetime as jdatetime
from jalali_date import datetime2jalali
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from app.forms import *


def home (request):
    sales = Sale.objects.all()
    return render(request, "app/home.html", {"sales": sales})

# class SaleCreateView(CreateView):
#     template_name = "app/new_sale.html" 
#     model = Sale
#     fields=["customer", "personnel", "work", "price", "date"]
#     success_url = reverse_lazy("home")


# from .forms import SaleForm, TransactionForm
 
class SaleCreateView(CreateView):
    template_name = "app/new_sale.html"
    form_class = SaleForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'sale_id': self.object.id})
        return response

class SaleListView(ListView):
    template_name = "app/sale_list.html"
    model = Sale
    context_object_name = "sales"
    
    
    def get_queryset(self):
        selected_date_str = self.request.GET.get('date')
    
        try:
            if selected_date_str:
                jalali_date = jdatetime.strptime(selected_date_str, '%Y-%m-%d')
                target_date = jalali_date.togregorian()
            else:
                target_date = timezone.now().date()
            
            
            sales =  Sale.objects.filter(date__date=target_date).order_by('-date')
            return sales
        
        except Exception as e:
            print(f"Error in date processing: {e}")
            return Sale.objects.none()

    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()
        def to_persian_numbers(s):
            persian_digits = '۰۱۲۳۴۵۶۷۸۹'
            return ''.join(persian_digits[int(ch)] if ch.isdigit() else ch for ch in str(s))
        selected_date = self.request.GET.get('date')
        if selected_date:
            try:
                # jalali_date = jdatetime.strptime(selected_date, '%Y-%m-%d')
                context['selected_jalali_date'] = selected_date
                context['date_formatted'] = selected_date
            except ValueError:
                pass
        else:
            jalali_today_str = datetime2jalali(today).strftime('%Y-%m-%d')  
            context['selected_jalali_date'] = to_persian_numbers(jalali_today_str)  
            context['date_formatted'] = jalali_today_str  
        
        context['today_jalali'] = datetime2jalali(today).strftime('%Y-%m-%d')

        sales_today = self.get_queryset()
        total_price = sales_today.aggregate(total=Sum('price'))['total'] or 0
        context['total_price'] = total_price

        return context

    
class SaleUpdateView(UpdateView):
    template_name = "app/edit_sale.html" 
    model = Sale
    fields=["customer", "personnel", "work", "price", "date"]
    success_url = reverse_lazy("home")
    context_object_name="sale"


class SaleDeleteView(DeleteView):
    template_name = "app/delete_sale.html" 
    model = Sale
    success_url = reverse_lazy("home")
    context_object_name="sale"


class CustomerListView(ListView):
    template_name="app/customer_list.html"
    model=Customer
    context_object_name="customers"
    
    def get_queryset(self):
        filter = self.request.GET.get("filter")
        queryset= super().get_queryset()
        if filter:
            queryset = queryset.filter(Q(name__search=filter) | Q(mobile__search=filter))
        return queryset.all() 



class CustomerCreateView(CreateView):
    template_name = "app/new_customer.html" 
    model = Customer
    fields=["name", "mobile"]
    success_url = reverse_lazy("customers")

class CustomerUpdateView(UpdateView):
    template_name = "app/edit_customer.html" 
    model = Customer
    fields=["name", "mobile", "black_list", "black_list_reason"]
    success_url = reverse_lazy("customers")
    context_object_name="customer"

class CustomerDeleteView(DeleteView):
    template_name = "app/delete_customer.html" 
    model = Customer
    success_url = reverse_lazy("customers")
    context_object_name="customer"


def get_payment_data(request):
    payment_methods = list(PaymentMethod.objects.all().values("id", "name", "requires_bank"))
    banks = list(Bank.objects.all().values("id", "name"))
    return JsonResponse({
        "payment_methods": payment_methods,
        "banks": banks
    })

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import json
from .models import Sale, Transaction, TransactionType, PaymentMethod, Bank

@csrf_exempt
def save_payments(request):
    if request.method == "POST":
        data = json.loads(request.body)
        sale_id = data.get("sale_id")
        payments = data.get("payments", [])

        sale = get_object_or_404(Sale, pk=sale_id)

        # نوع تراکنش دریافتی (effect=1)
        receive_type = TransactionType.objects.filter(effect=1).first()
        if not receive_type:
            return JsonResponse({"status": "error", "message": "نوع تراکنش دریافتی تعریف نشده است"}, status=400)

        for payment in payments:
            amount_str = str(payment.get("amount", "0")).replace(",", "")
            amount = float(amount_str) if amount_str else 0
            
            jalali_date = datetime2jalali(sale.date).strftime('%Y/%m/%d')
            description = f"{sale.customer.name} | {sale.work.work_name} | {jalali_date}"
            
            Transaction.objects.create(
                sale=sale,
                transaction_type=receive_type,
                source_type_id=payment.get("method_id"),
                bank_id=payment.get("bank_id") or None,
                amount=amount,
                date=sale.date,
                description=description
            )

        return JsonResponse({"status": "ok"})
    
class TransactionCreateView(CreateView):
    template_name = "app/new_transaction.html"
    form_class = TransactionForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'transaction_id': self.object.id})
        return response


class LedgerReportView(ListView):
    model = Transaction
    template_name = "app/ledger_report.html"
    context_object_name = "transactions"
    paginate_by = 50

    def get_default_dates(self):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        return {
            'default_start_date': start_date,
            'default_end_date': end_date,
            'default_start_date_str': start_date.strftime('%Y-%m-%d'),
            'default_end_date_str': end_date.strftime('%Y-%m-%d')
        }

    def get_queryset(self):
        bank_id = self.request.GET.get("bank")
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        payment_method_id = self.request.GET.get("payment_method")

        # تنظیم تاریخ‌های پیش‌فرض
        default_dates = self.get_default_dates()
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else default_dates['default_start_date']
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else default_dates['default_end_date']
        except (ValueError, TypeError):
            start_date = default_dates['default_start_date']
            end_date = default_dates['default_end_date']

        qs = Transaction.objects.select_related(
            'transaction_type', 'source_type', 'bank'
        ).order_by("date", "id")

        if bank_id:
            qs = qs.filter(bank_id=bank_id)
        if payment_method_id:
            qs = qs.filter(source_type_id=payment_method_id)

        qs = qs.filter(date__date__gte=start_date, date__date__lte=end_date)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # تنظیم تاریخ‌های پیش‌فرض
        default_dates = self.get_default_dates()
        
        bank_id = self.request.GET.get("bank")
        start_date_str = self.request.GET.get("start", default_dates['default_start_date_str'])
        end_date_str = self.request.GET.get("end", default_dates['default_end_date_str'])
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = default_dates['default_start_date']
            end_date = default_dates['default_end_date']

        # محاسبه موجودی اولیه
        opening_balance = 0
        opening_qs = Transaction.objects.all()
        
        if bank_id:
            opening_qs = opening_qs.filter(bank_id=bank_id)
            
        opening_txs = opening_qs.filter(date__date__lt=start_date)
        
        for tx in opening_txs:
            opening_balance += tx.amount * tx.transaction_type.effect

        # محاسبه موجودی جاری و جمع‌ها
        running_balance = opening_balance
        total_amount = 0
        increase_count = 0
        decrease_count = 0
        rows = [{
                "tx": type("Tx", (), {
                    "date": start_date,
                    "transaction_type": type("TType", (), {"name": "مانده اولیه"}),
                    "amount": opening_balance,
                    "description": ""
                })(),
                "balance": opening_balance,
                "amount_with_effect": None,
                "is_opening": True
                }]
        
        for tx in context["transactions"]:
            amount_with_effect = tx.amount * tx.transaction_type.effect
            tx.amount = tx.amount * tx.transaction_type.effect
            running_balance += amount_with_effect
            total_amount += amount_with_effect
            
            if tx.transaction_type.effect == 1:
                increase_count += 1
            else:
                decrease_count += 1
                
            rows.append({
                "tx": tx,
                "balance": running_balance
            })

        # انتخاب نوع پرداخت پیش‌فرض
        payment_methods = PaymentMethod.objects.all()
        default_payment_method = payment_methods.filter(requires_bank=False).first()
        if not default_payment_method:
            default_payment_method = payment_methods.first()

        context.update({
            "opening_balance": opening_balance,
            "closing_balance": running_balance,
            "rows": rows,
            "total_amount": total_amount,
            "increase_count": increase_count,
            "decrease_count": decrease_count,
            "payment_methods": payment_methods,
            "default_payment_method": default_payment_method,
            "banks": Bank.objects.all(),
            "transaction_types": TransactionType.objects.all(),
            "default_start_date": start_date_str,
            "default_end_date": end_date_str,
            "selected_start_date": start_date,
            "selected_end_date": end_date,
            "bank_id": bank_id,
        })
        return context