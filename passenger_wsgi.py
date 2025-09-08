import sys, os, traceback

# مسیر پروژه
project_home = '/home/medusabeautyir/repositories/medusa'
if project_home not in sys.path:
    sys.path.append(project_home)

# مسیر محیط مجازی
venv_path = '/home/medusabeautyir/virtualenv/repositories/medusa/3.12'
activate_this = os.path.join(venv_path, 'bin/activate_this.py')
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# تنظیمات Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'medusa.settings'

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    with open("/home/medusabeautyir/repositories/medusa/logs/passenger_startup.log", "w") as f:
        f.write(str(e))
    raisee