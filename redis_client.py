import json
import redis.asyncio as redis
from config import REDIS_URL

redis_pool = None
TIEMPO_EXPIRACION = 60  # 10 minutos

async def conectar_redis():
    global redis_pool
    # Si REDIS_URL no está en config, usamos localhost por defecto
    url = REDIS_URL if REDIS_URL else "redis://localhost:6379/0"
    
    try:
        redis_pool = redis.from_url(url, decode_responses=True)
        # Probamos la conexión
        await redis_pool.ping()
        
        # 🔥 ACTIVAR NOTIFICACIONES (Solo una vez)
        await redis_pool.config_set('notify-keyspace-events', 'Ex')
        print(f"✅ Conectado a Redis ({url}) y Notificaciones ACTIVADAS")
    except Exception as e:
        print(f"❌ Error crítico en Redis: {e}")
        raise e

async def desconectar_redis():
    global redis_pool
    if redis_pool:
        await redis_pool.close()

async def obtener_sesion(telefono: str) -> dict:
    if not redis_pool:
        return None
    datos = await redis_pool.get(f"kipu_sesion:{telefono}")
    return json.loads(datos) if datos else None

async def guardar_sesion(telefono: str, estado_sesion: dict):
    # Usamos el nuevo tiempo de 600 segundos
    if redis_pool:
        await redis_pool.set(
            f"kipu_sesion:{telefono}", 
            json.dumps(estado_sesion), 
            ex=TIEMPO_EXPIRACION
        )

async def eliminar_sesion(telefono: str):
    if redis_pool:
        await redis_pool.delete(f"kipu_sesion:{telefono}")