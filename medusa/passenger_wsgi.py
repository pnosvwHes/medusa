import sys, os

# مسیر پروژه‌ات (اصلاح کن بر اساس مسیر واقعی روی هاست)
project_home = '/home/medusabeautyir/repositories/medusa'

if project_home not in sys.path:
    sys.path.append(project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'medusa.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
