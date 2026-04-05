import asyncio
import redis_client  # Importamos el módulo completo, no la variable aislada
from whatsapp import enviar_texto

async def escuchar_expiraciones_redis():
    """Se queda corriendo en segundo plano escuchando si alguna sesión muere por tiempo."""
    
    # Le damos un pequeño respiro de 1 segundo para asegurar que Redis terminó de conectar en main.py
    await asyncio.sleep(1) 
    
    if not redis_client.redis_pool:
        print("❌ No hay conexión a Redis para el Listener")
        return

    pubsub = redis_client.redis_pool.pubsub()
    
    await pubsub.psubscribe('__keyevent@*__:expired')
    print("🎧 Listener de Redis iniciado: Esperando sesiones expiradas...")

    try:
        async for mensaje in pubsub.listen():
            if mensaje['type'] == 'pmessage':
                key_expirada = mensaje['data']
                
                if key_expirada.startswith("kipu_sesion:"):
                    telefono = key_expirada.split(":")[1]
                    print(f"⏰ ¡Sesión de {telefono} expirada! Enviando WhatsApp...")
                    
                    mensaje_timeout = (
                        "⏰ *Sesión cancelada por inactividad*\n\n"
                        "Tu solicitud actual ha superado el límite de espera y fue cancelada por seguridad. "
                        "Si deseas realizar otra operación, simplemente escríbeme *'Hola'* para empezar de nuevo."
                    )
                    
                    await enviar_texto(telefono, mensaje_timeout)
                    
    except asyncio.CancelledError:
        print("🛑 Listener de Redis detenido.")
    except Exception as e:
        print(f"❌ Error en el Listener de Redis: {e}")