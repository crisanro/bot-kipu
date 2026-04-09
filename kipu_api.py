import httpx
import os
from config import KIPU_BASE_URL, KIPU_CORE_KEY

async def verificar_usuario_kipu(whatsapp_number: str):
    url = f"{KIPU_BASE_URL}/check-status"
    params = {"whatsapp_number": whatsapp_number}
    headers = {"x-n8n-key": KIPU_CORE_KEY}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                return {"error": "problema_servidor"}

            data = response.json()
            
            # 🔥 EL CAMBIO ESTÁ AQUÍ 🔥
            # Solo bloqueamos la entrada si el usuario NO EXISTE o NO ESTÁ CONFIGURADO (ok: false)
            if data.get("ok") is False:
                return {
                    "error": "validacion_kipu", 
                    "codigo": data.get("codigo_error"),
                    "mensaje": data.get("mensaje_cliente", "No cumples con los requisitos.")
                }
            
            # ✅ SI ES CLIENTE (ok: true): Lo dejamos pasar a los botones de inicio.
            # Tenga o no tenga saldo, le damos la bienvenida.
            return {"status": "ok", "data": data.get("data", {})}

    except Exception as e:
        print(f"❌ Error de red/DNS: {e}")
        return {"error": "problema_servidor"}
    

async def emitir_factura_kipu(whatsapp_number: str, json_data: dict):
    url = f"{KIPU_BASE_URL}/invoice-whatsapp"
    headers = {
        "x-n8n-key": KIPU_CORE_KEY,
        "x-whatsapp-number": whatsapp_number,
        "Content-Type": "application/json"
    }
    try:
        # Aumentamos un poco el timeout porque a veces el SRI demora en autorizar
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=json_data)
            return response.json() # Retornamos el diccionario completo
    except Exception as e:
        print(f"❌ Error al emitir factura: {e}")
        return {"ok": False, "estado": "ERROR", "mensaje": "Problemas de red al conectar con Kipu."}

# Añade esto al final de kipu_api.py

Gemini dijo

¡Tienes toda la razón! Tienes un ojo clínico para la seguridad.

El correo electrónico no debería ser obligatorio para todas las peticiones y, de hecho, la lógica de cómo buscamos al usuario en la base de datos debe cambiar dependiendo de la acción que se esté solicitando.

Existen dos escenarios completamente distintos:

    Vincular la cuenta (VALIDAR_WS): Aquí el número de WhatsApp aún no existe en tu base de datos. El usuario hace clic en el enlace, envía el mensaje con su correo, y aquí el email es obligatorio porque es la única forma que tiene el backend de saber a qué cuenta se quiere atar ese número.

    Operaciones en la app (CREAR_TOKEN, ELIMINAR_TOKEN): Aquí el usuario ya es tu cliente y ya tiene su número registrado. Para estas acciones de alta seguridad, el backend debe obligatoriamente validar que ese número de WhatsApp exacto pertenece a un usuario en la base de datos. Si un número desconocido intenta mandar "apikey eliminar", el sistema debe rechazarlo inmediatamente sin importar qué correo envíen.

Para lograr esto, ajustemos el Schema, el Backend y la función del bot para que sean inteligentes según el caso.
1. Actualizar el Schema en FastAPI (app/schemas/seguridad.py)

Hacemos que el email sea opcional, ya que solo lo necesitaremos obligatoriamente cuando se trate de la primera vinculación.
Python

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class RequestPinSchema(BaseModel):
    whatsapp_number: str
    tipo_accion: str
    email: Optional[EmailStr] = None  # Opcional
    metadata: Optional[Dict[str, Any]] = None

2. Actualizar el Endpoint en FastAPI (app/routers/auth.py)

Haremos que el endpoint tome decisiones: si es vinculación busca por correo, si es otra acción de seguridad busca por número telefónico.
Python

@router.post("/request-pin", summary="Generar PIN para n8n/WhatsApp")
async def request_pin(data: RequestPinSchema, db: AsyncSession = Depends(get_db)):
    # Validar que sea un request interno (ej. verificando x-n8n-key en headers)
    
    # 1. Búsqueda dinámica del usuario
    if data.tipo_accion in ["VALIDAR_WS", "VALIDACION_GENERAL"]:
        if not data.email:
            raise HTTPException(status_code=400, detail="El email es obligatorio para vincular una cuenta.")
        # Buscamos por correo porque el número aún no está registrado
        query = text("SELECT emisor_id, email FROM profiles WHERE LOWER(email) = LOWER(:val)")
        param = {"val": data.email}
    else:
        # Para CREAR o ELIMINAR APIs, LA SEGURIDAD ES EL NÚMERO
        query = text("SELECT emisor_id, email FROM profiles WHERE whatsapp_number = :val")
        param = {"val": data.whatsapp_number}

    res = await db.execute(query, param)
    user = res.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no autorizado o no encontrado.")

    # 2. Generar PIN de 6 dígitos
    pin = f"{random.randint(100000, 999999)}"
    
    # 3. Guardar el challenge
    query_insert = text("""
        INSERT INTO auth_challenges (email, whatsapp_number, pin, tipo_accion, metadata, emisor_id, expires_at)
        VALUES (:email, :ws, :pin, :tipo, :meta, :eid, NOW() + INTERVAL '10 minutes')
    """)
    await db.execute(query_insert, {
        "email": user.email, # Usamos el email real de la base de datos, siempre
        "ws": data.whatsapp_number, 
        "pin": pin, 
        "tipo": data.tipo_accion, 
        "meta": data.metadata or {}, 
        "eid": user.emisor_id
    })
    await db.commit()

    return {"ok": True, "pin": pin}

3. Actualizar la función en el bot (kipu_api.py)

Ahora el email es el tercer parámetro y es opcional. Así, tu código del bot queda mucho más limpio al pedir llaves.
Python

async def solicitar_pin_auth(whatsapp_number: str, tipo_accion: str, email: str = None, metadata: dict = None):
    url = f"{KIPU_BASE_URL}/request-pin"
    headers = {
        "x-n8n-key": KIPU_CORE_KEY, # Reutilizamos tu llave de seguridad interna
        "Content-Type": "application/json"
    }
    payload = {
        "whatsapp_number": whatsapp_number,
        "tipo_accion": tipo_accion
    }
    
    if email:
        payload["email"] = email
    if metadata:
        payload["metadata"] = metadata
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.json()
    except Exception as e:
        print(f"❌ Error al solicitar PIN 2FA: {e}")
        return {"ok": False, "detail": "Error de red interna"}

async def obtener_apikeys_bot(whatsapp_number: str):
    """
    Nota: Necesitarás crear un endpoint interno en FastAPI tipo 
    GET /api-keys/internal/{whatsapp_number} que responda la lista de keys.
    """
    url = f"{KIPU_BASE_URL}/api-keys/internal/{whatsapp_number}"
    headers = {"x-n8n-key": KIPU_CORE_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            return resp.json()
    except Exception as e:
        print(f"❌ Error al listar llaves: {e}")
        return {"ok": False, "keys": []}
