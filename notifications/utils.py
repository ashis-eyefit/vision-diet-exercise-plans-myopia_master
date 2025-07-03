def send_push_notification(device_token, message):
    # Replace with actual FCM / OneSignal / Firebase logic
    print(f"Push to {device_token}: {message}")

def send_email(to_email, subject, content):
    # Optional: use SendGrid, SMTP etc.
    print(f"Email to {to_email}: {subject} - {content}")
def send_notification(user_id, message, channel):
    # Placeholder
    print(f"[NOTIFY-{channel.upper()}] User: {user_id} → {message}")
    return f"[NOTIFY-{channel.upper()}] Hi, {user_id} → {message}"
    
