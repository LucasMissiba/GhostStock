import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ghoststock.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
                                                    
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0

            
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@ghoststock.local")

               
    ENABLE_TALISMAN = os.getenv("ENABLE_TALISMAN", "true").lower() == "true"
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
                                              
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

                                                                                  
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "app", "static", "uploads"))
    QR_FOLDER = os.getenv("QR_FOLDER", os.path.join(os.getcwd(), "app", "static", "qrcodes"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024        
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

                   
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))

           
    EXPIRY_ALERT_DAYS = int(os.getenv("EXPIRY_ALERT_DAYS", "7"))
                                                          
    QR_TOKEN_MAX_AGE = int(os.getenv("QR_TOKEN_MAX_AGE", str(90 * 24 * 3600)))

               
    SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))

                   
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "10 per minute")

                       
    SENTRY_DSN = os.getenv("SENTRY_DSN")

                       
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


