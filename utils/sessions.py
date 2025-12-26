# utils/sessions.py
from datetime import datetime
from utils.device import device_icon, browser_name
from utils.location import detect_location
from utils.email import send_new_device_alert
from datetime import datetime

from firebase_admin import firestore
def get_db():
    return firestore.client()
def register_session(user_id, request):
    db = get_db()
    db.collection("sessions").add({
        "user_id": user_id,
        "agent": request.headers.get("User-Agent"),
        "ip": request.remote_addr,
        "created": datetime.utcnow(),
        "active": True
    })

def register_session(user_email, request):
    agent = request.headers.get("User-Agent", "")
    ip = request.remote_addr or "0.0.0.0"

    device = device_icon(agent)
    browser = browser_name(agent)
    location = detect_location(ip)

    # 🔍 check if device already known
    known = db.sessions.find_one({
        "user_id": user_email,
        "device": device,
        "browser": browser
    })

    if not known:
        send_new_device_alert(
            user_email,
            device=device,
            browser=browser,
            location=location
        )

    db.sessions.insert_one({
        "user_id": user_email,
        "agent": agent,
        "device": device,
        "browser": browser,
        "location": location,
        "ip": ip,
        "created": datetime.utcnow(),
        "active": True
    })

def register_session(db, user_id, request):
    agent = request.headers.get("User-Agent", "")
    ip = request.remote_addr or "0.0.0.0"

    db.collection("sessions").add({
        "user_id": user_id,
        "agent": agent,
        "ip": ip,
        "created": datetime.utcnow(),
        "active": True
    })