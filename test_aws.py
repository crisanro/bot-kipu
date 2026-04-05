import os
import boto3
import json

print("--- 1. CHEQUEANDO VARIABLES DE ENTORNO ---")
# Revisamos si la terminal o Dokploy realmente tienen las llaves cargadas
llave_id = os.getenv("AWS_ACCESS_KEY_ID")
print(f"AWS_ACCESS_KEY_ID : {'✅ Configurado' if llave_id else '❌ FALTA (Está vacío)'}")
print(f"AWS_SECRET_NAME   : {os.getenv('AWS_SECRET_NAME', 'Kipu (Por defecto)')}")
print(f"AWS_REGION        : {os.getenv('AWS_DEFAULT_REGION', 'us-east-2 (Por defecto)')}")

print("\n--- 2. INTENTANDO CONECTAR A AMAZON ---")
try:
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager', 
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-2")
    )
    respuesta = client.get_secret_value(SecretId=os.getenv("AWS_SECRET_NAME", "Kipu"))
    secretos_json = json.loads(respuesta['SecretString'])
    
    print("✅ ¡Conexión a AWS perfecta! Te dejaron entrar a la bóveda.")
    
    print("\n--- 3. REVISANDO QUÉ HAY DENTRO DEL JSON ---")
    print("Estas son las llaves que AWS nos devolvió (sin mostrar tus contraseñas):")
    for nombre_llave in secretos_json.keys():
        print(f" 🔹 {nombre_llave}")
        
    print("\n--- RESULTADO FINAL ---")
    if "DATABASE_URL" in secretos_json:
        print("🎉 'DATABASE_URL' SÍ ESTÁ en AWS. El error es de código local.")
    else:
        print("❌ 'DATABASE_URL' NO EXISTE dentro del JSON de AWS. Revisa cómo lo escribiste en la consola (¿Quizás le pusiste DB_URL o espacios extra?).")

except Exception as e:
    print(f"\n❌ AWS RECHAZÓ LA CONEXIÓN. Motivo exacto:\n{e}")