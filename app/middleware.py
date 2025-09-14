from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse, NoReverseMatch
# app/middleware.py

import logging
import traceback

logger = logging.getLogger("app")  # همون logger که تو settings تعریف کردی

class LogErrorsMiddleware:
    """
    Middleware برای لاگ کردن خطاهای 500 و Exception های غیرمنتظره.
    فقط خطاها رو ثبت میکنه، info/debug ثبت نمیشه.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # لاگ کردن خطا با traceback کامل
            logger.error("💥 Exception رخ داده: %s\n%s", e, traceback.format_exc())
            raise  # دوباره پرتاب میکنه تا Django همچنان 500 بده

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # مسیرهای آزاد
        allowed_urls = [settings.LOGIN_URL]
        # تلاش می‌کنیم URL های نام‌گذاری شده رو اضافه کنیم، اگر وجود نداشتن خطا رو نادیده می‌گیریم
        for name in ['booking_calendar', 'appointment_list']:
            try:
                allowed_urls.append(reverse(name))
            except NoReverseMatch:
                pass  # اگر URL وجود نداشت، نادیده گرفته می‌شود

        # اگر کاربر لاگین نکرده و مسیرش آزاد نیست
        if not request.user.is_authenticated and request.path not in allowed_urls:
            return redirect(settings.LOGIN_URL)

        return self.get_response(request)
