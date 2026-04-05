import asyncpg
from config import DATABASE_URL

# Variable global para mantener el pool de conexiones
pool = None

async def conectar_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Conectado a PostgreSQL (Pool)")

async def desconectar_db():
    global pool
    if pool:
        await pool.close()

# En database.py

async def guardar_mensaje(wamid: str, telefono: str, direccion: str, origen: str, tipo_mensaje: str, contenido: str, estado: str, reply_to: str = None):
    query = """
        INSERT INTO ws_mensajes (wamid, telefono, direccion, origen, tipo_mensaje, contenido, estado, reply_to)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
        ON CONFLICT (wamid) DO NOTHING;
    """
    async with pool.acquire() as conexion:
        await conexion.execute(query, wamid, telefono, direccion, origen, tipo_mensaje, contenido, estado, reply_to)

async def actualizar_estado_mensaje(wamid: str, nuevo_estado: str):
    query = """
        UPDATE ws_mensajes 
        SET estado = $1, actualizado_en = CURRENT_TIMESTAMP
        WHERE wamid = $2;
    """
    async with pool.acquire() as conexion:
        await conexion.execute(query, nuevo_estado, wamid)


# Agrégalo en database.py (debajo de tus otras funciones)

async def guardar_contacto(telefono: str, nombre_perfil: str):
    # Nota: Si tu columna en la base de datos se llama solo 'nombre' en lugar 
    # de 'nombre_perfil', ajusta la palabra aquí abajo:
    query = """
        INSERT INTO ws_contactos (telefono, nombre_perfil)
        VALUES ($1, $2)
        ON CONFLICT (telefono) DO UPDATE 
        SET nombre_perfil = EXCLUDED.nombre_perfil;
    """
    async with pool.acquire() as conexion:
        await conexion.execute(query, telefono, nombre_perfil)