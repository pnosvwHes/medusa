from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # مسیرهایی که باید بدون لاگین قابل دسترس باشن
        allowed_urls = [
            reverse('login'), 
            reverse('booking_calendar'),      
            reverse('appointment_list')
        ]
        
        # اگر درخواست کاربر لاگین نکرده و مسیرش جزو صفحات آزاد نیست
        if not request.user.is_authenticated and request.path not in allowed_urls:
            return redirect(settings.LOGIN_URL)

        return self.get_response(request)
