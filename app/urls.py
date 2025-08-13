from django.urls import path
from app.views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", SaleListView.as_view(), name="home"),
    path("sale/new/", SaleCreateView.as_view(), name="create_sale"),
    path("sale/<int:pk>/update", SaleUpdateView.as_view(), name="update_sale"),
    path("sale/<int:pk>/delete", SaleDeleteView.as_view(), name="delete_sale"),
    path("customers", CustomerListView.as_view(), name="customers"),
    path("customer/new/", CustomerCreateView.as_view(), name="new_customer"),
    path("customer/<int:pk>/update", CustomerUpdateView.as_view(), name="update_customer"),
    path("customer/<int:pk>/delete", CustomerDeleteView.as_view(), name="delete_customer"),
    path("sale/save-payments/", save_payments, name="save_payments"),
    path("sale/payment-data/", get_payment_data, name="get_payment_data"),
    path("transactions/new/", TransactionCreateView.as_view(), name="create_transaction"),
    path("ledger-report/", LedgerReportView.as_view(), name="ledger_report"),
    path('users/', user_list_view, name='users'),
    path('create-user/', create_user_view, name='create_user'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),
    path('booking', CalendarView.as_view(), name='booking_calendar'),
    path('booking/create/', create_appointment, name='create_appointment'),
    path('booking/get_slots/', get_available_time_slots, name='get_time_slots'),
    path('booking/appointments/', appointment_list, name='appointment_list'),
    path('booking/update/<int:pk>/', update_appointment, name='update_appointment'),
    path('booking/delete/<int:pk>/', delete_appointment, name='delete_appointment'),
]