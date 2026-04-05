import os
from dotenv import load_dotenv

load_dotenv()

# Meta / WhatsApp API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_API_VERSION = os.getenv("META_API_VERSION", "v19.0") # Centralizamos la versión

# Bases de datos
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Kipu API & Enlaces Frontend
KIPU_CORE_KEY = os.getenv("KIPU_CORE_KEY")
KIPU_BASE_URL = os.getenv("KIPU_API_ADMIN_URL")
KIPU_API_PUBLIC_URL = os.getenv("KIPU_API_PUBLIC_URL")
KIPU_FRONTEND_URL = os.getenv("KIPU_FRONTEND_URL")
KIPU_PAY_URL = os.getenv("KIPU_PAY_URL")

# Soporte
SUPPORT_PHONE_NUMBER = os.getenv("SUPPORT_PHONE_NUMBER")