import boto3
import json
import os
from botocore.exceptions import ClientError

def get_secrets():
    # Buscamos variables de entorno (Dokploy las inyecta automáticamente)
    secret_name = os.getenv("AWS_SECRET_NAME", "Kipu")
    region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-2")

    # Boto3 usa AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY del entorno
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        datos = json.loads(response['SecretString'])
        print(f"✅ Conexión exitosa a AWS. Secreto '{secret_name}' cargado.")
        return datos
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: No se pudo conectar a AWS Secrets Manager.\nDetalle: {e}")
        return {}

# --- CARGA ÚNICA EN MEMORIA RAM ---
secrets = get_secrets()

# --- EXTRACCIÓN CON VALIDACIÓN ---
DATABASE_URL = secrets.get("DATABASE_URL")

# --- EXTRACCIÓN CON VALIDACIÓN ---
DATABASE_URL = secrets.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "🚨 ERROR CRÍTICO: 'DATABASE_URL' está vacía. "
        "El servidor no puede arrancar. Revisa que tus llaves de AWS "
        "(AWS_ACCESS_KEY_ID) estén configuradas en tu entorno de Dokploy o Terminal "
        "y que el nombre del secreto sea correcto."
    )

# --- RESTO DE VARIABLES ---
REDIS_URL = secrets.get("REDIS_URL")
WHATSAPP_TOKEN = secrets.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = secrets.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = secrets.get("VERIFY_TOKEN")
KIPU_CORE_KEY = secrets.get("KIPU_CORE_KEY")
KIPU_BASE_URL = secrets.get("KIPU_API_ADMIN_URL")
KIPU_API_PUBLIC_URL = secrets.get("KIPU_API_PUBLIC_URL")
KIPU_FRONTEND_URL = secrets.get("KIPU_FRONTEND_URL")
KIPU_PAY_URL = secrets.get("KIPU_PAY_URL")
SUPPORT_PHONE_NUMBER = secrets.get("SUPPORT_PHONE_NUMBER")
META_API_VERSION = secrets.get("META_API_VERSION", "v19.0")