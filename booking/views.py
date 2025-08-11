from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from .models import Appointment
from app.models import Customer, Personnel, Work
from django.http import JsonResponse
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json

class CalendarView(ListView):
    template_name = 'booking/calendar.html'
    model = Appointment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['personnel_list'] = Personnel.objects.all()
        context['customer_list'] = Customer.objects.all()
        context['work_list'] = Work.objects.all()
        context['appointments'] = Appointment.objects.select_related('customer', 'personnel', 'work').all()
        return context


def create_appointment(request):
    if request.method == 'POST':
        try:
            data = request.POST

            customer_id = data.get('customer_id')
            work_id = data.get('work_id')
            personnel_id = data.get('personnel_id')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            # تبدیل رشته‌ها به datetime
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)

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

        except KeyError as e:
            return JsonResponse({
                'status': 'error',
                'message': f'فیلد ضروری {str(e)} وجود ندارد'
            }, status=400)

        except Exception as e:
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
    
    # محاسبه زمان‌های آزاد بر اساس رزروهای موجود
    # (پیاده‌سازی منطق اختصاصی شما)
    return JsonResponse({'slots': ['09:00', '11:00', '14:00']})



def appointment_list(request):
    personnel_id = request.GET.get('personnel_id')
    if not personnel_id:
        return JsonResponse([], safe=False)

    bookings = Appointment.objects.filter(personnel_id=personnel_id)
    data = []
    for b in bookings:
        data.append({
            'id': b.id,
            'title': f"{b.customer.name} - {b.work.work_name}",
            'start': b.start_time.isoformat(),
            'end': b.end_time.isoformat(),
            'customerId': b.customer.id,
            'customerName': b.customer.name,
            'workId': b.work.id,
            'workName': b.work.work_name,
            'personnelId': b.personnel.id,
            'personnelName': f"{b.personnel.fname} {b.personnel.lname}",
            'isPaid': b.is_paid,
        })
    return JsonResponse(data, safe=False)



@csrf_exempt
def update_appointment(request, pk):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            data = request.POST
            # به‌روزرسانی فیلدها
            appointment.customer_id = data.get('customer_id')
            appointment.work_id = data.get('work_id')
            appointment.personnel_id = data.get('personnel_id')
            appointment.start_time = data.get('start_time')
            appointment.end_time = data.get('end_time')
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