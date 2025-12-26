# utils/location.py
import requests

def detect_location(ip: str):
    try:
        if ip.startswith("127.") or ip == "0.0.0.0":
            return "Localhost"

        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3).json()
        city = res.get("city")
        country = res.get("country_name")

        if city and country:
            return f"{city}, {country}"
        if country:
            return country

        return "Unknown location"
    except Exception:
        return "Unknown location"