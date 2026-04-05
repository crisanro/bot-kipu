import httpx
import json
import urllib.parse
from database import guardar_mensaje
from config import (
    WHATSAPP_TOKEN, 
    WHATSAPP_PHONE_ID, 
    META_API_VERSION,
    KIPU_API_PUBLIC_URL,
    KIPU_FRONTEND_URL
)

# Unificamos Meta API
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}/{WHATSAPP_PHONE_ID}"
META_API_URL = f"{META_BASE_URL}/messages"
META_MEDIA_URL = f"{META_BASE_URL}/media"

HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json"
}

# --- FUNCIÓN AUXILIAR PARA GUARDAR EN BD LO QUE ENVÍA EL BOT ---
async def _registrar_salida(telefono: str, tipo: str, payload: dict, respuesta_meta: dict):
    """Extrae el ID de Meta y guarda el mensaje saliente en PostgreSQL"""
    try:
        if "messages" in respuesta_meta:
            wamid = respuesta_meta["messages"][0]["id"]
            await guardar_mensaje(
                wamid=wamid,
                telefono=telefono,
                direccion='saliente',
                origen='bot',
                tipo_mensaje=tipo,
                contenido=json.dumps(payload),
                estado='sent'
            )
    except Exception as e:
        print(f"⚠️ No se pudo registrar mensaje saliente: {e}")

# --- FUNCIONES DE ENVÍO ---

async def enviar_texto(telefono: str, texto: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "text", payload, resp.json())
        return resp.json()

async def enviar_botones_inicio(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": "Kipu Facturación ⚡"},
            "body": {"text": "Hola 👋, soy tu asistente virtual. Selecciona una opción:"},
            "footer": {"text": "Sistema Automático Kipu.ec"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_facturar", "title": "📝 Facturar"}},
                    {"type": "reply", "reply": {"id": "btn_menu", "title": "⚙️ Ver Menú"}},
                    {"type": "reply", "reply": {"id": "btn_soporte", "title": "💬 Soporte"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()

async def enviar_lista_menu(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Menú Principal 🗂️"},
            "body": {"text": "Aquí tienes más opciones para gestionar tu cuenta en Kipu:"},
            "footer": {"text": "Kipu.ec"},
            "action": {
                "button": "Abrir Opciones",
                "sections": [
                    {
                        "title": "Mi Cuenta",
                        "rows": [
                            {"id": "menu_comprar", "title": "💳 Comprar Créditos", "description": "Recarga facturas en tu cuenta"},
                            {"id": "menu_saldo", "title": "📊 Consultar Saldo", "description": "Mira cuántas facturas te quedan"},
                            {"id": "menu_ultima_fac", "title": "📄 Última Factura", "description": "Reenviar el último PDF emitido"}
                        ]
                    },
                    {
                        "title": "Ayuda",
                        "rows": [
                            {"id": "menu_tutoriales", "title": "📺 Tutoriales", "description": "Aprende a usar el sistema"}
                        ]
                    }
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()

async def enviar_lista_planes(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Planes de Recarga 💳"},
            "body": {"text": "Selecciona el paquete de facturas que deseas adquirir:"},
            "footer": {"text": "Kipu.ec - Pagos Seguros"},
            "action": {
                "button": "Ver Planes",
                "sections": [
                    {
                        "title": "Paquetes Disponibles",
                        "rows": [
                            {"id": "plan_50", "title": "50 Facturas", "description": "Ideal para negocios pequeños"},
                            {"id": "plan_100", "title": "100 Facturas", "description": "El más popular"},
                            {"id": "plan_200", "title": "200 Facturas", "description": "Para negocios en crecimiento"},
                            {"id": "plan_500", "title": "500 Facturas", "description": "Alto volumen"}
                        ]
                    }
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()
    

async def enviar_botones_prospecto(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": "Bienvenido a Kipu 🚀"},
            "body": {"text": "Hola 👋. Veo que este número aún no está registrado en nuestro sistema de facturación. ¿Cómo te puedo ayudar hoy?"},
            "footer": {"text": "Facturación Electrónica Ecuador"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_que_es", "title": "❓ ¿Qué es Kipu?"}},
                    {"type": "reply", "reply": {"id": "btn_registro", "title": "🛒 Crear Cuenta"}},
                    {"type": "reply", "reply": {"id": "btn_ventas", "title": "🤝 Hablar con Ventas"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()
    

import httpx
import os
# (Asegúrate de tener tus constantes META_API_URL y HEADERS aquí)

async def enviar_botones_tipo_cliente(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": "Facturación Express ⚡"
            },
            "body": {
                "text": "Genial, empecemos con la facturación. Por favor ayúdame indicando a quién le vamos a facturar.\n\n_*Nota:* Puedes cancelar el proceso enviando la palabra *Cancelar*._"
            },
            "footer": {
                "text": "Facturación por WS (Kipu.ec)"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "fac_nacional",
                            "title": "🇪🇨 Cédula o RUC"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "fac_extranjero",
                            "title": "🌍 Pasaporte/Ext."
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "fac_final",
                            "title": "👤 Cons. Final"
                        }
                    }
                ]
            }
        }
    }
    
    # Usamos el META_API_URL y HEADERS globales, igual que en tus otras funciones
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        # Registramos la salida en PostgreSQL para que no quede huérfana
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()
    

async def enviar_botones_iva(telefono: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Por último, indícanos la condición del IVA en tu producto o servicio:"},
            "footer": {"text": "Facturación por WS (Kipu.ec)"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "fac_iva0", "title": "No graba IVA"}},
                    {"type": "reply", "reply": {"id": "fac_iva1", "title": "Agrega el IVA"}},
                    {"type": "reply", "reply": {"id": "fac_iva2", "title": "Ya incluye el IVA"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
        return resp.json()

async def enviar_lista_metodos_pago(telefono: str, saldo_pendiente: float, texto_extra: str = ""):
    """Muestra la lista de pagos con el saldo actualizado"""
    texto_body = f"💰 *Saldo a pagar: ${saldo_pendiente:.2f}*\n\nSelecciona el método de pago:"
    if texto_extra:
        texto_body = f"{texto_extra}\n\n{texto_body}"

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Método de Pago 💳"},
            "body": {"text": texto_body},
            "footer": {"text": "Facturación Kipu.ec"},
            "action": {
                "button": "Elegir Método",
                "sections": [{
                    "title": "Opciones SRI",
                    "rows": [
                        {"id": "pago_01", "title": "💵 Efectivo", "description": "Sin sist. financiero"},
                        {"id": "pago_16", "title": "📱 Tarjeta Débito", "description": "Pago inmediato"},
                        {"id": "pago_19", "title": "💳 Tarjeta Crédito", "description": "Diferido o corriente"},
                        {"id": "pago_20", "title": "🔄 Transferencia", "description": "Sist. financiero"},
                        {"id": "pago_18", "title": "💳 Prepago", "description": "Tarjeta prepago"}
                    ]
                }]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())

async def enviar_botones_monto_pago(telefono: str, nombre_metodo: str, saldo_pendiente: float):
    """Pregunta si quiere pagar todo el saldo o solo una parte"""
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"Has seleccionado {nombre_metodo}.\n\n¿Deseas pagar el saldo completo (*${saldo_pendiente:.2f}*) o solo una parte?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "abono_total", "title": f"Total (${saldo_pendiente:.2f})"}},
                    {"type": "reply", "reply": {"id": "abono_parcial", "title": "Otra cantidad"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())

async def enviar_resumen_final(telefono: str, datos: dict):
    """Muestra el desglose total antes de emitir la factura al SRI"""
    correo = datos.get('correo', 'N/A')
    correo_oculto = correo
    if "@" in correo:
        user, domain = correo.split("@")
        correo_oculto = f"{user[:2]}****{user[-2:]}@{domain}" if len(user) > 4 else f"{user[0]}****@{domain}"

    texto_items = ""
    for item in datos.get("items_agregados", []):
        texto_items += f"▫️ {item['nombre']} -> *${item['_total_item']:.2f}*\n"

    nombres_sri = {"01": "Efectivo", "16": "T. Débito", "19": "T. Crédito", "20": "Transferencia", "18": "Prepago"}
    texto_pagos = ""
    for pago in datos.get("pagos_agregados", []):
        nombre_pago = nombres_sri.get(pago['formaPago'], "Otro")
        texto_pagos += f"▫️ {nombre_pago} -> *${pago['total']:.2f}*\n"

    texto_resumen = (
        "🧾 *RESUMEN FINAL DE FACTURA*\n"
        "Revisa que todo esté correcto antes de enviar al SRI:\n\n"
        f"👤 *Cliente:* {datos.get('razon_social', '')}\n"
        f"🆔 *Doc:* {datos.get('identificacion', '')}\n"
        f"📧 *Correo:* {correo_oculto}\n\n"
        "🛒 *DETALLE DE ÍTEMS:*\n"
        f"{texto_items}\n"
        "💳 *MÉTODOS DE PAGO:*\n"
        f"{texto_pagos}\n"
        "---\n"
        f"💰 *Subtotal:* ${datos.get('subtotal', 0):.2f}\n"
        f"➕ *IVA:* ${datos.get('iva', 0):.2f}\n"
        f"🏁 *TOTAL:* ${datos.get('total', 0):.2f}\n"
        "---\n\n"
        "¿Deseas emitir la factura ahora?"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto_resumen},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_emitir_factura", "title": "✅ Emitir Factura"}},
                    {"type": "reply", "reply": {"id": "btn_cancelar", "title": "❌ Cancelar"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())
    

async def enviar_qr_seguimiento(telefono: str, clave_acceso: str):
    link_seguimiento = f"{KIPU_FRONTEND_URL}/consultar?id={clave_acceso}"
    # Codificamos la URL para evitar errores en el QR
    link_encoded = urllib.parse.quote(link_seguimiento)
    url_qr = f"https://quickchart.io/qr?size=500&text={link_encoded}"
    
    mensaje_exito = (
        "*FACTURA GENERADA*\n\n"
        "La factura ha sido generada con éxito, la url para seguimiento es:\n\n"
        f"{link_seguimiento}"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "image",
        "image": {
            "link": url_qr,
            "caption": mensaje_exito
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "image", payload, resp.json())


async def enviar_documento_pdf(telefono: str, clave_acceso: str):
    url_pdf = f"{KIPU_API_PUBLIC_URL}/pdf/{clave_acceso}"
    headers_kipu = {"origin": "kipu.ec"} 

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp_pdf = await client.get(url_pdf, headers=headers_kipu)
            if resp_pdf.status_code != 200:
                print(f"⚠️ No se pudo descargar el PDF de Kipu. Código: {resp_pdf.status_code}")
                return

            pdf_bytes = resp_pdf.content
            nombre_archivo = f"Factura-{clave_acceso}.pdf"

            # 🔥 Usamos la variable unificada META_MEDIA_URL
            headers_media = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
            files = {"file": (nombre_archivo, pdf_bytes, "application/pdf")}
            data = {"messaging_product": "whatsapp"}
            
            resp_media = await client.post(META_MEDIA_URL, headers=headers_media, data=data, files=files)
            media_id = resp_media.json().get("id")

            if not media_id:
                print(f"⚠️ Error al subir Media a Meta: {resp_media.text}")
                return

            # 3. Enviamos el documento usando el ID generado
            payload = {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": nombre_archivo
                }
            }
            resp_envio = await client.post(META_API_URL, headers=HEADERS, json=payload)
            await _registrar_salida(telefono, "document", payload, resp_envio.json())
            
    except Exception as e:
        print(f"❌ Error en el proceso de enviar PDF: {e}")

async def enviar_botones_mas_items(telefono: str, cantidad_items: int):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"✅ Ítem agregado. Tienes *{cantidad_items}* producto(s) en tu factura.\n\n¿Qué deseas hacer ahora?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_mas_items", "title": "➕ Agregar otro"}},
                    {"type": "reply", "reply": {"id": "btn_pagar", "title": "💳 Proceder a cobrar"}}
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        await _registrar_salida(telefono, "interactive", payload, resp.json())