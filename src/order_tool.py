import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def send_order_email(customer_name: str, phone: str, address: str, items: str, notes: str = ""):
    """
    Send order details to restaurant email.
    Returns confirmation message.
    """
    try:
        # Email config from .env
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        restaurant_email = os.getenv("RESTAURANT_EMAIL")
        
        if not all([sender_email, sender_password, restaurant_email]):
            return "Error: Email not configured. Set SENDER_EMAIL, SENDER_PASSWORD, RESTAURANT_EMAIL in .env file."
        
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create email
        msg = MIMEMultipart()
        msg['Subject'] = f"New Order #{order_id} - {customer_name}"
        msg['From'] = sender_email
        msg['To'] = restaurant_email
        
        body = f"""
NEW ORDER RECEIVED

Order ID: {order_id}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

CUSTOMER:
Full Name: {customer_name}
Phone: {phone}
Address: {address}

ITEMS:
{items}

NOTES:
{notes if notes else "None"}

---
Sent from Restaurant AI
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return f"""
✅ ORDER SENT!

Order ID: {order_id}
Restaurant will contact you at {phone} to confirm.

Items:
{items}
"""
        
    except Exception as e:
        return f"❌ Failed to send order: {str(e)}"

def is_order_intent(question: str) -> bool:
    """Check if user wants to place an order"""
    order_keywords = ['order', 'buy', 'get', 'want', 'purchase', 'delivery', 'takeaway', 'pickup']
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in order_keywords)