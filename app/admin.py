from django.contrib import admin
from app.models import Personnel,Customer,Sale,Work,PaymentMethod,Bank,TransactionType,Transaction,Payment,PersonnelUser,PersonnelCommission
# Register your models here.

admin.site.register(Personnel)
admin.site.register(Customer)
admin.site.register(Sale)
admin.site.register(Work)
admin.site.register(PaymentMethod)
admin.site.register(Bank)
admin.site.register(Transaction)
admin.site.register(TransactionType)
admin.site.register(Payment)
admin.site.register(PersonnelUser)
admin.site.register(PersonnelCommission)