import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, NoReverseMatch, reverse
from app.models import *
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.utils import timezone
from jalali_date import datetime2jalali, date2jalali
from django.db.models import Sum, F, Q, Count, Max, Min, DateField
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
import logging
from django.db.models.functions import Cast

MAX_IMAGES = 4
MAX_SIZE = (1024, 1024)  # طول یا عرض حداکثر
JPEG_QUALITY = 75        # کیفیت JPEG

def is_admin(user):
    return user.is_superuser

def to_persian_numbers(s):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    return ''.join(persian_digits[int(ch)] if ch.isdigit() else ch for ch in str(s))


@login_required
def home (request):
    sales = Sale.objects.all()
    return render(request, "app/home.html", {"sales": sales})



logger = logging.getLogger("app")


class SaleCreateView(CreateView, UserTrackMixin):
    template_name = "app/new_sale.html"
    form_class = SaleForm
    model = Sale
    success_url = reverse_lazy("sales")

    def form_valid(self, form):
        sale = form.save()
        logger.info(
            "Sale created successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "sale_id": sale.id,
                "customer": getattr(sale.customer, "id", None),
                "price": sale.price,
            },
        )
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"sale_id": sale.id})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid sale form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid sale form",
                extra={
                    "errors": form.errors.as_json(),
                },
            )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_time = timezone.now().astimezone(timezone.get_current_timezone())
        context["current_time"] = current_time.strftime("%H:%M")
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
        context["before_images"] = images.filter(image_type=SaleImage.BEFORE)
        context["after_images"] = images.filter(image_type=SaleImage.AFTER)
        context["empty_before"] = 1 - context["before_images"].count()
        context["empty_after"] = 3 - context["after_images"].count()
        return context

    def form_valid(self, form):
        self.object = form.save()

        # لاگ ذخیره موفق
        logger.info(
            "Sale updated successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "sale_id": self.object.id,
                "customer": getattr(self.object.customer, "id", None),
                "price": self.object.price,
            },
        )

        # تصاویر قبل
        before_images = self.request.FILES.getlist("images_before")
        for img in before_images[:1]:
            compressed = compress_image(img)
            SaleImage.objects.create(
                sale=self.object, image=compressed, image_type=SaleImage.BEFORE
            )
            logger.info(
                "Before image added to sale",
                extra={"sale_id": self.object.id, "filename": img.name},
            )

        # تصاویر بعد
        after_images = self.request.FILES.getlist("images_after")
        for img in after_images[:3]:
            compressed = compress_image(img)
            SaleImage.objects.create(
                sale=self.object, image=compressed, image_type=SaleImage.AFTER
            )
            logger.info(
                "After image added to sale",
                extra={"sale_id": self.object.id, "filename": img.name},
            )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"sale_id": self.object.id})

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid update sale form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid update sale form",
                extra={"errors": form.errors.as_json()},
            )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class SaleListView(ListView):
    template_name = "app/sale_list.html"
    model = Sale
    context_object_name = "sales"
    
    def get_queryset(self):
        selected_date_str = self.request.GET.get("date")

        try:
            if selected_date_str:
                jalali_date = jdatetime.date.fromisoformat(selected_date_str)
                target_date = jalali_date.togregorian()
            else:
                target_date = timezone.now().date()
            start_datetime = gdatetime.combine(target_date, gdatetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            if self.request.user.is_superuser:
                sales = (
                    Sale.objects.filter(date__gte=start_datetime, date__lt=end_datetime)
                    .order_by("-date")
                )
                print(sales.__len__)
                print(target_date)  
                logger.info(
                    "Admin viewed sales list",
                    extra={
                        "user": getattr(self.request.user, "id", None),
                        "date": str(target_date),
                        "count": sales.count(),
                    },
                )
            else:
                personneluser = getattr(self.request.user, "personnel_profile", None)
                personnel = personneluser.get_personnel() if personneluser else None
                if personnel:
                    sales = (
                        Sale.objects.filter(date__gte=start_datetime, date__lt=end_datetime, personnel=personnel)
                        .annotate(display_price=F("commission_amount"))
                        .order_by("-date")
                    )
                    logger.info(
                        "Personnel viewed their sales list",
                        extra={
                            "user": getattr(self.request.user, "id", None),
                            "personnel": personnel.id,
                            "date": str(target_date),
                            "count": sales.count(),
                        },
                    )
              

            return sales

        except Exception as e:
            logger.error(
                "Error in date processing for sales list",
                exc_info=True,
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "date_str": selected_date_str,
                },
            )
            return Sale.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()

        selected_date = self.request.GET.get("date")
        if selected_date:
            context["selected_jalali_date"] = selected_date
            context["date_formatted"] = selected_date
        else:
            jalali_today_str = datetime2jalali(today).strftime("%Y-%m-%d")
            context["selected_jalali_date"] = to_persian_numbers(jalali_today_str)
            context["date_formatted"] = jalali_today_str

        sales_today = self.get_queryset()
        context["sales_today"] = sales_today

        total_price = sales_today.aggregate(total=Sum("price"))["total"] or 0
        total_commission = (
            sales_today.aggregate(total=Sum("commission_amount"))["total"] or 0
        )
        context["total_price"] = total_price
        context["total_commission"] = total_commission

        return context

@csrf_exempt
def delete_sale_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_id = data.get('image_id')
        try:
            img = SaleImage.objects.get(id=image_id)
            img.image.delete()  # حذف فایل از دیسک
            img.delete()        # حذف ردیف از دیتابیس
            logger.info(
                "Sale image deleted successfully",
                extra={
                    "user": getattr(request.user, "id", None),
                    "image_id": image_id,
                    "sale_id": getattr(img.sale, "id", None),
                },
            )
            return JsonResponse({'status': 'ok'})
        except SaleImage.DoesNotExist:
            logger.warning(
                "Attempt to delete non-existent sale image",
                extra={
                    "user": getattr(request.user, "id", None),
                    "image_id": image_id,
                },
            )
            return JsonResponse({'status': 'error'})

class SaleDeleteView(DeleteView):
    template_name = "app/delete_sale.html"
    model = Sale
    success_url = reverse_lazy("home")
    context_object_name = "sale"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        sale_id = self.object.id
        customer_id = getattr(self.object.customer, "id", None)
        response = super().delete(request, *args, **kwargs)
        logger.info(
            "Sale deleted successfully",
            extra={
                "user": getattr(request.user, "id", None),
                "sale_id": sale_id,
                "customer_id": customer_id,
            },
        )
        return response




class CustomerCreateView(CreateView):
    template_name = "app/new_customer.html"
    form_class = CustomerForm
    success_url = reverse_lazy("customers")

    def post(self, request, *args, **kwargs):
        if "import_excel" in request.POST and request.FILES.get("excel_file"):
            excel_file = request.FILES["excel_file"]
            try:
                df = pd.read_excel(excel_file)
                count = 0
                for _, row in df.iterrows():
                    Customer.objects.update_or_create(
                        mobile=row["mobile"],
                        defaults={"name": row["name"]},
                    )
                    count += 1

                logger.info(
                    "Customers imported from Excel",
                    extra={
                        "user": getattr(request.user, "id", None),
                        "file_name": excel_file.name,
                        "count": count,
                    },
                )

                messages.success(request, "مشتریان با موفقیت از اکسل وارد شدند.")

            except Exception as e:
                logger.error(
                    "Error importing customers from Excel",
                    exc_info=True,
                    extra={
                        "user": getattr(request.user, "id", None),
                        "file_name": excel_file.name,
                    },
                )
                messages.error(request, f"خطا در وارد کردن فایل: {e}")

            return self.get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)

        logger.info(
            "Customer created successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "customer_id": self.object.id,
            },
        )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"customer_id": self.object.id})
        return response

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid customer form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid customer form",
                extra={"errors": form.errors.as_json()},
            )
        return super().form_invalid(form)

class CustomerUpdateView(UpdateView):
    template_name = "app/edit_customer.html"
    model = Customer
    fields = ["name", "mobile", "black_list", "black_list_reason"]
    success_url = reverse_lazy("customers")
    context_object_name = "customer"

    def form_valid(self, form):
        response = super().form_valid(form)

        logger.info(
            "Customer updated successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "customer_id": self.object.id,
                "fields_updated": list(form.changed_data),
            },
        )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"customer_id": self.object.id})
        return response

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid customer update form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "customer_id": getattr(self.get_object(), "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid customer update form",
                extra={
                    "errors": form.errors.as_json(),
                },
            )
        return super().form_invalid(form)
class CustomerDeleteView(DeleteView):
    template_name = "app/delete_customer.html"
    model = Customer
    success_url = reverse_lazy("customers")
    context_object_name = "customer"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        customer_id = self.object.id
        customer_name = getattr(self.object, "name", None)
        try:
            response = super().delete(request, *args, **kwargs)
            logger.info(
                "Customer deleted successfully",
                extra={
                    "user": getattr(request.user, "id", None),
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                },
            )
            return response
        except Exception as e:
            logger.error(
                "Error deleting customer",
                exc_info=True,
                extra={
                    "user": getattr(request.user, "id", None),
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                },
            )
            raise  # دوباره پرتاب می‌کنه تا جنگو خودش handle کنه

def get_payment_data(request):
    try:
        payment_methods = list(PaymentMethod.objects.all().values("id", "name", "requires_bank"))
        banks = list(Bank.objects.all().values("id", "name"))

        logger.info(
            "Payment data retrieved successfully",
            extra={
                "user": getattr(request.user, "id", None),
                "payment_methods_count": len(payment_methods),
                "banks_count": len(banks),
            },
        )

        return JsonResponse({
            "payment_methods": payment_methods,
            "banks": banks
        })

    except Exception as e:
        logger.error(
            "Error retrieving payment data",
            exc_info=True,
            extra={
                "user": getattr(request.user, "id", None),
            },
        )
        return JsonResponse({"error": "Failed to load payment data"}, status=500)



@csrf_exempt
def save_receipts(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            sale_id = data.get("sale_id")
            payments = data.get("payments", [])

            sale = get_object_or_404(Sale, pk=sale_id)
            logger.info(
                "Saving receipts for sale",
                extra={
                    "user": getattr(request.user, "id", None),
                    "sale_id": sale_id,
                    "customer_id": getattr(sale.customer, "id", None),
                    "payments_count": len(payments),
                },
            )

            customer_receipt_type = ReceiptType.objects.filter(is_customer=True).first()
            if not customer_receipt_type:
                logger.error(
                    "Customer receipt type not defined",
                    extra={"user": getattr(request.user, "id", None)},
                )
                return JsonResponse(
                    {"status": "error", "message": "نوع دریافت مشتری تعریف نشده است"},
                    status=400,
                )

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
                logger.info(
                    "Receipt created",
                    extra={
                        "user": getattr(request.user, "id", None),
                        "sale_id": sale_id,
                        "amount": amount,
                        "method_id": payment.get("method_id"),
                        "bank_id": payment.get("bank_id"),
                    },
                )

            return JsonResponse({"status": "ok"})

        except Exception as e:
            logger.error(
                "Error saving receipts",
                exc_info=True,
                extra={"user": getattr(request.user, "id", None)},
            )
            return JsonResponse({"status": "error", "message": "خطا در ثبت دریافت‌ها"}, status=500)


# class TransactionCreateView(CreateView):
#     template_name = "app/new_transaction.html"
#     form_class = TransactionForm
#     success_url = reverse_lazy("home")
    

#     def form_valid(self, form):
#         response = super().form_valid(form)
#         if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
#             return JsonResponse({'transaction_id': self.object.id})
#         return response
    
class PayCreateView(CreateView):
    template_name = "app/new_pay.html"
    form_class = PayForm
    success_url = reverse_lazy("pay_list")
    source_types = PaymentMethod.objects.all()
    pay_type = PayType.objects.all()

    def form_valid(self, form):
        response = super().form_valid(form)

        logger.info(
            "Payment created successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "pay_id": self.object.id,
                "amount": getattr(self.object, "amount", None),
                "source_type_id": getattr(self.object, "source_type_id", None),
            },
        )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"pay_id": self.object.id})
        return response

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid payment form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid payment form",
                extra={"errors": form.errors.as_json()},
            )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        date_val = data.get("date")
        if date_val:
            try:
                date_val = persian_to_english(date_val)
                parts = list(map(int, date_val.split("/")))
                import jdatetime
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data["date"] = date_val
            except Exception as e:
                logger.warning(
                    "Failed to convert Persian date to Gregorian",
                    extra={
                        "user": getattr(request.user, "id", None),
                        "input_date": data.get("date"),
                        "error": str(e),
                    },
                )
        request.POST = data
        return super().post(request, *args, **kwargs)


class ReceiptCreateView(CreateView):
    template_name = "app/new_receipt.html"
    form_class = ReceiptForm
    success_url = reverse_lazy("receipt_list")
    receipt_types = ReceiptType.objects.all()
    source_types = PaymentMethod.objects.all()

    def form_valid(self, form):
        response = super().form_valid(form)

        logger.info(
            "Receipt created successfully",
            extra={
                "user": getattr(self.request.user, "id", None),
                "receipt_id": self.object.id,
                "amount": getattr(self.object, "amount", None),
                "source_type_id": getattr(self.object, "source_type_id", None),
                "receipt_type_id": getattr(self.object, "receipt_type_id", None),
            },
        )

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"receipt_id": self.object.id})
        return response

    def form_invalid(self, form):
        if self.request.user.is_authenticated:
            logger.error(
                "Authenticated user submitted invalid receipt form",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "errors": form.errors.as_json(),
                },
            )
        else:
            logger.warning(
                "Anonymous user submitted invalid receipt form",
                extra={"errors": form.errors.as_json()},
            )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        date_val = data.get("date")
        if date_val:
            try:
                date_val = persian_to_english(date_val)
                parts = list(map(int, date_val.split("/")))
                import jdatetime
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data["date"] = date_val
            except Exception as e:
                logger.warning(
                    "Failed to convert Persian date to Gregorian in receipt form",
                    extra={
                        "user": getattr(request.user, "id", None),
                        "input_date": data.get("date"),
                        "error": str(e),
                    },
                )
        request.POST = data
        return super().post(request, *args, **kwargs)




class PayListView(ListView):
    model = Pay
    template_name = "app/pay_list.html"
    context_object_name = "pays"

    def get_queryset(self):
        qs = super().get_queryset()
        today = timezone.localdate()
        default_from = today - timedelta(days=7)
        default_to = today

        from_date_str = self.request.GET.get("from_date")
        to_date_str = self.request.GET.get("to_date")

        from_date = default_from
        to_date = default_to

        # تبدیل تاریخ شروع
        if from_date_str:
            try:
                j_from = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d").date()
                from_date = j_from.togregorian()
            except Exception as e:
                logger.warning(
                    "Failed to parse from_date in PayListView",
                    extra={"user": getattr(self.request.user, "id", None),
                           "input_date": from_date_str,
                           "error": str(e)},
                )

        # تبدیل تاریخ پایان
        if to_date_str:
            try:
                j_to = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d").date()
                to_date = j_to.togregorian()
            except Exception as e:
                logger.warning(
                    "Failed to parse to_date in PayListView",
                    extra={"user": getattr(self.request.user, "id", None),
                           "input_date": to_date_str,
                           "error": str(e)},
                )

        qs = qs.filter(date__range=[from_date, to_date])
        self.from_date = from_date
        self.to_date = to_date

        logger.info(
            "Pay list retrieved",
            extra={
                "user": getattr(self.request.user, "id", None),
                "from_date": str(from_date),
                "to_date": str(to_date),
                "count": qs.count(),
            },
        )

        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["from_date"] = english_to_persian(
            jdatetime.date.fromgregorian(date=self.from_date).strftime("%Y/%m/%d")
        )
        context["to_date"] = english_to_persian(
            jdatetime.date.fromgregorian(date=self.to_date).strftime("%Y/%m/%d")
        )

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
    template_name = "app/receipt_list.html"
    context_object_name = "receipts"

    def get_queryset(self):
        qs = super().get_queryset()

        today = timezone.localdate()
        default_from = today - timedelta(days=7)
        default_to = today

        from_date_str = self.request.GET.get("from_date")
        to_date_str = self.request.GET.get("to_date")

        from_date = default_from
        to_date = default_to

        # تبدیل تاریخ شروع
        if from_date_str:
            try:
                j_from = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d").date()
                from_date = j_from.togregorian()
            except Exception as e:
                logger.warning(
                    "Failed to parse from_date in ReceiptListView",
                    extra={
                        "user": getattr(self.request.user, "id", None),
                        "input_date": from_date_str,
                        "error": str(e),
                    },
                )

        # تبدیل تاریخ پایان
        if to_date_str:
            try:
                j_to = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d").date()
                to_date = j_to.togregorian()
            except Exception as e:
                logger.warning(
                    "Failed to parse to_date in ReceiptListView",
                    extra={
                        "user": getattr(self.request.user, "id", None),
                        "input_date": to_date_str,
                        "error": str(e),
                    },
                )

        qs = qs.filter(date__range=[from_date, to_date])

        self.from_date = from_date
        self.to_date = to_date

        logger.info(
            "Receipt list retrieved",
            extra={
                "user": getattr(self.request.user, "id", None),
                "from_date": str(from_date),
                "to_date": str(to_date),
                "count": qs.count(),
            },
        )

        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def to_persian(num):
            return str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

        context["from_date"] = to_persian(
            jdatetime.date.fromgregorian(date=self.from_date).strftime("%Y/%m/%d")
        )
        context["to_date"] = to_persian(
            jdatetime.date.fromgregorian(date=self.to_date).strftime("%Y/%m/%d")
        )
        return context

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView
from django.utils import timezone
from datetime import timedelta
import jdatetime
from app.models import Pay, Receipt, PaymentMethod, Bank
from django.utils.dateparse import parse_date
import logging

logger = logging.getLogger(__name__)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')
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
            start_date = parse_date(start_date_str) if start_date_str else default_dates['default_start_date']
            end_date = parse_date(end_date_str) if end_date_str else default_dates['default_end_date']
        except Exception as e:
            logger.warning(
                "LedgerReportView: Failed to parse start/end date",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "start_date_str": start_date_str,
                    "end_date_str": end_date_str,
                    "error": str(e)
                }
            )
            start_date = default_dates['default_start_date']
            end_date = default_dates['default_end_date']

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

        pay_list = [{'obj': p, 'type': 'pay', 'amount': -p.amount} for p in pay_qs]
        receipt_list = [{'obj': r, 'type': 'receipt', 'amount': r.amount} for r in receipt_qs]

        all_tx = sorted(pay_list + receipt_list, key=lambda x: (x['obj'].date, getattr(x['obj'], 'id', 0)))

        logger.info(
            "Ledger report queryset prepared",
            extra={
                "user": getattr(self.request.user, "id", None),
                "bank_id": bank_id,
                "payment_method_id": payment_method_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "total_transactions": len(all_tx),
            }
        )

        return all_tx

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_dates = self.get_default_dates()
        bank_id = self.request.GET.get("bank")
        start_date_str = self.request.GET.get("start_date", default_dates['default_start_date_str'])
        end_date_str = self.request.GET.get("end_date", default_dates['default_end_date_str'])

        try:
            start_date_j = jdatetime.date.fromisoformat(start_date_str.replace('/','-'))
            start_date = start_date_j.togregorian()
            end_date_j = jdatetime.date.fromisoformat(end_date_str.replace('/','-'))
            end_date = end_date_j.togregorian()
        except Exception as e:
            logger.warning(
                "LedgerReportView: Failed to convert start/end dates to Gregorian",
                extra={
                    "user": getattr(self.request.user, "id", None),
                    "start_date_str": start_date_str,
                    "end_date_str": end_date_str,
                    "error": str(e)
                }
            )
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
        rows = []

        if opening_balance != 0:
            rows.append({
                "tx": type("Tx", (), {
                    "date": start_date,
                    "transaction_type": type("TType", (), {"name": "مانده اولیه"})(),
                    "amount": opening_balance,
                    "description": ""
                })(),
                "balance": opening_balance,
                "amount_with_effect": None,
                "is_opening": True
            })

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
        default_payment_method = payment_methods.filter(requires_bank=False).first() or payment_methods.first()

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

        logger.info(
            "Ledger report context prepared",
            extra={
                "user": getattr(self.request.user, "id", None),
                "bank_id": bank_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "rows_count": len(rows)
            }
        )

        return context


class TreasuryDashboardView(ListView):
    template_name = "app/treasury_dashboard.html"
    context_object_name = "methods"

    def get_queryset(self):
        methods = []

        payment_methods = PaymentMethod.objects.all()
        logger.info(f"TreasuryDashboard: calculating for {payment_methods.count()} payment methods",
                    extra={"user": getattr(self.request.user, "id", None)})

        for method in payment_methods:
            if method.requires_bank:
                for bank in Bank.objects.all():
                    try:
                        total_receipt = Receipt.objects.filter(source_type=method, bank=bank).aggregate(
                            total=models.Sum('amount'))['total'] or 0
                        total_pay = Pay.objects.filter(source_type=method, bank=bank).aggregate(
                            total=models.Sum('amount'))['total'] or 0
                        balance = total_receipt - total_pay

                        last_tx_date_receipt = Receipt.objects.filter(source_type=method, bank=bank).order_by('-date').first()
                        last_tx_date_pay = Pay.objects.filter(source_type=method, bank=bank).order_by('-date').first()
                        last_tx_date = max(filter(None, [
                            last_tx_date_receipt.date if last_tx_date_receipt else None,
                            last_tx_date_pay.date if last_tx_date_pay else None
                        ]), default=None)

                        methods.append({
                            "name": f"{method.name} - {bank.name}",
                            "balance": balance,
                            "last_tx_date": last_tx_date,
                            "payment_method_id": method.id,
                            "bank_id": bank.id,
                        })

                        logger.debug(
                            f"TreasuryDashboard: {method.name} - {bank.name}, balance={balance}, last_tx={last_tx_date}",
                            extra={"user": getattr(self.request.user, "id", None)}
                        )
                    except Exception as e:
                        logger.warning(
                            f"TreasuryDashboard: Failed to process {method.name} - {bank.name}: {e}",
                            extra={"user": getattr(self.request.user, "id", None)}
                        )
            else:
                try:
                    total_receipt = Receipt.objects.filter(source_type=method, bank__isnull=True).aggregate(
                        total=models.Sum('amount'))['total'] or 0
                    total_pay = Pay.objects.filter(source_type=method, bank__isnull=True).aggregate(
                        total=models.Sum('amount'))['total'] or 0
                    balance = total_receipt - total_pay

                    last_tx_date_receipt = Receipt.objects.filter(source_type=method, bank__isnull=True).order_by('-date').first()
                    last_tx_date_pay = Pay.objects.filter(source_type=method, bank__isnull=True).order_by('-date').first()
                    last_tx_date = max(filter(None, [
                        last_tx_date_receipt.date if last_tx_date_receipt else None,
                        last_tx_date_pay.date if last_tx_date_pay else None
                    ]), default=None)

                    methods.append({
                        "name": method.name,
                        "balance": balance,
                        "last_tx_date": last_tx_date,
                        "payment_method_id": method.id,
                        "bank_id": None,
                    })

                    logger.debug(
                        f"TreasuryDashboard: {method.name}, balance={balance}, last_tx={last_tx_date}",
                        extra={"user": getattr(self.request.user, "id", None)}
                    )
                except Exception as e:
                    logger.warning(
                        f"TreasuryDashboard: Failed to process {method.name}: {e}",
                        extra={"user": getattr(self.request.user, "id", None)}
                    )

        logger.info(f"TreasuryDashboard: completed, total entries={len(methods)}",
                    extra={"user": getattr(self.request.user, "id", None)})

        return methods



@login_required
@user_passes_test(is_admin)
def create_user_view(request):
    logger.info("Accessed create_user_view", extra={"user": getattr(request.user, "id", None)})

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)  # ⚡ هش پسورد قبل از ذخیره
            password = form.cleaned_data.get("password")
            if password:
                user.set_password(password)  # هش کردن پسورد
            user.save()  # حالا کاربر را ذخیره کن
            
            messages.success(request, "کاربر با موفقیت ساخته شد.")
            logger.info(
                "User created successfully",
                extra={"user_id": user.id, "created_by": getattr(request.user, "id", None)}
            )
            return redirect('users')
        else:
            logger.warning(
                "User creation form invalid",
                extra={"errors": form.errors, "submitted_by": getattr(request.user, "id", None)}
            )
    else:
        form = CustomUserCreationForm()

    return render(request, 'app/new_user.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    users = User.objects.all()
    logger.info(f"user_list_view accessed, total users: {users.count()}", extra={"user": getattr(request.user, "id", None)})
    return render(request, 'app/user_list.html', {'users': users})


class CalendarView(ListView):
    template_name = 'app/calendar.html'
    model = Appointment
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        personnel_user = getattr(self.request.user, "personnel_profile", None)
        if self.request.user.is_superuser:
            personnel_list = Personnel.objects.all()
        else:

            personnel_user = getattr(self.request.user, "personnel_profile", None)
            personnel_list = Personnel.objects.filter(id=personnel_user.personnel.id if personnel_user else None)
        customer_list = Customer.objects.all()
        work_list = Work.objects.all()
        appointments = Appointment.objects.select_related('customer', 'personnel', 'work').all()

        context.update({
            'personnel_list': personnel_list,
            'customer_list': customer_list,
            'work_list': work_list,
            'appointments': appointments,
        })

        logger.info(
            f"CalendarView context prepared, personnel: {personnel_list.count()}, customers: {customer_list.count()}, appointments: {appointments.count()}",
            extra={"user": getattr(self.request.user, "id", None)}
        )


            
        
        
        if personnel_user:
            # context['personnel_list'] = Personnel.objects.filter(id=personnel_user.personnel.id)
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
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from app.models import Appointment
from app.sms import customer_sms, personnel_sms, send_sms
from django.utils import timezone

logger = logging.getLogger(__name__)

@csrf_exempt
def create_appointment(request):
    logger.info("Accessed create_appointment view", extra={"user": getattr(request.user, "id", None)})
    if request.method == 'POST':
        try:
            data = request.POST

            customer_id = data.get('customer_id')
            work_id = data.get('work_id')
            personnel_id = data.get('personnel_id')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            if not all([customer_id, personnel_id, start_time_str, end_time_str]):
                logger.warning("Missing required fields", extra={"data": data, "user": getattr(request.user, "id", None)})
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفاً تمام فیلدهای ضروری را پر کنید'
                }, status=400)
            
            # تبدیل رشته‌ها به datetime
            try:
                start_time = gdatetime.fromisoformat(start_time_str)
                end_time = gdatetime.fromisoformat(end_time_str)
            except ValueError as e:
                logger.warning("Invalid date format", extra={"error": str(e), "data": data, "user": getattr(request.user, "id", None)})
                return JsonResponse({
                    'status': 'error',
                    'message': 'فرمت تاریخ نامعتبر است',
                    'error_details': str(e)
                }, status=400)

            # بررسی تداخل فقط برای همان پرسنل
            conflict = Appointment.objects.filter(
                personnel_id=personnel_id,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()

            if conflict:
                logger.warning("Appointment conflict detected", extra={"personnel_id": personnel_id, "start_time": start_time, "end_time": end_time, "user": getattr(request.user, "id", None)})
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
            logger.info("Appointment created successfully", extra={"appointment_id": appointment.id, "user": getattr(request.user, "id", None)})

            # ارسال پیامک به مشتری
            customer_mobile = appointment.customer.mobile
            customer_name = appointment.customer.fname
            customer_l_name = appointment.customer.lname
            customer_full_name = f"{customer_name} {customer_l_name}"
            work = appointment.work.work_name
            appointment_time = appointment.start_time
            personnel_name = appointment.personnel.fname

            customer_msg = customer_sms(customer_name, work, appointment_time)
            send_sms(customer_mobile, customer_msg)
            logger.info(f"SMS sent to customer {customer_id}", extra={"appointment_id": appointment.id})

            # ارسال پیامک به پرسنل
            personnel_mobile = appointment.personnel.mobile
            personnel_msg = personnel_sms(personnel_name, customer_full_name, appointment_time)
            send_sms(personnel_mobile, personnel_msg)
            logger.info(f"SMS sent to personnel {personnel_id}", extra={"appointment_id": appointment.id})

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'message': 'رزرو با موفقیت ثبت شد'
            }, status=201)

        except Exception as e:
            logger.error("Failed to create appointment", exc_info=True, extra={"user": getattr(request.user, "id", None)})
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    logger.warning("Invalid HTTP method", extra={"method": request.method, "user": getattr(request.user, "id", None)})
    return JsonResponse({
        'status': 'error',
        'message': 'متد غیرمجاز'
    }, status=405)

@login_required
def get_available_time_slots(request):
    personnel_id = request.GET.get('personnel_id')
    date = request.GET.get('date')
    logger.info("Accessed get_available_time_slots", extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id, "date": date})

    if not personnel_id or not date:
        logger.warning("Missing required parameters", extra={"user": getattr(request.user, "id", None)})
        return JsonResponse({'status': 'error', 'message': 'پارامترهای ضروری ارسال نشده'}, status=400)
    
    try:
        appointments = Appointment.objects.filter(
            personnel_id=personnel_id,
            start_time__date=date
        ).order_by('start_time')
        logger.info(f"Found {appointments.count()} appointments for personnel {personnel_id} on {date}", extra={"user": getattr(request.user, "id", None)})

        # اینجا منطق محاسبه زمان‌های خالی را پیاده‌سازی کنید
        slots = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00']
        
        return JsonResponse({'status': 'success', 'slots': slots})
    except Exception as e:
        logger.error("Failed to get available time slots", exc_info=True, extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id, "date": date})
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def appointment_list(request):
    personnel_id = request.GET.get('personnel_id')
    logger.info("Accessed appointment_list", extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id})

    if not personnel_id:
        logger.warning("Missing personnel_id parameter", extra={"user": getattr(request.user, "id", None)})
        return JsonResponse([], safe=False)

    try:
        appointments = Appointment.objects.filter(personnel_id=personnel_id)
        logger.info(f"Found {appointments.count()} appointments for personnel {personnel_id}", extra={"user": getattr(request.user, "id", None)})

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
        logger.error("Failed to fetch appointment list", exc_info=True, extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id})
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from app.models import Appointment

logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def update_appointment(request, pk):
    logger.info("Accessed update_appointment", extra={"user": getattr(request.user, "id", None), "appointment_id": pk})
    
    if request.method != 'POST':
        logger.warning("Invalid HTTP method", extra={"method": request.method, "user": getattr(request.user, "id", None)})
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'}, status=405)
    
    appointment = get_object_or_404(Appointment, pk=pk)
    
    try:
        data = request.POST
        required_fields = ['customer_id', 'personnel_id', 'start_time', 'end_time']
        if not all(field in data for field in required_fields):
            logger.warning("Missing required fields", extra={"user": getattr(request.user, "id", None), "data": data})
            return JsonResponse({'status': 'error', 'message': 'لطفاً تمام فیلدهای ضروری را پر کنید'}, status=400)

        # به‌روزرسانی فیلدها
        appointment.customer_id = data.get('customer_id')
        appointment.work_id = data.get('work_id')
        appointment.personnel_id = data.get('personnel_id')
        
        try:
            appointment.start_time = gdatetime.fromisoformat(data.get('start_time'))
            appointment.end_time = gdatetime.fromisoformat(data.get('end_time'))
        except ValueError as e:
            logger.warning("Invalid date format", extra={"user": getattr(request.user, "id", None), "error": str(e)})
            return JsonResponse({'status': 'error', 'message': 'فرمت تاریخ نامعتبر است'}, status=400)

        # بررسی تداخل
        conflict = Appointment.objects.filter(
            personnel_id=appointment.personnel_id,
            start_time__lt=appointment.end_time,
            end_time__gt=appointment.start_time,
        ).exclude(pk=appointment.pk).exists()

        if conflict:
            logger.warning("Appointment conflict detected", extra={"user": getattr(request.user, "id", None), "appointment_id": pk})
            return JsonResponse({'status': 'error', 'message': 'این بازه زمانی قبلاً برای این پرسنل رزرو شده است.'}, status=400)

        appointment.save()
        logger.info("Appointment updated successfully", extra={"user": getattr(request.user, "id", None), "appointment_id": pk})

        return JsonResponse({'status': 'success', 'message': 'رزرو با موفقیت ویرایش شد'})

    except Exception as e:
        logger.error("Failed to update appointment", exc_info=True, extra={"user": getattr(request.user, "id", None), "appointment_id": pk})
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@csrf_exempt
def delete_appointment(request, pk):
    logger.info("Accessed delete_appointment", extra={"user": getattr(request.user, "id", None), "appointment_id": pk})

    if request.method != 'POST':
        logger.warning("Invalid HTTP method", extra={"method": request.method, "user": getattr(request.user, "id", None)})
        return JsonResponse({'status': 'error', 'message': 'متد غیرمجاز'}, status=405)

    appointment = get_object_or_404(Appointment, pk=pk)

    try:
        appointment.delete()
        logger.info("Appointment deleted successfully", extra={"user": getattr(request.user, "id", None), "appointment_id": pk})
        return JsonResponse({'status': 'success', 'message': 'رزرو با موفقیت حذف شد'})
    except Exception as e:
        logger.error("Failed to delete appointment", exc_info=True, extra={"user": getattr(request.user, "id", None), "appointment_id": pk})
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def personnel_works(request):
    personnel_id = request.GET.get('personnel_id')
    logger.info("Accessed personnel_works", extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id})

    if not personnel_id:
        logger.warning("Missing personnel_id parameter", extra={"user": getattr(request.user, "id", None)})
        return JsonResponse([], safe=False)

    try:
        commissions = PersonnelCommission.objects.filter(
            personnel_id=personnel_id
        ).select_related('work')

        data = [{"id": c.work.id, "work_name": c.work.work_name} for c in commissions]
        logger.info(f"Returned {len(data)} works for personnel {personnel_id}", extra={"user": getattr(request.user, "id", None)})

        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error("Failed to fetch personnel works", exc_info=True, extra={"user": getattr(request.user, "id", None), "personnel_id": personnel_id})
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from app.models import SaleImage, Customer, Personnel, PersonnelUser

logger = logging.getLogger(__name__)

@login_required
def gallery_view(request):
    logger.info("Accessed gallery_view", extra={"user": getattr(request.user, "id", None)})

    images = SaleImage.objects.all()

    # فیلتر بر اساس پرسنل اگر کاربر ادمین نیست
    if not request.user.is_superuser:
        try:
            personnel_user = PersonnelUser.objects.get(user=request.user)
            personnel = personnel_user.personnel
            images = images.filter(sale__personnel=personnel)
            logger.info(f"Filtered images for personnel {personnel.id}", extra={"user": getattr(request.user, "id", None)})
        except PersonnelUser.DoesNotExist:
            images = SaleImage.objects.none()
            logger.warning("PersonnelUser does not exist for user", extra={"user": getattr(request.user, "id", None)})

    # فیلتر بر اساس مشتری
    customer_filter = request.GET.get('customer')
    if customer_filter:
        images = images.filter(sale__customer__id=customer_filter)
        logger.info(f"Filtered images by customer {customer_filter}", extra={"user": getattr(request.user, "id", None)})

    # فیلتر بر اساس پرسنل (برای ادمین)
    personnel_filter = request.GET.get('personnel')
    print(personnel_filter)
    
    if personnel_filter and request.user.is_superuser:
        images = images.filter(sale__personnel__id=personnel_filter)

        logger.info(f"Filtered images by personnel {personnel_filter}", extra={"user": getattr(request.user, "id", None)})

    # فقط عکس‌های "بعد"
        personnel_filter = Personnel.objects.filter(id=personnel_filter).first()
    else:
    # اگر انتخابی نبود، اولین پرسنل موجود رو بیاور
        personnel_filter = Personnel.objects.first()
    


    # در نهایت فقط عکس‌های "بعد"
    images = images.filter(image_type=SaleImage.AFTER)

    # دریافت لیست مشتریان و پرسنل برای فیلترها
    customers = Customer.objects.all()
    personnel_list = Personnel.objects.all() if request.user.is_superuser else []

    logger.info(f"Returning {images.count()} images", extra={"user": getattr(request.user, "id", None)})

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

        logger.info("Accessing HomeDashboardView", extra={"user_id": user.id, "is_superuser": is_super})

        personnel = None
        if not is_super:
            try:
                personnel = user.personnel_profile.personnel
                logger.info(f"Personnel user detected: {personnel.id}", extra={"user_id": user.id})
            except Exception:
                personnel = None
                logger.warning("No personnel profile found for non-superuser", extra={"user_id": user.id})

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
        logger.info(f"Prepared balances_chart with {len(balances_chart)} series", extra={"user_id": user.id})

        # ===== 2. فروش روزانه =====
        sales = Sale.objects.all()
        if not is_super and personnel:
            sales = sales.filter(personnel=personnel)

        min_date = sales.aggregate(min_date=Min('date'))['min_date']
        max_date = sales.aggregate(max_date=Max('date'))['max_date']

        daily_sales = []
        if min_date and max_date:
            current = min_date.date()
            last = max_date.date()
            while current <= last:
                start = gdatetime.combine(current, gdatetime.min.time())
                end = start + timedelta(days=1)
                day_sales = sales.filter(date__gte=start, date__lt=end).aggregate(
                    commission=Sum('commission_amount'),
                    total=Sum('price')
                )
                daily_sales.append({
                    'day': current,
                    'commission': day_sales['commission'] or 0,
                    'total': day_sales['total'] or 0
                })
                current += timedelta(days=1)
                


        sales_chart = []
        for row in daily_sales:
            day_str = str(row["day"])

            day_date = gdatetime.strptime(day_str, "%Y-%m-%d").date()
            
            sales_chart.append({
                "date": jdatetime.date.fromgregorian(date=day_date).strftime("%Y-%m-%d"),
                "commission": int(row["commission"]) or 0,
                "remainder": ((int(row["total"]) or 0) - (int(row["commission"]) or 0)) if is_super else 0
            })
        context["sales_chart"] = sales_chart
        logger.info(f"Prepared sales_chart with {len(sales_chart)} points", extra={"user_id": user.id})

        # ===== 3. رزروها =====
        appointments = Appointment.objects.all()
        if not is_super and personnel:
            appointments = appointments.filter(personnel=personnel)

        daily_appts = (
            appointments
            .annotate(day=Cast("start_time", output_field=DateField()))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        print(daily_appts.__len__)
        appt_chart = []
        for row in daily_appts:
            day_date = gdatetime.strptime(day_str, "%Y-%m-%d").date()
            print (day_date)
            appt_chart.append({
                "date": jdatetime.date.fromgregorian(date=day_date).strftime("%Y-%m-%d"),
                "count": row["count"]
            })
        context["appt_chart"] = appt_chart
        logger.info(f"Prepared appt_chart with {len(appt_chart)} points", extra={"user_id": user.id})

        # ===== 4. تعداد فاکتورها =====
        sales_count = (
            sales.annotate(day=Cast("date", output_field=DateField()))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day"))
 
        sales_count_chart = []
        for row in sales_count:
            day_str = str(row["day"])
            day_date = gdatetime.strptime(day_str, "%Y-%m-%d").date()
            sales_count_chart.append({
                "date": jdatetime.date.fromgregorian(date=day_date).strftime("%Y-%m-%d"),
                "count": row["count"]
            })
        context["sales_count_chart"] = sales_count_chart
        logger.info(f"Prepared sales_count_chart with {len(sales_count_chart)} points", extra={"user_id": user.id})

        context["is_super"] = is_super
        return context


class PayUpdateView(UpdateView):
    template_name = "app/edit_pay.html"
    form_class = PayForm
    model = Pay
    success_url = reverse_lazy("pay_list")

    def form_valid(self, form):
        pay = form.save()
        # لاگ عملیات موفق
        logger.info(f"Pay updated: {pay.id}", extra={"user_id": self.request.user.id})

        # اگر درخواست Ajax بود، خروجی JSON بده
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "id": pay.id,
                "date": jdatetime.date.fromgregorian(date=pay.date).strftime("%Y-%m-%d") if pay.date else "",
                "pay_type": pay.pay_type.name if pay.pay_type else "",
                "personnel": f"{pay.personnel.fname} {pay.personnel.lname}" if pay.personnel else "",
                "amount": f"{pay.amount:,}",
                "source_type": pay.source_type.name if pay.source_type else "",
                "bank": pay.bank.name if pay.bank else "",
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        # لاگ عملیات ناموفق
        logger.warning("Pay update failed", extra={"user_id": self.request.user.id, "errors": form.errors})

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """قبل از اعتبارسنجی فرم، تاریخ و اعداد فارسی را تبدیل می‌کنیم"""
        data = request.POST.copy()
        date_val = data.get("date")
        if date_val:
            try:
                date_val = persian_to_english(date_val)  # تبدیل اعداد فارسی به انگلیسی
                parts = list(map(int, date_val.split("/")))
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data["date"] = date_val
            except Exception as e:
                logger.error("Error parsing date in PayUpdateView", exc_info=e)
        request.POST = data
        return super().post(request, *args, **kwargs)


logger = logging.getLogger(__name__)

class ReceiptUpdateView(UpdateView):
    template_name = "app/edit_receipt.html"
    form_class = ReceiptForm
    model = Receipt
    success_url = reverse_lazy("Receipt_list")

    def form_valid(self, form):
        receipt = form.save()
        # لاگ عملیات موفق
        logger.info(f"Receipt updated: {receipt.id}", extra={"user_id": self.request.user.id})

        # اگر درخواست Ajax بود، خروجی JSON بده
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "id": receipt.id,
                "date": jdatetime.date.fromgregorian(date=receipt.date).strftime("%Y-%m-%d") if receipt.date else "",
                "receipt_type": receipt.receipt_type.name if receipt.receipt_type else "",
                "customer": f"{receipt.customer.name}" if receipt.customer else "",
                "amount": f"{receipt.amount:,}",
                "source_type": receipt.source_type.name if receipt.source_type else "",
                "bank": receipt.bank.name if receipt.bank else "",
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        # لاگ عملیات ناموفق
        logger.warning("Receipt update failed", extra={"user_id": self.request.user.id, "errors": form.errors})

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """قبل از اعتبارسنجی فرم، تاریخ و اعداد فارسی را تبدیل می‌کنیم"""
        data = request.POST.copy()
        date_val = data.get("date")
        if date_val:
            try:
                date_val = persian_to_english(date_val)  # تبدیل اعداد فارسی به انگلیسی
                parts = list(map(int, date_val.split("/")))
                date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
                data["date"] = date_val
            except Exception as e:
                logger.error("Error parsing date in ReceiptUpdateView", exc_info=e)
        request.POST = data
        return super().post(request, *args, **kwargs)

@login_required
def sale_images_view(request, sale_id):
    try:
        sale = get_object_or_404(Sale, id=sale_id)

        # فیلتر تصاویر بر اساس دسترسی کاربر
        images = sale.images.all()
        if not request.user.is_superuser:
            try:
                personnel_user = request.user.personnel_profile
                if sale.personnel != personnel_user.personnel:
                    images = images.none()
            except Exception:
                images = images.none()

        context = {
            'sale': sale,
            'images': images
        }

        logger.info(f"User {request.user.id} viewed images for Sale {sale.id}")
        return render(request, 'app/sale_images.html', context)

    except Exception as e:
        logger.error(f"Error in sale_images_view: {e}", exc_info=True)
        return render(request, 'app/sale_images.html', {'sale': None, 'images': []})


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

    def get_queryset(self):
        qs = super().get_queryset()
        logger.info(f"User {self.request.user.id} accessed Personnel list. Count: {qs.count()}")
        return qs

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelCreateView(CreateView):
    model = Personnel
    fields = ["fname", "lname", "mobile", "comment", "on_site", "is_active"]
    template_name = "app/personnel_form.html"
    success_url = reverse_lazy("personnel_list")

    def form_valid(self, form):
        personnel = form.save()
        logger.info(f"Personnel {personnel.id} created by user {self.request.user.id}")
        # پشتیبانی از Ajax
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "id": personnel.id,
                "fname": personnel.fname,
                "lname": personnel.lname,
                "mobile": personnel.mobile,
                "on_site": personnel.on_site,
                "is_active": personnel.is_active
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(f"Failed attempt to create Personnel by user {self.request.user.id}: {form.errors}")
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)
        return super().form_invalid(form)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelUpdateView(UpdateView):
    model = Personnel
    fields = ["fname", "lname", "mobile", "comment", "on_site", "is_active"]
    template_name = "app/personnel_form.html"
    success_url = reverse_lazy("personnel_list")

    def form_valid(self, form):
        personnel = form.save()
        logger.info(f"Personnel {personnel.id} updated by user {self.request.user.id}")
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "id": personnel.id,
                "fname": personnel.fname,
                "lname": personnel.lname,
                "mobile": personnel.mobile,
                "on_site": personnel.on_site,
                "is_active": personnel.is_active
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(f"Failed attempt to update Personnel by user {self.request.user.id}: {form.errors}")
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            }, status=400)
        return super().form_invalid(form)



@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelDeleteView(DeleteView):
    model = Personnel
    template_name = "app/personnel_confirm_delete.html"
    success_url = reverse_lazy("personnel_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        personnel_id = self.object.id
        try:
            response = super().delete(request, *args, **kwargs)
            logger.info(f"Personnel {personnel_id} deleted by user {request.user.id}")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True, "id": personnel_id})
            return response
        except Exception as e:
            logger.error(f"Error deleting Personnel {personnel_id} by user {request.user.id}: {e}")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            raise


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class WorkListView(ListView):
    model = Work
    template_name = "settings/work_list.html"
    context_object_name = "works"

    def get_queryset(self):
        try:
            qs = super().get_queryset()
            logger.info(f"Work list accessed by user {self.request.user.id}")
            return qs
        except Exception as e:
            logger.error(f"Error fetching Work list for user {self.request.user.id}: {e}")
            return Work.objects.none()

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class WorkCreateView(CreateView):
    model = Work
    fields = ["work_name"]
    template_name = "settings/work_form.html"
    success_url = reverse_lazy("works")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            logger.info(f"Work '{self.object.work_name}' created by user {self.request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error creating Work by user {self.request.user.id}: {e}")
            form.add_error(None, "خطا در ذخیره اطلاعات")
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class WorkUpdateView(UpdateView):
    model = Work
    fields = ["work_name"]
    template_name = "settings/work_form.html"
    success_url = reverse_lazy("works")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            logger.info(f"Work '{self.object.work_name}' updated by user {self.request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error updating Work '{self.object.id}' by user {self.request.user.id}: {e}")
            form.add_error(None, "خطا در به‌روزرسانی اطلاعات")
            return self.form_invalid(form)
@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class WorkDeleteView(DeleteView):
    model = Work
    template_name = "settings/work_confirm_delete.html"
    success_url = reverse_lazy("works")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            work_name = self.object.work_name
            response = super().delete(request, *args, **kwargs)
            logger.info(f"Work '{work_name}' deleted by user {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error deleting Work '{self.object.id}' by user {request.user.id}: {e}")
            return self.render_to_response(self.get_context_data(
                error="خطا در حذف رکورد"
            ))


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelCommissionListView(ListView):
    model = PersonnelCommission
    template_name = "settings/commission_list.html"
    context_object_name = "commissions"

    def get_queryset(self):
        try:
            show_history = self.request.GET.get("history") == "1"

            if show_history:
                qs = PersonnelCommission.objects.all().order_by("-start_date")
                logger.info(f"User {self.request.user.id} requested full commission history")
                return qs

            # فقط آخرین رکورد برای هر پرسنل و خدمت
            latest_ids = (
                PersonnelCommission.objects
                .values("personnel_id", "work_id")
                .annotate(max_id=Max("id"))
                .values_list("max_id", flat=True)
            )
            qs = PersonnelCommission.objects.filter(id__in=latest_ids).order_by("personnel__lname", "work__work_name")
            logger.info(f"User {self.request.user.id} requested latest commissions only")
            return qs

        except Exception as e:
            logger.error(f"Error fetching PersonnelCommission list for user {self.request.user.id}: {e}")
            return PersonnelCommission.objects.none()


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelCommissionCreateView(CreateView):
    model = PersonnelCommission
    fields = ["personnel", "work", "percentage", "start_date", "end_date"]
    template_name = "settings/commission_form.html"
    success_url = reverse_lazy("commissions")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            logger.info(f"User {self.request.user.id} created commission {self.object.id}")
            return response
        except Exception as e:
            logger.error(f"Error creating commission by user {self.request.user.id}: {e}")
            form.add_error(None, "خطایی در ایجاد کمیسیون رخ داد.")
            return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelCommissionUpdateView(UpdateView):
    model = PersonnelCommission
    fields = ["personnel", "work", "percentage", "start_date", "end_date"]
    template_name = "settings/commission_form.html"
    success_url = reverse_lazy("commissions")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            logger.info(f"User {self.request.user.id} updated commission {self.object.id}")
            return response
        except Exception as e:
            logger.error(f"Error updating commission {self.object.id} by user {self.request.user.id}: {e}")
            form.add_error(None, "خطایی در بروزرسانی کمیسیون رخ داد.")
            return self.form_invalid(form)



@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class PersonnelCommissionDeleteView(DeleteView):
    model = PersonnelCommission
    template_name = "settings/commission_confirm_delete.html"
    success_url = reverse_lazy("commissions")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            logger.info(f"User {request.user.id} is deleting commission {self.object.id}")
            response = super().delete(request, *args, **kwargs)
            logger.info(f"Commission {self.object.id} deleted successfully")
            return response
        except Exception as e:
            logger.error(f"Error deleting commission {self.object.id} by user {request.user.id}: {e}")
            from django.http import HttpResponseServerError
            return HttpResponseServerError("خطایی در حذف کمیسیون رخ داد.")
        
class CustomerListView(ListView):
    template_name = "app/customer_list.html"
    model = Customer
    context_object_name = "customers"

    def get_queryset(self):
        filter_value = self.request.GET.get("filter")
        queryset = super().get_queryset()

        if filter_value:
            queryset = queryset.filter(
                Q(name__search=filter_value) | Q(mobile__search=filter_value)
            )
            logger.info(f"Customer search applied: filter='{filter_value}', results={queryset.count()}")
        else:
            logger.info("Customer list viewed without filter")

        return queryset
    

def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")  # پسورد جدید
        
        # به‌روزرسانی اطلاعات
        user.username = username
        user.email = email
        
        if password:
            user.set_password(password)  # هش کردن پسورد
        user.save()
        
        messages.success(request, "کاربر با موفقیت ویرایش شد.")
        return redirect('users')
    
    return render(request, "accounts/edit_user.html", {"user": user})

def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        user.delete()
        messages.success(request, "کاربر با موفقیت حذف شد.")
        return redirect('users_list')
    
    return render(request, "accounts/delete_user_confirm.html", {"user": user})