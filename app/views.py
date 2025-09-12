import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, NoReverseMatch, reverse
from app.models import *
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.utils import timezone
from jalali_date import datetime2jalali, date2jalali
from django.db.models import Sum, F, Q, Count, Max
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime as gdatetime, timedelta
from app.forms import *
from django.contrib.auth.decorators import login_required,user_passes_test
from django.utils.decorators import method_decorator
from .utils import is_admin,compress_image, persian_to_english, english_to_persian, jalali_to_gregorian
import jdatetime
import pandas as pd
from app.mixins import UserTrackMixin
from django.db.models.functions import TruncDate
from .sms import customer_sms, personnel_sms, send_sms

MAX_IMAGES = 4
MAX_SIZE = (1024, 1024)  # طول یا عرض حداکثر
JPEG_QUALITY = 75        # کیفیت JPEG


def to_persian_numbers(s):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    return ''.join(persian_digits[int(ch)] if ch.isdigit() else ch for ch in str(s))


@login_required
def home (request):
    sales = Sale.objects.all()
    return render(request, "app/home.html", {"sales": sales})



class SaleCreateView(CreateView, UserTrackMixin):
    template_name = "app/new_sale.html"
    form_class = SaleForm
    success_url = reverse_lazy("sales")

    def form_valid(self, form):
        sale = form.save()
        # اگر درخواست Ajax بود → JSON برگردون
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"sale_id": sale.id})
        return super().form_valid(form)

    def form_invalid(self, form):
        # در حالت Ajax خطاها رو هم به صورت JSON برگردون
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_time = timezone.now().astimezone(timezone.get_current_timezone())
        context['current_time'] = current_time.strftime('%H:%M')
        return context
class SaleUpdateView(UserTrackMixin, UpdateView):
    template_name = "app/edit_sale.html" 
    model = Sale
    fields = ["customer", "personnel", "work", "price", "date"]
    success_url = reverse_lazy("sales")
    context_object_name = "sale"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        images = self.object.images.all()
        context['before_images'] = images.filter(image_type=SaleImage.BEFORE)
        context['after_images'] = images.filter(image_type=SaleImage.AFTER)
        context['empty_before'] = 1 - context['before_images'].count()  # فقط یک عکس قبل
        context['empty_after'] = 3 - context['after_images'].count()   # حداکثر ۳ عکس بعد
        return context

    def form_valid(self, form):
        self.object = form.save()

        # قبل
        before_images = self.request.FILES.getlist("images_before")
        for img in before_images[:1]:
            compressed = compress_image(img)
            SaleImage.objects.create(sale=self.object, image=compressed, image_type=SaleImage.BEFORE)


        # بعد
        after_images = self.request.FILES.getlist("images_after")
        for img in after_images[:3]:
            compressed = compress_image(img)
            SaleImage.objects.create(sale=self.object, image=compressed, image_type=SaleImage.AFTER)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'sale_id': self.object.id})

        return super().form_valid(form)




class SaleListView(ListView):
    template_name = "app/sale_list.html"
    model = Sale
    context_object_name = "sales"
    def get_queryset(self):
        selected_date_str = self.request.GET.get('date')
        
        try:
            if selected_date_str:
                # تبدیل رشته دریافتی به جلالی و سپس میلادی
                jalali_date = jdatetime.date.fromisoformat(selected_date_str)
                target_date = jalali_date.togregorian()
                
            else:
                target_date = timezone.now().date()

            
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

        selected_date = self.request.GET.get('date')
        if selected_date:
            context['selected_jalali_date'] = selected_date
            context['date_formatted'] = selected_date
        else:
            jalali_today_str = datetime2jalali(today).strftime('%Y-%m-%d')
            context['selected_jalali_date'] = to_persian_numbers(jalali_today_str)
            context['date_formatted'] = jalali_today_str

        sales_today = self.get_queryset()
        context['sales_today'] = sales_today  # اضافه می‌کنیم برای کارت‌ها

        total_price = sales_today.aggregate(total=Sum('price'))['total'] or 0
        total_commission = sales_today.aggregate(total=Sum('commission_amount'))['total'] or 0
        context['total_price'] = total_price
        context['total_commission'] = total_commission

        return context

# class SaleUpdateView(UserTrackMixin, UpdateView):
#     template_name = "app/edit_sale.html" 
#     model = Sale
#     fields=["customer", "personnel", "work", "price", "date"]
#     success_url = reverse_lazy("home")
#     context_object_name="sale"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         images = self.object.images.all()
#         context['images'] = images
#         context['empty_slots'] = MAX_IMAGES - images.count()
#         return context

#     def form_valid(self, form):
#         self.object = form.save()
#         existing_count = self.object.images.count()
#         remaining_slots = MAX_IMAGES - existing_count
#         images = self.request.FILES.getlist("images")
#         for img in images[:remaining_slots]:
#             compressed = compress_image(img)
#             SaleImage.objects.create(sale=self.object, image=compressed)
#         return super().form_valid(form)

@csrf_exempt
def delete_sale_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_id = data.get('image_id')
        try:
            img = SaleImage.objects.get(id=image_id)
            img.image.delete()  # حذف فایل از دیسک
            img.delete()        # حذف ردیف از دیتابیس
            return JsonResponse({'status': 'ok'})
        except SaleImage.DoesNotExist:
            return JsonResponse({'status': 'error'})
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
    form_class = CustomerForm
    success_url = reverse_lazy("customers")

    def post(self, request, *args, **kwargs):
        # اگر آپلود اکسل بود
        if "import_excel" in request.POST and request.FILES.get("excel_file"):
            excel_file = request.FILES["excel_file"]
            try:
                df = pd.read_excel(excel_file)
                for _, row in df.iterrows():
                    Customer.objects.update_or_create(
                        mobile=row['mobile'],
                        defaults={'name': row['name']}
                    )
                messages.success(request, "مشتریان با موفقیت از اکسل وارد شدند.")
            except Exception as e:
                messages.error(request, f"خطا در وارد کردن فایل: {e}")
            return self.get(request, *args, **kwargs)

        # ثبت فرم تک‌تک مشتری
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'customer_id': self.object.id})
        return response

class CustomerUpdateView(UpdateView):
    template_name = "app/edit_customer.html" 
    model = CustomerForm
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



@csrf_exempt
def save_receipts(request):
    if request.method == "POST":
        data = json.loads(request.body)
        sale_id = data.get("sale_id")
        payments = data.get("payments", [])

        sale = get_object_or_404(Sale, pk=sale_id)

        # همیشه از نوع مشتری استفاده می‌کنیم
        customer_receipt_type = ReceiptType.objects.filter(is_customer=True).first()
        if not customer_receipt_type:
            return JsonResponse({"status": "error", "message": "نوع دریافت مشتری تعریف نشده است"}, status=400)

        for payment in payments:
            amount_str = str(payment.get("amount", "0")).replace(",", "")
            amount = float(amount_str) if amount_str else 0

            description = f"{sale.customer.name} | {sale.work.work_name} | {datetime2jalali(sale.date).strftime('%Y/%m/%d')}"

            Receipt.objects.create(
                sale=sale,
                customer=sale.customer,
                receipt_type=customer_receipt_type,
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
    
class PayCreateView(CreateView):
    template_name = "app/new_pay.html"  
    form_class = PayForm
    success_url = reverse_lazy("pay_list")
    source_types = PaymentMethod.objects.all()
    pay_type = PayType.objects.all()
   
    def form_valid(self, form):
        response = super().form_valid(form)
        # پشتیبانی از Ajax
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            
            return JsonResponse({'pay_id': self.object.id})
        return response    
    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        date_val = data.get('date')
        if date_val:
            try:
                date_val = persian_to_english(date_val)
                parts = list(map(int, date_val.split('/')))
                import jdatetime
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data['date'] = date_val
            except:
                pass
        request.POST = data
        return super().post(request, *args, **kwargs)
class ReceiptCreateView(CreateView):
    
    template_name = "app/new_receipt.html"  # می‌توانی قالب جدا هم بسازی
    form_class = ReceiptForm
    success_url = reverse_lazy("receipt_list")
    receipt_types = ReceiptType.objects.all()
    source_types = PaymentMethod.objects.all()
    

    def form_valid(self, form):
        response = super().form_valid(form)
        # پشتیبانی از Ajax
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            
            return JsonResponse({'receipt_id': self.object.id})
        return response    
   
    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        date_val = data.get('date')
        if date_val:
            try:
                # تبدیل اعداد فارسی به انگلیسی
                date_val = persian_to_english(date_val)
                # تبدیل تاریخ شمسی به میلادی
                parts = list(map(int, date_val.split('/')))
                import jdatetime
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data['date'] = date_val
            except:
                pass
        request.POST = data
        return super().post(request, *args, **kwargs)



class PayListView(ListView):
    model = Pay
    template_name = 'app/pay_list.html'
    context_object_name = 'pays'

    def get_queryset(self):
        qs = super().get_queryset()
        today = timezone.localdate()
        default_from = today - timedelta(days=7)
        default_to = today

        from_date_str = self.request.GET.get("from_date")
        to_date_str = self.request.GET.get("to_date")

        if from_date_str:
            try:
                j_from = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d").date()
                from_date = j_from.togregorian()
            except:
                from_date = default_from
        else:
            from_date = default_from

        if to_date_str:
            try:
                j_to = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d").date()
                to_date = j_to.togregorian()
            except:
                to_date = default_to
        else:
            to_date = default_to

        qs = qs.filter(date__range=[from_date, to_date])
        self.from_date = from_date
        self.to_date = to_date

        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)


        context["from_date"] = english_to_persian(jdatetime.date.fromgregorian(date=self.from_date).strftime("%Y/%m/%d"))
        context["to_date"] = english_to_persian(jdatetime.date.fromgregorian(date=self.to_date).strftime("%Y/%m/%d"))

        # Select2 JSON data
        context["pay_types_json"] = json.dumps(
            [{"id": pt.id, "name": pt.name, "is_personnel": pt.is_personnel} for pt in PayType.objects.all()]
        )
        context["personnel_json"] = json.dumps(
            [{"id": p.id, "name": f"{p.fname}-{p.lname}"} for p in Personnel.objects.all()]
        )
        context["source_types_json"] = json.dumps(
            [{"id": st.id, "name": st.name, "requires_bank": st.requires_bank} for st in PaymentMethod.objects.all()]
        )
        context["banks_json"] = json.dumps(
            [{"id": b.id, "name": b.name} for b in Bank.objects.all()]
        )

        return context


class ReceiptListView(ListView):
    model = Receipt
    template_name = 'app/receipt_list.html'
    context_object_name = 'receipts'

    def get_queryset(self):
        qs = super().get_queryset()

        today = timezone.localdate()
        default_from = today - timedelta(days=7)
        default_to = today

        from_date_str = self.request.GET.get("from_date")
        to_date_str = self.request.GET.get("to_date")

        if from_date_str:
            try:
                # رشته شمسی → جلالی
                j_from = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d").date()
                # جلالی → میلادی
                from_date = j_from.togregorian()
            except:
                from_date = default_from
        else:
            from_date = default_from

        if to_date_str:
            try:
                j_to = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d").date()
                to_date = j_to.togregorian()
            except:
                to_date = default_to
        else:
            to_date = default_to

        qs = qs.filter(date__range=[from_date, to_date])

        self.from_date = from_date
        self.to_date = to_date

        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def to_persian(num):
            return str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

        context["from_date"] = to_persian(jdatetime.date.fromgregorian(date=self.from_date).strftime("%Y/%m/%d"))
        context["to_date"] = to_persian(jdatetime.date.fromgregorian(date=self.to_date).strftime("%Y/%m/%d"))
        return context

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')  # یا تابع is_admin خودت
class LedgerReportView(ListView):
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
        start_date_str = self.request.GET.get("start_date")
        end_date_str = self.request.GET.get("end_date")
        payment_method_id = self.request.GET.get("payment_method")

        default_dates = self.get_default_dates()
        try:
            start_date = gdatetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else default_dates['default_start_date']
            end_date = gdatetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else default_dates['default_end_date']
        except (ValueError, TypeError):
            start_date = default_dates['default_start_date']
            end_date = default_dates['default_end_date']
        
        # همه پرداخت‌ها و دریافت‌ها
        pay_qs = Pay.objects.select_related('pay_type', 'source_type', 'bank').all()
        receipt_qs = Receipt.objects.select_related('receipt_type', 'source_type', 'bank').all()

        # فیلتر تاریخ
        pay_qs = pay_qs.filter(date__gte=start_date, date__lte=end_date)
        receipt_qs = receipt_qs.filter(date__gte=start_date, date__lte=end_date)

        # فیلتر بانک
        if bank_id:
            pay_qs = pay_qs.filter(bank_id=bank_id)
            receipt_qs = receipt_qs.filter(bank_id=bank_id)

        # فیلتر روش پرداخت
        if payment_method_id:
            pay_qs = pay_qs.filter(source_type_id=payment_method_id)
            receipt_qs = receipt_qs.filter(source_type_id=payment_method_id)

        # اضافه کردن نوع تراکنش برای مرتب‌سازی و محاسبه
        pay_list = [{'obj': p, 'type': 'pay', 'amount': -p.amount} for p in pay_qs]
        receipt_list = [{'obj': r, 'type': 'receipt', 'amount': r.amount} for r in receipt_qs]

        # ادغام و مرتب‌سازی بر اساس تاریخ و id
        all_tx = sorted(pay_list + receipt_list, key=lambda x: (x['obj'].date, getattr(x['obj'], 'id', 0)))
    
        return all_tx

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_dates = self.get_default_dates()
        bank_id = self.request.GET.get("bank")
        start_date_str = self.request.GET.get("start_date", default_dates['default_start_date_str'])
        end_date_str = self.request.GET.get("end_date", default_dates['default_end_date_str'])
        
        try:
            start_date_str = start_date_str.replace('/','-')
            start_date_j = jdatetime.date.fromisoformat(start_date_str)
            start_date = start_date_j.togregorian()
            # end_date = gdatetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_date_str = end_date_str.replace('/', '-')
            end_date_j = jdatetime.date.fromisoformat(end_date_str)
            end_date = end_date_j.togregorian()
        except (ValueError, TypeError):
            start_date = default_dates['default_start_date']
            end_date = default_dates['default_end_date']
        
        # موجودی اولیه
        opening_balance = 0
        if bank_id:
            opening_balance += sum(p.amount for p in Pay.objects.filter(bank_id=bank_id, date__lt=start_date))
            opening_balance -= sum(r.amount for r in Receipt.objects.filter(bank_id=bank_id, date__lt=start_date))
        else:
            opening_balance += sum(p.amount for p in Pay.objects.filter(date__lt=start_date))
            opening_balance -= sum(r.amount for r in Receipt.objects.filter(date__lt=start_date))

        running_balance = opening_balance
        total_amount = opening_balance
        increase_count = 0
        decrease_count = 0
        if opening_balance != 0:
            rows = [{
                "tx": type("Tx", (), {
                    "date": start_date,
                    "transaction_type": type("TType", (), {"name": "مانده اولیه"})(),
                    "amount": opening_balance,
                    "description": ""
                })(),
                "balance": opening_balance,
                "amount_with_effect": None,
                "is_opening": True
            }]
        else :
            rows = []
        for item in context["transactions"]:
            tx = item['obj']
            amount_with_effect = item['amount']
            running_balance += amount_with_effect
            total_amount += amount_with_effect

            if item['type'] == 'receipt':
                increase_count += 1
            else:
                decrease_count += 1

            rows.append({
                "tx": tx,
                "balance": running_balance,
                "amount_with_effect": amount_with_effect,
                "type": item['type'],
                "is_opening": False
            })

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
            "default_start_date": start_date_str,
            "default_end_date": end_date_str,
            "selected_start_date": start_date,
            "selected_end_date": end_date,
            "bank_id": bank_id,
        })
        return context


class TreasuryDashboardView(ListView):
    template_name = "app/treasury_dashboard.html"
    context_object_name = "methods"

    def get_queryset(self):
        methods = []

        # تمام روش‌های پرداخت
        payment_methods = PaymentMethod.objects.all()

        for method in payment_methods:
            if method.requires_bank:
                # برای هر حساب بانکی
                for bank in Bank.objects.all():
                    # محاسبه موجودی و آخرین تاریخ
                    total_receipt = Receipt.objects.filter(source_type=method, bank=bank).aggregate(total=models.Sum('amount'))['total'] or 0
                    total_pay = Pay.objects.filter(source_type=method, bank=bank).aggregate(total=models.Sum('amount'))['total'] or 0
                    balance = total_receipt - total_pay

                    last_tx_date_receipt = Receipt.objects.filter(source_type=method, bank=bank).order_by('-date').first()
                    last_tx_date_pay = Pay.objects.filter(source_type=method, bank=bank).order_by('-date').first()
                    last_tx_date = max(filter(None, [last_tx_date_receipt.date if last_tx_date_receipt else None,
                                                     last_tx_date_pay.date if last_tx_date_pay else None]), default=None)

                    methods.append({
                        "name": f"{method.name} - {bank.name}",
                        "balance": balance,
                        "last_tx_date": last_tx_date,
                        "payment_method_id": method.id,
                        "bank_id": bank.id,
                    })
            else:
                # نقد
                total_receipt = Receipt.objects.filter(source_type=method, bank__isnull=True).aggregate(total=models.Sum('amount'))['total'] or 0
                total_pay = Pay.objects.filter(source_type=method, bank__isnull=True).aggregate(total=models.Sum('amount'))['total'] or 0
                balance = total_receipt - total_pay

                last_tx_date_receipt = Receipt.objects.filter(source_type=method, bank__isnull=True).order_by('-date').first()
                last_tx_date_pay = Pay.objects.filter(source_type=method, bank__isnull=True).order_by('-date').first()
                last_tx_date = max(filter(None, [last_tx_date_receipt.date if last_tx_date_receipt else None,
                                                 last_tx_date_pay.date if last_tx_date_pay else None]), default=None)

                methods.append({
                    "name": method.name,
                    "balance": balance,
                    "last_tx_date": last_tx_date,
                    "payment_method_id": method.id,
                    "bank_id": None,
                })

        return methods


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

class CalendarView(ListView):
    template_name = 'app/calendar.html'
    model = Appointment
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        personnel_user = getattr(self.request.user, "personnel_profile", None)
        if self.request.user.is_superuser:
            context['personnel_list'] = Personnel.objects.all()
        else:
            
            context['personnel_list'] = Personnel.objects.filter(id=personnel_user.personnel.id)
        
        if personnel_user:
            context['selected_personnel'] = personnel_user.personnel.id
        else:

            personnel_filter_id = self.request.GET.get('personnel')
            if not personnel_filter_id :
                personnel_filter = Personnel.objects.first()
                personnel_filter_id = personnel_filter.id
            context['selected_personnel'] = personnel_filter_id

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
                
                start_time = gdatetime.fromisoformat(start_time_str)
                end_time = gdatetime.fromisoformat(end_time_str)
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'فرمت تاریخ نامعتبر است',
                    'error_details': str(e)  # اضافه کردن جزئیات خطا
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
            
            customer_mobile = appointment.customer.mobile
            customer_name = appointment.customer.fname
            customer_full_name = appointment.customer.name
            work = appointment.work.work_name
            appointment_time=appointment.start_time
            personnel_name = appointment.personnel.fname

            
            customer_msg = customer_sms(customer_name, work, appointment_time)
            send_sms(customer_mobile, customer_msg)

            # ===== ارسال پیامک به پرسنل =====
            personnel_mobile = appointment.personnel.mobile
            personnel_msg = personnel_sms(personnel_name, customer_full_name, appointment_time)
            send_sms(personnel_mobile, personnel_msg)


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

@login_required
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

@login_required
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
                appointment.start_time = gdatetime.fromisoformat(data.get('start_time'))
                appointment.end_time = gdatetime.fromisoformat(data.get('end_time'))
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'فرمت تاریخ نامعتبر است'
                }, status=400)

            # بررسی تداخل زمان‌ها
            conflict = Appointment.objects.filter(
                personnel_id=appointment.personnel_id,
                start_time__lt=appointment.end_time,
                end_time__gt=appointment.start_time,
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

@login_required
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

@login_required
def personnel_works(request):
    personnel_id = request.GET.get('personnel_id')
    if not personnel_id:
        return JsonResponse([], safe=False)
    commissions = PersonnelCommission.objects.filter(
        personnel_id=personnel_id
    ).select_related('work')
    
    data = [
        {"id": c.work.id, "work_name": c.work.work_name}
        for c in commissions
    ]
    return JsonResponse(data, safe=False)

@login_required
def gallery_view(request):
    images = SaleImage.objects.all()
    
    # فیلتر بر اساس پرسنل اگر کاربر ادمین نیست
    if not request.user.is_superuser:
        try:
            personnel_user = PersonnelUser.objects.get(user=request.user)
            personnel = personnel_user.personnel
            images = images.filter(sale__personnel=personnel)
        except PersonnelUser.DoesNotExist:
            images = SaleImage.objects.none()
    
    # فیلتر بر اساس مشتری (از طریق پارامتر GET)
    customer_filter = request.GET.get('customer')
    if customer_filter:
        images = images.filter(sale__customer__id=customer_filter)
    
    # فیلتر بر اساس پرسنل (از طریق پارامتر GET)
    personnel_filter = request.GET.get('personnel')
    print(personnel_filter)
    
    if personnel_filter and request.user.is_superuser:
        images = images.filter(sale__personnel__id=personnel_filter)
        personnel_filter = Personnel.objects.filter(id=personnel_filter).first()
    else:
    # اگر انتخابی نبود، اولین پرسنل موجود رو بیاور
        personnel_filter = Personnel.objects.first()
    


    # در نهایت فقط عکس‌های "بعد"
    images = images.filter(image_type=SaleImage.AFTER)
    
    # دریافت لیست مشتریان و پرسنل برای فیلترها
    from .models import Customer, Personnel
    customers = Customer.objects.all()
    personnel_list = Personnel.objects.all() if request.user.is_superuser else []
    
    context = {
        'images': images,
        'customers': customers,
        'personnel_list': personnel_list,
        'selected_customer': customer_filter,
        'selected_personnel': personnel_filter,
    }
    
    return render(request, 'app/gallery.html', context)

class HomeDashboardView(TemplateView):
    template_name = "app/home_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_super = user.is_superuser

        personnel = None
        if not is_super:
            try:
                personnel = user.personnel_profile.personnel
            except:
                personnel = None

        # آخرین ۳۰ روز
        today = timezone.now().date()
        last_30_days = [today - timezone.timedelta(days=i) for i in range(29, -1, -1)]

        # ===== 1. مانده پرداخت‌ها =====
        balances_chart = []

        if is_super:
            payment_methods = PaymentMethod.objects.all()
            balances = {}
            for method in payment_methods:
                if method.requires_bank:
                    for bank in Bank.objects.all():
                        line_data = []
                        for d in last_30_days:
                            pays = Pay.objects.filter(date=d, source_type=method, bank=bank)
                            total = pays.aggregate(total=Sum("amount"))["total"] or 0
                            line_data.append({
                                "date": jdatetime.date.fromgregorian(date=d).strftime("%Y-%m-%d"),
                                "balance": int(total)
                            })
                        balances[method.name + " - " + bank.name] = line_data
                else:
                    line_data = []
                    for d in last_30_days:
                        pays = Pay.objects.filter(date=d, source_type=method, bank__isnull=True)
                        total = pays.aggregate(total=Sum("amount"))["total"] or 0
                        line_data.append({
                            "date": jdatetime.date.fromgregorian(date=d).strftime("%Y-%m-%d"),
                            "balance": int(total)
                        })
                    balances[method.name] = line_data

            for key, data in balances.items():
                balances_chart.append({"name": key, "data": data})

        else:
            line_data = []
            for d in last_30_days:
                pays = Pay.objects.filter(date=d, personnel=personnel)
                total = pays.aggregate(total=Sum("amount"))["total"] or 0
                total = int(total)
                line_data.append({
                    "date": jdatetime.date.fromgregorian(date=d).strftime("%Y-%m-%d"),
                    "balance": total
                })
            balances_chart = [{"name": "پرداخت‌ها", "data": line_data}]

        context["balances_chart"] = balances_chart

        # ===== 2. فروش روزانه =====
        sales = Sale.objects.all()
        if not is_super and personnel:
            sales = sales.filter(personnel=personnel)

        daily_sales = (
            sales.annotate(day=TruncDate("date"))
                 .values("day")
                 .annotate(commission=Sum("commission_amount"), total=Sum("price"))
                 .order_by("day")
        )
        sales_chart = []
        for row in daily_sales:
            sales_chart.append({
                "date": jdatetime.date.fromgregorian(date=row["day"]).strftime("%Y-%m-%d"),
                "commission": int(row["commission"]) or 0,
                "remainder": ((int(row["total"]) or 0) - (int(row["commission"]) or 0)) if is_super else 0
            })
        context["sales_chart"] = sales_chart

        # ===== 3. رزروها =====
        appointments = Appointment.objects.all()
        if not is_super and personnel:
            appointments = appointments.filter(personnel=personnel)

        daily_appts = (
            appointments.annotate(day=TruncDate("start_time"))
                        .values("day")
                        .annotate(count=Count("id"))
                        .order_by("day")
        )
        appt_chart = []
        for row in daily_appts:
            appt_chart.append({
                "date": jdatetime.date.fromgregorian(date=row["day"]).strftime("%Y-%m-%d"),
                "count": row["count"]
            })
        context["appt_chart"] = appt_chart

        # ===== 4. تعداد فاکتورها =====
        sales_count = (
            sales.annotate(day=TruncDate("date"))
                 .values("day")
                 .annotate(count=Count("id"))
                 .order_by("day")
        )
        sales_count_chart = []
        for row in sales_count:
            sales_count_chart.append({
                "date": jdatetime.date.fromgregorian(date=row["day"]).strftime("%Y-%m-%d"),
                "count": row["count"]
            })
        context["sales_count_chart"] = sales_count_chart

        context["is_super"] = is_super
        return context
class PayUpdateView(UpdateView):
    template_name = "app/edit_pay.html"
    form_class = PayForm
    model = Pay
    success_url = reverse_lazy("pay_list")

    def form_valid(self, form):
        pay = form.save()
        # اگر درخواست Ajax بود، خروجی JSON بده
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            import jdatetime
            return JsonResponse({
                            "success": True,
                            "id": pay.id,
                            "date": pay.date, 
                            "pay_type": pay.pay_type.name if pay.pay_type else "",
                            "personnel": pay.personnel.name if pay.personnel else "",
                            "amount": f"{pay.amount:,}",
                            "source_type": pay.source_type.name if pay.source_type else "",
                            "bank": pay.bank.name if pay.bank else "",
    })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """قبل از اعتبارسنجی فرم تاریخ فارسی/اعداد فارسی رو تبدیل می‌کنیم"""
        data = request.POST.copy()
        date_val = data.get("date")
        if date_val:
            try:
                date_val = persian_to_english(date_val)  # تبدیل اعداد فارسی به انگلیسی
                parts = list(map(int, date_val.split("/")))
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data["date"] = date_val
            except Exception as e:
                print("❌ Error parsing date in UpdateView:", e)
        request.POST = data
        return super().post(request, *args, **kwargs)
class ReceiptUpdateView(UpdateView):
    template_name = "app/edit_Receipt.html"
    form_class = ReceiptForm    
    model = Receipt
    success_url = reverse_lazy("Receipt_list")


def sale_images_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    images = sale.images.all()  # همه عکس‌ها
    return render(request, 'app/sale_images.html', {'sale': sale, 'images': images})

@login_required
def finance_menu(request):
    return render(request, "app/finance_menu.html")

def settings_menu(request):
    menu_items = []

    def add_item(name, icon, url_name):
        try:
            url = reverse(url_name)
            menu_items.append({"name": name, "icon": icon, "url": url})
        except NoReverseMatch:
            pass  # اگر url ثبت نشده باشه، آیتم ساخته نمیشه


    # کاربران
    # add_item("کاربر جدید", "fas fa-user-plus", "create_user")
    add_item("کاربران", "fas fa-users", "users")

    # پرسنل
    # add_item("پرسنل جدید", "fas fa-user-tie", "new_personnel")
    add_item("لیست پرسنل", "fas fa-id-card", "personnel_list")

    # خدمات
    # add_item("خدمت جدید", "fas fa-briefcase", "new_work")
    add_item("خدمات", "fas fa-tasks", "works")

    # مشتری
    # add_item("مشتری جدید", "fas fa-user", "new_customer")
    add_item("مشتریان", "fas fa-address-book", "customers")

    # add_item("کمیسیون جدید", "fas fa-plus-circle", "new_commission")
    add_item("کمیسیون پرسنل", "fas fa-percent", "commissions")

    add_item("تغییر رمز عبور", "fas fa-key", "password_change")
    add_item("خروج", "fas fa-sign-out-alt", "logout")

    return render(request, "app/settings_menu.html", {"menu_items": menu_items})



class PersonnelListView(ListView):
    model = Personnel
    template_name = "app/personnel_list.html"
    context_object_name = "personnels"

class PersonnelCreateView(CreateView):
    model = Personnel
    fields = ["fname", "lname", "mobile", "comment", "on_site", "is_active"]
    template_name = "app/personnel_form.html"
    success_url = reverse_lazy("personnel_list")

class PersonnelUpdateView(UpdateView):
    model = Personnel
    fields = ["fname", "lname", "mobile", "comment", "on_site", "is_active"]
    template_name = "app/personnel_form.html"
    success_url = reverse_lazy("personnel_list")

class PersonnelDeleteView(DeleteView):
    model = Personnel
    template_name = "app/personnel_confirm_delete.html"
    success_url = reverse_lazy("personnel_list")


class WorkListView(ListView):
    model = Work
    template_name = "settings/work_list.html"
    context_object_name = "works"


class WorkCreateView(CreateView):
    model = Work
    fields = ["work_name"]
    template_name = "settings/work_form.html"
    success_url = reverse_lazy("works")


class WorkUpdateView(UpdateView):
    model = Work
    fields = ["work_name"]
    template_name = "settings/work_form.html"
    success_url = reverse_lazy("works")


class WorkDeleteView(DeleteView):
    model = Work
    template_name = "settings/work_confirm_delete.html"
    success_url = reverse_lazy("works")


class PersonnelCommissionListView(ListView):
    model = PersonnelCommission
    template_name = "settings/commission_list.html"
    context_object_name = "commissions"

    def get_queryset(self):
        show_history = self.request.GET.get("history") == "1"

        if show_history:
            return PersonnelCommission.objects.all().order_by("-start_date")

        # فقط آخرین رکورد برای هر پرسنل و خدمت
        latest_ids = (
            PersonnelCommission.objects
            .values("personnel_id", "work_id")
            .annotate(max_id=Max("id"))
            .values_list("max_id", flat=True)
        )
        return PersonnelCommission.objects.filter(id__in=latest_ids).order_by("personnel__lname", "work__work_name")



class PersonnelCommissionCreateView(CreateView):
    model = PersonnelCommission
    fields = ["personnel", "work", "percentage", "start_date", "end_date"]
    template_name = "settings/commission_form.html"
    success_url = reverse_lazy("commissions")


class PersonnelCommissionUpdateView(UpdateView):
    model = PersonnelCommission
    fields = ["personnel", "work", "percentage", "start_date", "end_date"]
    template_name = "settings/commission_form.html"
    success_url = reverse_lazy("commissions")



class PersonnelCommissionDeleteView(DeleteView):
    model = PersonnelCommission
    template_name = "settings/commission_confirm_delete.html"
    success_url = reverse_lazy("commissions")
