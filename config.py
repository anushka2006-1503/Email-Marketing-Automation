import os 
 
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 
 
class Config: 
 
    SECRET_KEY = os.environ.get("SECRET_KEY", "email-marketing-dev-key") 
 
    DATABASE_PATH = os.path.join(BASE_DIR, "email_marketing.db") 
 
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com") 
 
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587")) 
 
    SMTP_USER = os.environ.get("SMTP_USER", "anushkaa.1503@gmail.com") 
 
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "alkd fxfx fjyy kmue") 
 
    SMTP_FROM = os.environ.get("SMTP_FROM", "anushkaa.1503@gmail.com") 
 
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"