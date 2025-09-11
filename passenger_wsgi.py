import sys
import os

# مسیر پروژه (جایی که فولدر medusa هست)
project_home = '/home/medusabeautyir/medusa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# فعال کردن virtualenv
activate_this = '/home/medusabeautyir/virtualenv/medusa/3.12/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# تنظیم متغیر محیطی برای Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medusa.settings')

# استفاده مستقیم از WSGI اصلی پروژه Django
from medusa.wsgi import application
