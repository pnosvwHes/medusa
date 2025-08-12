from django.urls import path
from app.views import *

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
]