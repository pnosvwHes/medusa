from datetime import timezone
from django.db import migrations

def create_superuser(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='masoud').exists():
        User.objects.create_superuser(
            username='masoud',
            email='masoud.hesaraki1985@gmail.com',
            password='1234',
            last_login=timezone.now()  # ← اضافه شده
        )

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),  # مایگرِیشن قبلی
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]
