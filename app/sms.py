import requests
from decouple import config
from app.utils import gregorian_to_jalali_parts
API_TOKEN = config("IPPANEL_API_KEY")
BASE_URL = "https://edge.ippanel.com/v1"

def send_sms(recipients, message):
    print(message)
    from_number = '+9890000145'
    url = f"{BASE_URL}/api/send"
    headers = {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json"
    }
    body = {
        "sending_type": "webservice",
        "from_number": from_number,
        "message": message,
        "params": {"recipients": recipients if isinstance(recipients, list) else [recipients]}
    }
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)

        print("🔹 Status Code:", response.status_code)
        print("🔹 Raw Response:", response.text)

        try:
            return response.json()
        except Exception:
            return {"status_code": response.status_code, "text": response.text}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}
    

def customer_sms(customer_name,work, time):
    jdate, jtime, weekday = gregorian_to_jalali_parts(time)
    return(
    f"{customer_name} عزیز\n"
    f"رزرو {work} شما برای روز {weekday}  در تاریخ {jdate} و ساعت {jtime} ثبت شد \n"
    f"سالن زیبایی مدوسا")

def personnel_sms(personnel_name, customer_name, time):
    jdate, jtime, weekday = gregorian_to_jalali_parts(time)
    return(
    f"{personnel_name} عزیز\n"
    f"یک رزرو جدید برای شما در روز {weekday} ثبت شد\n"
    f"برای {customer_name} در تاریخ {jdate} و در ساعت {jtime} \n" 
    f"سالن زیبایی مدوسا")
    
    