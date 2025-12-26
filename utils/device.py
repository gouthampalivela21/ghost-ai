# utils/device.py

def device_icon(agent: str):
    a = agent.lower()

    if "iphone" in a or "android" in a or "ipad" in a:
        return "📱"
    if "macintosh" in a or "windows" in a or "linux" in a:
        return "💻"
    return "🌐"


def browser_name(agent: str):
    a = agent.lower()

    if "edg" in a:
        return "Edge"
    if "chrome" in a and "safari" in a:
        return "Chrome"
    if "safari" in a and "chrome" not in a:
        return "Safari"
    if "firefox" in a:
        return "Firefox"

    return "Unknown"