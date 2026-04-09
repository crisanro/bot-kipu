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

async def solicitar_pin_auth(email: str, whatsapp_number: str, tipo_accion: str, metadata: dict = None):
    url = f"{KIPU_BASE_URL}/auth/request-pin"
    headers = {
        "x-n8n-key": KIPU_CORE_KEY, # Reutilizamos tu llave de seguridad interna
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "whatsapp_number": whatsapp_number,
        "tipo_accion": tipo_accion,
        "metadata": metadata or {}
    }
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
