from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import json
import asyncio

from config import VERIFY_TOKEN
from database import conectar_db, desconectar_db, guardar_mensaje, actualizar_estado_mensaje, guardar_contacto
from redis_client import conectar_redis, desconectar_redis
from logic import procesar_conversacion 
from redis_listener import escuchar_expiraciones_redis # Importamos el escuchador

# Variable global para guardar la tarea en segundo plano
tarea_listener = None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Al arrancar el servidor ---
    await conectar_db()
    await conectar_redis()
    
    # Encendemos el escuchador en segundo plano
    global tarea_listener
    tarea_listener = asyncio.create_task(escuchar_expiraciones_redis())
    
    yield # Aquí FastAPI está corriendo y recibiendo mensajes
    
    # --- Al apagar el servidor ---
    if tarea_listener:
        tarea_listener.cancel() # Apagamos el escuchador
    await desconectar_redis()
    # (También deberías desconectar tu BD de postgres aquí si tienes la función)

app = FastAPI(lifespan=lifespan)

@app.get("/bot/v1/webhook")
async def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado con éxito")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")

@app.post("/bot/v1/webhook")
async def recibir_mensajes(request: Request, background_tasks: BackgroundTasks):
    datos = await request.json()
    # Procesamos en segundo plano para responderle a Meta en < 3 segundos
    background_tasks.add_task(enrutar_payload, datos)
    return {"status": "ok"}

async def enrutar_payload(datos: dict):
    try:
        # Validamos que el JSON traiga la estructura esperada
        if not datos.get('entry') or not datos['entry'][0].get('changes'):
            return

        cambios = datos['entry'][0]['changes'][0]['value']
        
        # 1. CASO: MENSAJE RECIBIDO (Texto, Botón, Lista, etc.)
        if 'messages' in cambios:
            mensaje = cambios['messages'][0]
            contacto = cambios.get('contacts', [{}])[0]
            
            telefono = mensaje['from']
            # Extraemos el nombre o ponemos el valor por defecto
            nombre_wa = contacto.get('profile', {}).get('name', 'Usuario WhatsApp')
            
            wamid = mensaje['id']
            tipo = mensaje['type']
            reply_to = mensaje.get('context', {}).get('id')
            
            # 🔥 PRIMERO: Creamos o actualizamos el contacto
            await guardar_contacto(telefono, nombre_wa)
            
            # 🔥 SEGUNDO: Ahora sí guardamos el mensaje sin que Postgres llore
            await guardar_mensaje(
                wamid=wamid, 
                telefono=telefono, 
                direccion='entrante', 
                origen='cliente', 
                tipo_mensaje=tipo, 
                contenido=json.dumps(mensaje), 
                estado='recibido',
                reply_to=reply_to
            )
            
            # Pasamos el control a logic.py para que decida qué responder
            await procesar_conversacion(telefono, mensaje)

        # 2. CASO: ACTUALIZACIÓN DE ESTADO (Los Ticks ✓✓)
        elif 'statuses' in cambios:
            estado_obj = cambios['statuses'][0]
            wamid = estado_obj['id']
            nuevo_estado = estado_obj['status']
            
            # Actualizamos el estado en la base de datos
            await actualizar_estado_mensaje(wamid, nuevo_estado)

    except Exception as e:
        print(f"❌ Error procesando el webhook: {e}")
