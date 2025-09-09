import sys, os

# مسیر پروژه
sys.path.insert(0, "/home/medusabeautyir/medusa_app")

# مسیر virtualenv
activate_this = '/home/medusabeautyir/virtualenv/repositories/medusa/3.12/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), dict(__file__=activate_this))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medusa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
