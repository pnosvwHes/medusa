from datetime import date
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import jdatetime

def is_admin(user):
    if user.is_superuser:
        return True
    if hasattr(user, 'personnel_profile'):
        return user.personnel_profile.is_admin
    return False



MAX_SIZE = (1024, 1024)
JPEG_QUALITY = 75

def compress_image(file):
    image = Image.open(file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return ContentFile(buffer.getvalue(), name=file.name.split('.')[0] + ".jpg")

def gregorian_to_jalali_parts(gdatetime):
    jalali_dt = jdatetime.datetime.fromgregorian(datetime=gdatetime)
    weekday_map = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنجشنبه",
        "Friday": "جمعه",
    }

    weekday_name = weekday_map[jalali_dt.strftime("%A")]
    jalali_date = jalali_dt.strftime("%Y-%m-%d")
    jalali_time = jalali_dt.strftime("%H:%M")

    return jalali_date, jalali_time, weekday_name


# utils.py

def persian_to_english(s: str) -> str:
    """
    تبدیل اعداد فارسی به انگلیسی
    مثال: "۱۴۰۴/۰۶/۰۵" → "1404/06/05"
    """
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    return str(s).translate(str.maketrans(persian_digits, english_digits))


def english_to_persian(s: str) -> str:

    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    return str(s).translate(str.maketrans(english_digits, persian_digits))


def jalali_to_gregorian(jalali_str: str) -> date:
    
    jalali_str = persian_to_english(jalali_str)
    parts = list(map(int, jalali_str.split("-")))
    date_val = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
    
    return date_val