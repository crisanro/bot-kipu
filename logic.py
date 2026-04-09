import asyncio
from whatsapp import (
    enviar_texto, 
    enviar_botones_inicio, 
    enviar_botones_prospecto, 
    enviar_lista_menu, 
    enviar_lista_planes,
    enviar_botones_tipo_cliente,
    enviar_botones_monto_pago,
    enviar_lista_metodos_pago,
    enviar_resumen_final,
    enviar_botones_iva, enviar_botones_mas_items,enviar_qr_seguimiento, enviar_documento_pdf,enviar_documento_xml
)
from redis_client import guardar_sesion, eliminar_sesion, obtener_sesion
from kipu_api import verificar_usuario_kipu
from config import KIPU_FRONTEND_URL, KIPU_PAY_URL, SUPPORT_PHONE_NUMBER


def validar_documento_ecuador(documento: str):
    documento = documento.replace("-", "").replace(".", "").replace(" ", "").strip()
    
    if not documento.isdigit():
        return False, "El documento debe contener solo números.", ""
    
    if len(documento) not in [10, 13]:
        return False, "Longitud no válida (debe ser 10 o 13 dígitos).", ""
        
    provincia = int(documento[0:2])
    if provincia < 1 or provincia > 24:
        return False, f"Provincia '{documento[0:2]}' no existe.", ""
        
    tercer_digito = int(documento[2])
    
    # FUNCIONES INTERNAS DE MÓDULO
    def validar_modulo_10(id_str):
        digitos = [int(x) for x in id_str[:9]]
        verificador_recibido = int(id_str[9])
        suma = 0
        for i, val in enumerate(digitos):
            prod = val * 2 if i % 2 == 0 else val * 1
            if prod > 9: prod -= 9
            suma += prod
        residuo = suma % 10
        verificador_calculado = 0 if residuo == 0 else 10 - residuo
        return verificador_calculado == verificador_recibido

    def validar_modulo_11(id_str):
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        digitos = [int(x) for x in id_str[:9]]
        verificador_recibido = int(id_str[9])
        suma = sum([val * coeficientes[i] for i, val in enumerate(digitos)])
        residuo = suma % 11
        verificador_calculado = 0 if residuo == 0 else 11 - residuo
        return verificador_calculado == verificador_recibido

    # VALIDACIÓN CÉDULA (05)
    if len(documento) == 10:
        if tercer_digito < 6:
            if validar_modulo_10(documento):
                return True, "", "05"
            return False, "Número de cédula inválido.", ""
        return False, "Cédula inválida (tercer dígito incorrecto).", ""
        
    # VALIDACIÓN RUC (04)
    elif len(documento) == 13:
        if not documento.endswith("001"):
            return False, "El RUC debe terminar en 001.", ""
            
        if tercer_digito < 6: # Natural
            es_valido = validar_modulo_10(documento[:10])
        elif tercer_digito == 9: # Jurídica
            es_valido = validar_modulo_11(documento[:10])
        elif tercer_digito == 6: # Pública
            es_valido = True
        else:
            return False, "Tercer dígito de RUC inválido.", ""
            
        if es_valido:
            return True, "", "04"
        return False, "El número de RUC no es válido.", ""

async def iniciar_temporizador(telefono: str, sesion: dict):
    await guardar_sesion(telefono, sesion)
    print(f"⏲️ Temporizador reiniciado para {telefono} (10 min)")

async def cancelar_temporizador(telefono: str):
    await eliminar_sesion(telefono)
    print(f"🚫 Temporizador cancelado para {telefono}")


async def procesar_conversacion(telefono: str, mensaje_wa: dict):
    tipo = mensaje_wa.get("type")
    id_interactivo = None
    texto_usuario = ""

    # 1. EXTRACCIÓN DE DATOS
    if tipo == "interactive":
        if "button_reply" in mensaje_wa["interactive"]:
            id_interactivo = mensaje_wa["interactive"]["button_reply"]["id"]
        elif "list_reply" in mensaje_wa["interactive"]:
            id_interactivo = mensaje_wa["interactive"]["list_reply"]["id"]
    elif tipo == "text":
        texto_usuario = mensaje_wa["text"]["body"].lower().strip()


    if tipo == "text":
        texto_usuario = mensaje_wa["text"]["body"].lower().strip()

    # --- NUEVA LÓGICA DE SEGURIDAD Y 2FA ---
    
    # 1. Vincular WhatsApp
    if texto_usuario.startswith("kipu_validar y vincular a "):
        correo = texto_usuario.replace("kipu_validar y vincular a ", "").strip()
        from kipu_api import solicitar_pin_auth
        
        await enviar_texto(telefono, "⏳ Procesando tu solicitud de seguridad...")
        resp = await solicitar_pin_auth(correo, telefono, "VALIDAR_WS")
        
        if resp.get("ok"):
            await enviar_texto(telefono, f"🔐 ¡Hola! Hemos generado tu código de seguridad.\n\nTu PIN es: *{resp['pin']}*\n\nRegresa a la plataforma web e ingrésalo para vincular este número.")
        else:
            await enviar_texto(telefono, "⚠️ No pudimos generar el código. Verifica que el enlace esté correcto.")
        return

    # 2. Crear API Key
    if texto_usuario.startswith("apikey crear "):
        nombre_key = texto_usuario.replace("apikey crear ", "").strip()
        validacion = await verificar_usuario_kipu(telefono)
        
        if validacion.get("status") == "ok":
            correo = validacion.get("data", {}).get("email") # Asegúrate de que el API de Kipu retorne el 'email' en 'data'
            from kipu_api import solicitar_pin_auth
            
            resp = await solicitar_pin_auth(correo, telefono, "CREAR_TOKEN", {"nombre": nombre_key})
            if resp.get("ok"):
                await enviar_texto(telefono, f"🔑 Solicitaste crear la llave '{nombre_key}'.\n\nIngresa este PIN en la web para generarla:\n\n*{resp['pin']}*")
            else:
                await enviar_texto(telefono, "⚠️ Hubo un problema al generar el PIN de seguridad.")
        else:
            await enviar_texto(telefono, "⚠️ Tu número no está vinculado a una cuenta activa de Kipu.")
        return

    # 3. Eliminar API Key (Inicia Flujo)
    if texto_usuario == "apikey eliminar":
        validacion = await verificar_usuario_kipu(telefono)
        
        if validacion.get("status") == "ok":
            from kipu_api import obtener_apikeys_bot
            from whatsapp import enviar_lista_apikeys
            
            await enviar_texto(telefono, "🔍 Buscando tus llaves activas...")
            resp_keys = await obtener_apikeys_bot(telefono)
            keys = resp_keys.get("keys", [])
            
            if not keys:
                await enviar_texto(telefono, "No tienes API Keys activas en este momento.")
                return
                
            await enviar_lista_apikeys(telefono, keys)
            
            # Guardamos sesión para atrapar la respuesta de la lista
            sesion = await obtener_sesion(telefono) or {"datos": validacion.get("data", {})}
            sesion["paso"] = "ESPERANDO_ELIMINAR_APIKEY"
            sesion["datos"]["email"] = validacion.get("data", {}).get("email")
            await iniciar_temporizador(telefono, sesion)
        else:
            await enviar_texto(telefono, "⚠️ Tu número no está vinculado a una cuenta activa.")
        return

    # 3. DEscargar facturas
    if texto_usuario.startswith("descargar"):
        partes = texto_usuario.split() # Separa por espacios
        
        # Caso 1: Solo envió "descargar"
        if len(partes) == 1:
            await enviar_texto(telefono, "Para poder enviarte la factura, por favor ayúdame escribiendo la palabra *Descargar* seguida de los 49 dígitos de tu clave de acceso.\n\nEjemplo: _Descargar 0102202301179..._")
            return

        # Caso 2: Envió "descargar clave"
        clave_acceso = partes[1]
        if len(clave_acceso) == 49 and clave_acceso.isdigit():
            await enviar_texto(telefono, "🔍 Localizando tus archivos, un momento por favor...")
            
            # Importamos y ejecutamos las funciones de whatsapp.py
            await enviar_documento_pdf(telefono, clave_acceso)
            await asyncio.sleep(1) # Dale 2 segundos de respiro a Meta
            await enviar_documento_xml(telefono, clave_acceso)
            
            await enviar_texto(telefono, "✅ Archivos enviados con éxito.")
            # Si quieres cerrar la sesión actual si existía una:
            await eliminar_sesion(telefono)
        else:
            await enviar_texto(telefono, "⚠️ La clave de acceso proporcionada no parece ser válida (debe tener 49 dígitos numéricos). Revisa el número e intenta de nuevo.")
        return

    # 2. COMANDO DE SALIDA CORTÉS
    if texto_usuario in ["cancelar", "salir", "chao", "adios", "adiós"] or id_interactivo == "btn_cancelar":
        await eliminar_sesion(telefono)
        mensaje_despedida = (
            "Entendido. He cancelado la solicitud actual. ✅\n\n"
            "Fue un gusto atenderte. Si necesitas algo más en el futuro, "
            "solo escríbenos para empezar de nuevo. "
            "¡Que tengas un excelente día! 😊"
        )
        await enviar_texto(telefono, mensaje_despedida)
        return

    # 3. OBTENER ESTADO ACTUAL
    sesion = await obtener_sesion(telefono)

    # ==========================================
    # LA PUERTA DE ENTRADA 
    # ==========================================
    if not sesion:
        saludos = ["hola", "buenas", "inicio", "menú", "menu"]
        es_inicio_fresco = texto_usuario in saludos or id_interactivo is not None
        
        if not es_inicio_fresco and texto_usuario != "":
            mensaje_timeout = (
                "⏰ *Sesión expirada*\n\n"
                "Lo sentimos, la solicitud anterior superó el tiempo límite de 10 minutos y fue cancelada por seguridad. "
                "Para ayudarte de nuevo, por favor selecciona una opción:"
            )
            await enviar_texto(telefono, mensaje_timeout)

        validacion = await verificar_usuario_kipu(telefono)
        
        if validacion.get("error") in ["problema_servidor", "respuesta_invalida"]:
            await enviar_texto(telefono, 
                "⚠️ Lo sentimos, estamos teniendo problemas técnicos en nuestro sistema central. "
                f"Por favor, comunícate con soporte:\n👉 https://wa.me/{SUPPORT_PHONE_NUMBER}")
            return
            
        if validacion.get("error") == "validacion_kipu":
            mensaje_api = validacion.get("mensaje")
            await enviar_texto(telefono, mensaje_api)
            await enviar_botones_prospecto(telefono)
            await guardar_sesion(telefono, {"paso": "ESPERANDO_ACCION_PROSPECTO", "datos": {}})
        else:
            await enviar_botones_inicio(telefono)
            await guardar_sesion(telefono, {
                "paso": "ESPERANDO_ACCION_CLIENTE", 
                "datos": validacion.get("data", {})
            })
        return

    paso = sesion.get("paso")

    # ==========================================
    # CAMINO A: LÓGICA DEL PROSPECTO
    # ==========================================
    if paso == "ESPERANDO_ACCION_PROSPECTO":
        if id_interactivo == "btn_que_es":
            await enviar_texto(telefono, "Kipu es la plataforma más rápida para emitir facturas electrónicas en Ecuador 🇪🇨.\n\n✅ Envía desde WhatsApp\n✅ Sin instalar programas\n✅ Autorizado por el SRI\n\nMira cómo funciona aquí: [Link a tu video]")
            await enviar_botones_prospecto(telefono)
            
        elif id_interactivo == "btn_registro":
            await enviar_texto(telefono, "¡Genial! 🛒\n\nPuedes ver nuestros planes y crear tu cuenta en menos de 2 minutos ingresando aquí:\n👉 https://kipu.ec/planes\n\nUna vez que tengas tu cuenta, vuelve a escribirme 'Hola'.")
            await eliminar_sesion(telefono)
            
        elif id_interactivo == "btn_ventas":
            await enviar_texto(telefono, f"👨‍💻 Un asesor humano está listo para resolver tus dudas.\n\nHaz clic aquí para chatear con Ventas:\n👉 https://wa.me/{SUPPORT_PHONE_NUMBER}")
            await eliminar_sesion(telefono)
        else:
            await enviar_texto(telefono, "⚠️ Por favor, selecciona una de las opciones del menú superior o escribe *'Salir'*.")

    # ==========================================
    # CAMINO B: LÓGICA DEL CLIENTE 
    # ==========================================
    elif paso == "ESPERANDO_ACCION_CLIENTE":
        if id_interactivo == "btn_facturar":
            datos_usuario = sesion.get("datos", {})
            balance = int(datos_usuario.get("balance", 0))

            if balance > 0:
                # ✅ ADVERTENCIA DE POCOS CRÉDITOS
                if balance <= 9:
                    await enviar_texto(telefono, f"⚠️ *Aviso:* Te quedan {balance} créditos disponibles. Recuerda recargar pronto para no quedarte sin facturas.")
                
                # Enviamos el nuevo menú de 3 opciones
                await enviar_botones_tipo_cliente(telefono)
                
                sesion["paso"] = "ESPERANDO_TIPO_CLIENTE"
                await iniciar_temporizador(telefono, sesion)
            else:
                # ❌ SIN CRÉDITOS
                await enviar_texto(telefono, 
                    "⚠️ *Saldo Insuficiente*\n\n"
                    "No tienes créditos disponibles en tu cuenta para emitir facturas. "
                    "Por favor, selecciona un paquete de recarga para continuar:")
                await enviar_lista_planes(telefono)
                sesion["paso"] = "ESPERANDO_PLAN"
                await iniciar_temporizador(telefono, sesion)

        elif id_interactivo == "btn_menu":
            await enviar_lista_menu(telefono)
            sesion["paso"] = "ESPERANDO_OPCION_MENU"
            await iniciar_temporizador(telefono, sesion)

        elif id_interactivo == "btn_soporte":
            await enviar_texto(telefono, "👨‍💻 *Soporte Kipu*\nEscríbenos directamente aquí: https://wa.me/593992534211")
            await eliminar_sesion(telefono)
        else:
            await enviar_texto(telefono, "⚠️ Por favor, selecciona una de las opciones del menú superior para continuar.")

    # ==========================================
    # NUEVO FLUJO: SELECCIÓN DE CLIENTE Y DOCUMENTO
    # ==========================================
    # ... código anterior ...
    elif paso == "ESPERANDO_TIPO_CLIENTE":
        opciones_validas = ["fac_nacional", "fac_extranjero", "fac_final"]
        if id_interactivo in opciones_validas:
            sesion["datos"]["tipo_cliente_seleccionado"] = id_interactivo
            
            if id_interactivo == "fac_final":
                sesion["datos"]["codigo_sri"] = "07"
                sesion["datos"]["identificacion"] = "9999999999999"
                sesion["datos"]["razon_social"] = "CONSUMIDOR FINAL"
                sesion["datos"]["correo"] = "" 
                sesion["datos"]["items_agregados"] = []
                
                await enviar_texto(telefono, "👤 *Consumidor Final*\n\nPor favor, escribe la **descripción** del producto o servicio (Ej: Consultoría web):")
                sesion["paso"] = "ESPERANDO_DESCRIPCION"
            else:
                texto_ayuda = "Cédula o RUC" if id_interactivo == "fac_nacional" else "Pasaporte o ID Extranjero"
                await enviar_texto(telefono, f"✍️ Por favor, escribe el número de **{texto_ayuda}**:")
                sesion["paso"] = "ESPERANDO_NUMERO_ID"
                
            await iniciar_temporizador(telefono, sesion)
            
    elif paso == "ESPERANDO_NUMERO_ID":
        tipo_cliente = sesion["datos"].get("tipo_cliente_seleccionado")
        
        if tipo_cliente == "fac_nacional":
            es_valido, error, codigo_sri = validar_documento_ecuador(texto_usuario) # <--- Usamos tu validador
            if not es_valido:
                await enviar_texto(telefono, f"❌ {error}\nPor favor, ingresa un documento válido o escribe *Cancelar*.")
                return
            sesion["datos"]["codigo_sri"] = codigo_sri
        else:
            # Extranjero / Pasaporte
            sesion["datos"]["codigo_sri"] = "06" 

        sesion["datos"]["identificacion"] = texto_usuario
        await enviar_texto(telefono, "✅ Documento registrado.\n\nPor favor, escribe la **Razón Social** o **Nombre** del cliente:")
        sesion["paso"] = "ESPERANDO_NOMBRE"
        await iniciar_temporizador(telefono, sesion)

    elif paso == "ESPERANDO_NOMBRE":
        sesion["datos"]["razon_social"] = texto_usuario.upper()
        sesion["datos"]["correo"] = "" 
        sesion["datos"]["items_agregados"] = []
        
        await enviar_texto(telefono, "📝 ¿Cuál es la **descripción** del primer producto o servicio? (Ej: Servicio de Mantenimiento)")
        sesion["paso"] = "ESPERANDO_DESCRIPCION"
        await iniciar_temporizador(telefono, sesion)

    elif paso == "ESPERANDO_DESCRIPCION":
        sesion["datos"]["descripcion"] = texto_usuario
        await enviar_texto(telefono, "💰 Ingresa el **valor base** del producto o servicio (Ej: 15.50):")
        sesion["paso"] = "ESPERANDO_MONTO_BASE"
        await iniciar_temporizador(telefono, sesion)

    elif paso == "ESPERANDO_MONTO_BASE":
        try:
            valor_base = float(texto_usuario.replace(',', '.'))
            sesion["datos"]["valor_base"] = valor_base
            
            # Mandamos los botones de IVA
            await enviar_botones_iva(telefono)
            sesion["paso"] = "ESPERANDO_TIPO_IVA"
            await iniciar_temporizador(telefono, sesion)
        except ValueError:
            await enviar_texto(telefono, "⚠️ Ingresa un monto numérico válido (Ej: 10.50).")

    elif paso == "ESPERANDO_TIPO_IVA":
        if id_interactivo in ["fac_iva0", "fac_iva1", "fac_iva2"]:
            valor_base = sesion["datos"]["valor_base"]
            desc_actual = sesion["datos"]["descripcion"]
            porcentaje_iva = 0.15 
            
            if id_interactivo == 'fac_iva0':
                subtotal, iva, total, tarifa_iva = valor_base, 0.0, valor_base, 0
            elif id_interactivo == 'fac_iva1':
                subtotal, iva, total, tarifa_iva = valor_base, valor_base * porcentaje_iva, valor_base * (1 + porcentaje_iva), porcentaje_iva
            elif id_interactivo == 'fac_iva2':
                subtotal = valor_base / (1 + porcentaje_iva)
                iva = valor_base - subtotal
                total, tarifa_iva = valor_base, porcentaje_iva
                
            # Armamos el ítem actual y lo guardamos en la canasta
            nuevo_item = {
                "codigo": f"ITEM00{len(sesion['datos'].get('items_agregados', [])) + 1}", 
                "nombre": desc_actual,
                "cantidad": 1, 
                "precio": round(subtotal, 2),
                "descuento": 0.00, 
                "tarifaIva": tarifa_iva,
                "_iva_item": iva, 
                "_total_item": total 
            }
            sesion["datos"]["items_agregados"].append(nuevo_item)
            
            # Preguntamos si quiere más ítems o pagar
            await enviar_botones_mas_items(telefono, len(sesion["datos"]["items_agregados"]))
            sesion["paso"] = "ESPERANDO_DECISION_ITEMS"
            await iniciar_temporizador(telefono, sesion)
            
            # ❌ (OJO: AQUÍ BORRAMOS EL CÓDIGO VIEJO QUE MOSTRABA EL RESUMEN)


    # =======================================================
    # PASO 3: ¿AGREGAR MÁS O PROCEDER A COBRAR?
    # =======================================================
    elif paso == "ESPERANDO_DECISION_ITEMS":
        if id_interactivo == "btn_mas_items":
            await enviar_texto(telefono, "📝 Escribe la **descripción** del siguiente producto/servicio:")
            sesion["paso"] = "ESPERANDO_DESCRIPCION"
            await iniciar_temporizador(telefono, sesion)
            
        elif id_interactivo == "btn_pagar":
            items = sesion["datos"]["items_agregados"]
            gran_subtotal = sum(item["precio"] for item in items)
            gran_iva = sum(item["_iva_item"] for item in items)
            gran_total = sum(item["_total_item"] for item in items)
            
            if sesion["datos"].get("codigo_sri") == "07" and gran_total > 50.00:
                await enviar_texto(telefono, f"❌ *Límite Excedido*\nEl total es ${gran_total:.2f}. Consumidor Final no puede superar los **$50.00**.\nEnvía *Cancelar* para reiniciar con datos.")
                return

            sesion["datos"].update({
                "subtotal": round(gran_subtotal, 2), 
                "iva": round(gran_iva, 2), 
                "total": round(gran_total, 2),
                "saldo_pendiente": round(gran_total, 2), 
                "pagos_agregados": [] 
            })
            
            await enviar_lista_metodos_pago(telefono, gran_total, "🛒 Ítems listos. ¿Cómo deseas pagar?")
            sesion["paso"] = "ESPERANDO_SELECCION_PAGO"
            await iniciar_temporizador(telefono, sesion)


    # =======================================================
    # BUCLE DE PAGOS (UX)
    # =======================================================
    elif paso == "ESPERANDO_SELECCION_PAGO":
        if id_interactivo and id_interactivo.startswith("pago_"):
            codigo_pago = id_interactivo.split("_")[1]
            saldo = sesion["datos"]["saldo_pendiente"]
            
            nombres_pago = {"01": "💵 Efectivo", "16": "📱 Tarjeta Débito", "19": "💳 Tarjeta Crédito", "20": "🔄 Transferencia", "18": "💳 Prepago"}
            nombre_metodo = nombres_pago.get(codigo_pago, "este método")
            
            sesion["datos"]["metodo_actual"] = {"codigo": codigo_pago, "nombre": nombre_metodo}
            
            await enviar_botones_monto_pago(telefono, nombre_metodo, saldo)
            sesion["paso"] = "ESPERANDO_TIPO_ABONO"
            await iniciar_temporizador(telefono, sesion)

    elif paso == "ESPERANDO_TIPO_ABONO":
        saldo_actual = sesion["datos"]["saldo_pendiente"]
        if id_interactivo == "abono_total":
            sesion["datos"]["pagos_agregados"].append({
                "formaPago": sesion["datos"]["metodo_actual"]["codigo"],
                "total": saldo_actual,
                "plazo": 0, "unidadTiempo": "dias"
            })
            sesion["datos"]["saldo_pendiente"] = 0.0
            
            # EL SALDO ES CERO -> MOSTRAMOS RESUMEN FINAL
            await enviar_resumen_final(telefono, sesion["datos"])
            sesion["paso"] = "ESPERANDO_CONFIRMACION_FINAL"
            await iniciar_temporizador(telefono, sesion)
            
        elif id_interactivo == "abono_parcial":
            nombre_metodo = sesion["datos"]["metodo_actual"]["nombre"]
            await enviar_texto(telefono, f"✍️ Escribe el monto exacto que vas a abonar con {nombre_metodo} (Ej: 15.50):")
            sesion["paso"] = "ESPERANDO_MONTO_PARCIAL"
            await iniciar_temporizador(telefono, sesion)

    elif paso == "ESPERANDO_MONTO_PARCIAL":
        try:
            monto_abonado = float(texto_usuario.replace(',', '.'))
            saldo_actual = sesion["datos"]["saldo_pendiente"]
            
            if monto_abonado <= 0 or monto_abonado > saldo_actual:
                await enviar_texto(telefono, f"⚠️ El monto debe ser mayor a 0 y no superar tu saldo de *${saldo_actual:.2f}*. Intenta de nuevo:")
                return
                
            sesion["datos"]["pagos_agregados"].append({
                "formaPago": sesion["datos"]["metodo_actual"]["codigo"],
                "total": round(monto_abonado, 2),
                "plazo": 0, "unidadTiempo": "dias"
            })
            
            sesion["datos"]["saldo_pendiente"] = round(saldo_actual - monto_abonado, 2)
            
            if sesion["datos"]["saldo_pendiente"] > 0:
                nombre_metodo = sesion["datos"]["metodo_actual"]["nombre"]
                texto_restante = f"✅ Registrado: ${monto_abonado:.2f} en {nombre_metodo}."
                await enviar_lista_metodos_pago(telefono, sesion["datos"]["saldo_pendiente"], texto_restante)
                sesion["paso"] = "ESPERANDO_SELECCION_PAGO"
            else:
                # EL SALDO ES CERO -> MOSTRAMOS RESUMEN FINAL
                await enviar_resumen_final(telefono, sesion["datos"])
                sesion["paso"] = "ESPERANDO_CONFIRMACION_FINAL"
                
            await iniciar_temporizador(telefono, sesion)

        except ValueError:
            await enviar_texto(telefono, "⚠️ Formato inválido. Ingresa solo números (Ej: 20.00):")


    # =======================================================
    # CONFIRMACIÓN FINAL Y EMISIÓN (SRI)
    # =======================================================
    elif paso == "ESPERANDO_CONFIRMACION_FINAL":
        if id_interactivo == "btn_emitir_factura":
            datos_kipu = sesion["datos"]
            
            # Limpiar variables auxiliares de los ítems
            items_limpios = []
            for item in datos_kipu["items_agregados"]:
                item_limpio = {k: v for k, v in item.items() if not k.startswith("_")}
                items_limpios.append(item_limpio)
            
            # Construcción del JSON Maestro
            json_factura = {
                "rucEmisor": datos_kipu.get("ruc"),
                "establecimiento": "001",
                "punto_emision": "333",
                "formato": 1,
                "cliente": {
                    "tipoId": datos_kipu.get("codigo_sri"),
                    "identificacion": datos_kipu.get("identificacion"),
                    "razonSocial": datos_kipu.get("razon_social"),
                    "direccion": "", "telefono": "", "email": datos_kipu.get("correo", "")
                },
                "items": items_limpios,
                "pagos": datos_kipu.get("pagos_agregados", []),
                "infoAdicional": [
                    {"nombre": "Generado", "valor": "Desde WhatsApp con Kipu.ec ⚡"}
                ]
            }

            await enviar_texto(telefono, "⏳ Procesando factura con el SRI, esto tomará unos segundos...")
            
            from kipu_api import emitir_factura_kipu
            respuesta = await emitir_factura_kipu(telefono, json_factura)
            
            if not respuesta.get("ok"):
                await enviar_texto(telefono, f"❌ Ocurrió un problema: {respuesta.get('mensaje', 'Error desconocido.')}")
            else:
                estado = respuesta.get("estado", "")
                clave_acceso = respuesta.get("claveAcceso", "")
                mensaje_api = respuesta.get("mensaje", "")

                if estado in ["DEVUELTA", "RECHAZADO"]:
                    await enviar_texto(telefono, f"⚠️ *Factura {estado}*\nEl SRI o nuestro sistema reportó: _{mensaje_api}_")
                else:
                    await enviar_qr_seguimiento(telefono, clave_acceso)
                    if estado == "AUTORIZADO":
                        await enviar_documento_pdf(telefono, clave_acceso)

            await eliminar_sesion(telefono)
            
        elif id_interactivo == "btn_cancelar":
            # Si el cliente cancela la pre-visualización de la factura
            await enviar_texto(telefono, "❌ Emisión cancelada. Puedes iniciar de nuevo cuando desees enviando la palabra 'Hola'.")
            await eliminar_sesion(telefono)

    # ==========================================
    # MENÚ ADICIONAL Y PLANES
    # ==========================================
    elif paso == "ESPERANDO_OPCION_MENU":
        if id_interactivo and id_interactivo.startswith("menu_"):
            if id_interactivo == "menu_comprar":
                await enviar_lista_planes(telefono)
                sesion["paso"] = "ESPERANDO_PLAN"
                await iniciar_temporizador(telefono, sesion)
                
            elif id_interactivo == "menu_saldo":
                balance_actual = sesion.get("datos", {}).get("balance", 0)
                await enviar_texto(telefono, f"🔎 Consultando sistema...\n\nTienes *{balance_actual} facturas* disponibles.")
                await enviar_botones_inicio(telefono)
                sesion["paso"] = "ESPERANDO_ACCION_CLIENTE"
                await iniciar_temporizador(telefono, sesion)
                
            elif id_interactivo == "menu_tutoriales":
                await enviar_texto(telefono, "📺 *Tutoriales Kipu*:\n1. Firma electrónica: [Link]\n2. Primeros pasos: [Link]")
                await enviar_botones_inicio(telefono)
                sesion["paso"] = "ESPERANDO_ACCION_CLIENTE"
                await iniciar_temporizador(telefono, sesion)
        else:
            await enviar_texto(telefono, "⚠️ Opción no válida. Por favor, selecciona una de la lista o escribe *'Salir'*.")

    elif paso == "ESPERANDO_PLAN":
        if id_interactivo and id_interactivo.startswith("plan_"):
            links = {
                "plan_50": f"{KIPU_PAY_URL}/50",
                "plan_100": f"{KIPU_PAY_URL}/100",
                "plan_200": f"{KIPU_PAY_URL}/200",
                "plan_500": f"{KIPU_PAY_URL}/500"
            }
            link = links.get(id_interactivo, KIPU_PAY_URL)
            await enviar_texto(telefono, f"✅ Excelente. Usa este link para completar tu pago de forma segura:\n👉 {link}\n\nTus facturas se acreditarán automáticamente.")
            await eliminar_sesion(telefono)
        else:
            await enviar_texto(telefono, "⚠️ No pude identificar el plan. Por favor selecciona uno de la lista o escribe *'Cancelar'*.")


    elif paso == "ESPERANDO_ELIMINAR_APIKEY":
        if id_interactivo and id_interactivo.startswith("delkey_"):
            key_id = int(id_interactivo.split("_")[1])
            correo = sesion["datos"].get("email")
            
            from kipu_api import solicitar_pin_auth
            resp = await solicitar_pin_auth(correo, telefono, "ELIMINAR_TOKEN", {"key_id": key_id})
            
            if resp.get("ok"):
                await enviar_texto(telefono, f"🗑️ Estás a punto de revocar una API Key.\n\nIngresa este PIN en la web de KIPU para confirmar la eliminación:\n\n*{resp['pin']}*")
            else:
                await enviar_texto(telefono, "⚠️ Hubo un error al generar el PIN de confirmación.")
            
            await eliminar_sesion(telefono) # Cerramos la sesión porque ya tiene el PIN
        else:
            await enviar_texto(telefono, "⚠️ Por favor selecciona una llave de la lista o escribe *Cancelar*.")
