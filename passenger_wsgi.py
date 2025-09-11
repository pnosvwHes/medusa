import sys
import os

# مسیر پروژه (جایی که manage.py هست)
sys.path.insert(0, '/home/medusabeautyir/repositories/medusa')

# فعال کردن virtualenv
activate_this = '/home/medusabeautyir/virtualenv/medusa_app/3.12/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# تنظیمات Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medusa.settings')

# ایمپورت و آماده‌سازی WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

