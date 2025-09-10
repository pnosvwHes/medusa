import sys
import os

# 1. مسیر پروژه (جایی که manage.py هست)
sys.path.insert(0, '/home/medusabeautyir/medusa_app')

# 2. فعال کردن virtualenv
activate_this = '/home/medusabeautyir/virtualenv/medusa_app/3.12/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# 3. ست کردن تنظیمات Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'medusa.settings'

# 4. ایمپورت و آماده‌سازی WSGI
from medusa.wsgi import application
