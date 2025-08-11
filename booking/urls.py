from django.urls import path
from .views import (
    CalendarView,
    create_appointment,
    get_available_time_slots,
    appointment_list,      # برای گرفتن لیست رزروها با فیلتر
    update_appointment,    # ویرایش رزرو
    delete_appointment     # حذف رزرو
)
app_name = 'booking'

urlpatterns = [
    path('', CalendarView.as_view(), name='booking_calendar'),
    path('create/', create_appointment, name='create_appointment'),
    path('get_slots/', get_available_time_slots, name='get_time_slots'),
    path('appointments/', appointment_list, name='appointment_list'),
    path('update/<int:pk>/', update_appointment, name='update_appointment'),
    path('delete/<int:pk>/', delete_appointment, name='delete_appointment'),
]
