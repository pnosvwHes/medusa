import os, sys

sys.path.insert(0, "/home/medusabeautyir/repositories/medusa")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medusa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
