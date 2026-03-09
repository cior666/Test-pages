import asyncio
import pandas as pd
import re
import os
from playwright.async_api import async_playwright

# 1. FUNCIÓN PARA LIMPIAR EMOJIS (ASCII Filtering)
def limpiar_texto(texto):
    if not texto: return ""
    # Eliminamos cualquier caracter que no sea estándar para un Excel limpio
    return re.sub(r'[^\x00-\x7F]+', '', texto).strip()

async def clasificar_comercio(rubro, ciudad):
    async with async_playwright() as p:
        # Iniciamos el navegador (puedes poner headless=True si no quieres ver la ventana)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Armado de URL y navegación inicial
        query = f"{rubro} en {ciudad}"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        await page.goto(url)
        await page.wait_for_timeout(5000)

        # --- SECCIÓN: SCROLL AUTOMÁTICO POR SELECTOR ---
        print(f"🚀 Iniciando barrido total de {rubro}...")
        panel_selector = 'div[role="feed"]'
        
        cant_anterior = 0
        intentos_sin_cambios = 0
        
        while True:
            # Forzamos el scroll directamente sobre el panel de resultados
            try:
                await page.locator(panel_selector).evaluate("el => el.scrollTop += 10000")
            except:
                print("⚠️ No se pudo encontrar el panel de scroll, intentando de nuevo...")
            
            await page.wait_for_timeout(3000) # Esperamos carga de datos
            
            locales_actuales = await page.query_selector_all('div[role="article"]')
            nueva_cantidad = len(locales_actuales)
            print(f"Buscando... cantidad en pantalla: {nueva_cantidad}")

            if nueva_cantidad <= cant_anterior:
                intentos_sin_cambios += 1
                if intentos_sin_cambios >= 5: # Confirmamos final real
                    print("🏁 Fin de la lista alcanzado.")
                    break
            else:
                cant_anterior = nueva_cantidad
                intentos_sin_cambios = 0 

        # --- SECCIÓN: PROCESAMIENTO DE DATOS ---
        lista_leads = []
        for local in locales_actuales:
            try:
                # Obtenemos nombre y limpiamos emojis
                nombre_raw = await local.get_attribute('aria-label')
                nombre = limpiar_texto(nombre_raw)
                
                # Clic para ver detalles
                await local.scroll_into_view_if_needed()
                await local.click()
                await page.wait_for_timeout(2000)

                # Captura de sitio web
                web_element = await page.query_selector('a[aria-label*="Sitio web"]')
                sitio_web = await web_element.get_attribute('href') if web_element else None

                es_prospecto = False
                estado = ""

                # Tu filtro estratégico de Facebook/Instagram
                if not sitio_web:
                    es_prospecto = True
                    estado = "Sin web"
                elif "facebook.com" in sitio_web.lower() or "instagram.com" in sitio_web.lower():
                    es_prospecto = True
                    estado = "Solo redes sociales"
                
                if es_prospecto:
                    try:
                        dir_raw = await page.inner_text('button[data-item-id="address"]')
                        direccion = limpiar_texto(dir_raw)
                    except: direccion = "S/D"

                    try:
                        tel_raw = await page.inner_text('button[data-item-id^="phone"]')
                        telefono = limpiar_texto(tel_raw)
                    except: telefono = "S/D"

                    lista_leads.append({
                        "RUBRO": rubro.upper(),
                        "NOMBRE": nombre,
                        "DIRECCIÓN": direccion,
                        "MAIL": "", # Para completar a mano
                        "TELÉFONO": telefono,
                        "ESTADO": estado
                    })
                    print(f"🎯 Guardado: {nombre}")

            except Exception:
                continue

        # --- SECCIÓN: GUARDADO INTELIGENTE (PANDAS) ---
        archivo = "Hunteds.xlsx"
        df_nuevo = pd.DataFrame(lista_leads)

        if os.path.exists(archivo):
            # Leemos lo que ya tienes y le sumamos lo nuevo
            df_existente = pd.read_excel(archivo)
            # El secreto: borramos duplicados basados en el nombre del negocio
            df_final = pd.concat([df_existente, df_nuevo]).drop_duplicates(subset=["NOMBRE"], keep='first')
            print("📈 Actualizando Excel sin repetir clientes...")
        else:
            df_final = df_nuevo
            print("🆕 Creando nuevo archivo Excel...")

        df_final.to_excel(archivo, index=False)
        print(f"🔥 ¡Proceso finalizado! Total en lista: {len(df_final)}")
        await browser.close()

# MODIFICA AQUÍ EL RUBRO Y LA CIUDAD
asyncio.run(clasificar_comercio("Veterinarias 24hs", "Santo Tomé"))