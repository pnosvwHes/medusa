import os
import sys

# مسیر پروژه (فولدری که manage.py هست)
sys.path.insert(0, os.path.dirname(__file__))

# تنظیمات Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medusa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
