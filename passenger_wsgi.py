import os
import sys

# مسیر پروژه‌ات رو به sys.path اضافه کن
sys.path.insert(0, os.path.dirname(__file__))

# ست کردن متغیرهای محیطی Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medusa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
