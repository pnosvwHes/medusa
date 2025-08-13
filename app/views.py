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
from django.db.models import Sum,Case, When, F, IntegerField
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from app.forms import *
from django.contrib.auth.decorators import login_required,user_passes_test
from django.utils.decorators import method_decorator
from django.shortcuts import render
from app.models import Sale
from .utils import is_admin
import jdatetime

@login_required
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
    print('1')
    def get_queryset(self):
        selected_date_str = self.request.GET.get('date')
        
        try:
            if selected_date_str:
                # تبدیل رشته دریافتی به جلالی و سپس میلادی
                jalali_date = jdatetime.date.fromisoformat(selected_date_str)
                target_date = jalali_date.togregorian()
                
            else:
                target_date = timezone.now().date()

            print("Target date:", self.request.user.is_superuser, self.request.user.first_name)  # تست
            # شرط برای ادمین
            if self.request.user.is_superuser:
                sales = Sale.objects.filter(date__date=target_date).order_by('-date')
            else:
                personneluser = getattr(self.request.user, "personnel_profile", None)
                personnel = personneluser.get_personnel()
                if personnel:
                    sales = Sale.objects.filter(
                        date__date=target_date,
                        personnel=personnel
                    ).annotate(
                        display_price=F('commission_amount')  # برای کاربران عادی، همیشه کمیسیون
                    ).order_by('-date')
                else:
                    sales = Sale.objects.none()

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
            context['selected_jalali_date'] = selected_date
            context['date_formatted'] = selected_date
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
from .models import Appointment, Sale, Transaction, TransactionType, PaymentMethod, Bank

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

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
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
    

@login_required
@user_passes_test(is_admin)
def create_user_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "کاربر با موفقیت ساخته شد.")
            return redirect('users')
    else:
        form = CustomUserCreationForm()

    return render(request, 'app/new_user.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    users = User.objects.all()
    return render(request, 'app/user_list.html', {'users': users})


from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from .models import Appointment, Personnel, Customer, Work
from datetime import datetime
from django.utils import timezone

class CalendarView(ListView):
    template_name = 'app/calendar.html'
    model = Appointment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['personnel_list'] = Personnel.objects.all()
        context['customer_list'] = Customer.objects.all()
        context['work_list'] = Work.objects.all()
        context['appointments'] = Appointment.objects.select_related('customer', 'personnel', 'work').all()
        return context

@csrf_exempt
def create_appointment(request):
    if request.method == 'POST':
        try:
            data = request.POST

            customer_id = data.get('customer_id')
            work_id = data.get('work_id')
            personnel_id = data.get('personnel_id')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            if not all([customer_id, personnel_id, start_time_str, end_time_str]):
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفاً تمام فیلدهای ضروری را پر کنید'
                }, status=400)

            # تبدیل رشته‌ها به datetime
            try:
                start_time = datetime.fromisoformat(start_time_str)
                end_time = datetime.fromisoformat(end_time_str)
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'فرمت تاریخ نامعتبر است'
                }, status=400)

            # بررسی تداخل فقط برای همان پرسنل
            conflict = Appointment.objects.filter(
                personnel_id=personnel_id,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()

            if conflict:
                return JsonResponse({
                    'status': 'error',
                    'message': 'این بازه زمانی قبلاً برای این پرسنل رزرو شده است.'
                }, status=400)

            # اگر تداخلی نبود، ایجاد رزرو
            appointment = Appointment.objects.create(
                customer_id=customer_id,
                work_id=work_id,
                personnel_id=personnel_id,
                start_time=start_time,
                end_time=end_time
            )

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'message': 'رزرو با موفقیت ثبت شد'
            }, status=201)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
        except Exception as e:
            import traceback; traceback.print_exc()
            return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'متد غیرمجاز'
    }, status=405)

def get_available_time_slots(request):
    personnel_id = request.GET.get('personnel_id')
    date = request.GET.get('date')
    
    if not personnel_id or not date:
        return JsonResponse({'status': 'error', 'message': 'پارامترهای ضروری ارسال نشده'}, status=400)
    
    try:
        # محاسبه زمان‌های آزاد بر اساس رزروهای موجود
        appointments = Appointment.objects.filter(
            personnel_id=personnel_id,
            start_time__date=date
        ).order_by('start_time')
        
        # اینجا منطق محاسبه زمان‌های خالی را پیاده‌سازی کنید
        slots = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00']
        
        return JsonResponse({'status': 'success', 'slots': slots})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def appointment_list(request):
    personnel_id = request.GET.get('personnel_id')
    if not personnel_id:
        return JsonResponse([], safe=False)

    try:
        appointments = Appointment.objects.filter(personnel_id=personnel_id)
        data = []
        for app in appointments:
            data.append({
                'id': app.id,
                'title': f"{app.customer.name} - {app.work.work_name}",
                'start': app.start_time.isoformat(),
                'end': app.end_time.isoformat(),
                'customerId': app.customer.id,
                'customerName': app.customer.name,
                'workId': app.work.id,
                'workName': app.work.work_name,
                'personnelId': app.personnel.id,
                'personnelName': f"{app.personnel.fname} {app.personnel.lname}",
                'isPaid': app.is_paid,
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def update_appointment(request, pk):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            data = request.POST
            
            # اعتبارسنجی داده‌ها
            required_fields = ['customer_id', 'personnel_id', 'start_time', 'end_time']
            if not all(field in data for field in required_fields):
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفاً تمام فیلدهای ضروری را پر کنید'
                }, status=400)

            # به‌روزرسانی فیلدها
            appointment.customer_id = data.get('customer_id')
            appointment.work_id = data.get('work_id')
            appointment.personnel_id = data.get('personnel_id')
            
            try:
                appointment.start_time = datetime.fromisoformat(data.get('start_time'))
                appointment.end_time = datetime.fromisoformat(data.get('end_time'))
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'فرمت تاریخ نامعتبر است'
                }, status=400)

            # بررسی تداخل زمان‌ها
            conflict = Appointment.objects.filter(
                personnel_id=appointment.personnel_id,
                start_time__lt=appointment.end_time,
                end_time__gt=appointment.start_time
            ).exclude(pk=appointment.pk).exists()

            if conflict:
                return JsonResponse({
                    'status': 'error',
                    'message': 'این بازه زمانی قبلاً برای این پرسنل رزرو شده است.'
                }, status=400)

            appointment.save()
            return JsonResponse({
                'status': 'success',
                'message': 'رزرو با موفقیت ویرایش شد'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'}, status=405)

@csrf_exempt
def delete_appointment(request, pk):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            appointment.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'رزرو با موفقیت حذف شد'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'}, status=405)