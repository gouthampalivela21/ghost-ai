def send_security_alert(user_email, info: dict):
    """
    Send email / notification on new login
    """
    # Replace with your email / notification logic
    print("🚨 SECURITY ALERT")
    print(f"To: {user_email}")
    print(f"Device: {info['device']}")
    print(f"Browser: {info['browser']}")
    print(f"Location: {info['location']}")