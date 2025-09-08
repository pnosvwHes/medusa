import sys, os, traceback

# مسیر فایل لاگ startup
log_path = '/home/medusabeautyir/repositories/medusa/logs/passenger_startup.log'
os.makedirs(os.path.dirname(log_path), exist_ok=True)

def log_startup_error(exc):
    with open(log_path, 'a') as f:
        f.write('==== Passenger startup error ====\n')
        f.write(traceback.format_exc())
        f.write('\n\n')

try:
    # مسیر پروژه
    project_home = '/home/medusabeautyir/repositories/medusa'
    if project_home not in sys.path:
        sys.path.insert(0, project_home)

    # محیط مجازی
    venv_path = '/home/medusabeautyir/virtualenv/repositories/medusa/3.12'
    activate_this = os.path.join(venv_path, 'bin/activate_this.py')
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

    # تنظیمات Django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'medusa.settings'

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

except Exception:
    log_startup_error(sys.exc_info())
    raise
