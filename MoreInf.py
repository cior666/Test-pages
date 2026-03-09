import asyncio
import pandas as pd
import os
import re
from playwright.async_api import async_playwright

def limpiar_numero(texto):
    if not texto: return "0"
    nums = re.findall(r'\d+', texto)
    return "".join(nums) if nums else "0"

async def enriquecer_datos():
    archivo = "Hunteds.xlsx"
    
    if not os.path.exists(archivo):
        print(f"❌ No se encontró el archivo {archivo}.")
        return

    df = pd.read_excel(archivo)
    
    # Nos aseguramos de que las columnas existan en el DataFrame antes de empezar
    for col in ['PUNTAJE', 'RESEÑAS', 'CANTIDAD DE VOTANTES']:
        if col not in df.columns:
            df[col] = None

    print(f"📖 Analizando {len(df)} locales en total...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        for index, row in df.iterrows():
            # LÓGICA CORRECTA: Verificamos si la CELDA actual está vacía
            # Si PUNTAJE es nulo o "S/P", significa que hay que buscarlo
            if pd.notnull(row.get("PUNTAJE")) and row.get("PUNTAJE") != "S/P":
                continue

            nombre = str(row['NOMBRE'])
            direccion = str(row['DIRECCIÓN'])
            search_query = f"{nombre} {direccion}"
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            
            print(f"🔎 Enriqueciendo datos para: {nombre}...")
            
            try:
                await page.goto(url)
                await page.wait_for_timeout(4500)

                try:
                    rating_selector = await page.query_selector('span[role="img"]')
                    info_raw = await rating_selector.get_attribute('aria-label') if rating_selector else ""
                    
                    if info_raw:
                        partes = info_raw.split(" ")
                        puntaje = partes[0]  
                        votos_limpios = limpiar_numero(partes[-2]) 
                        
                        df.at[index, 'PUNTAJE'] = puntaje 
                        df.at[index, 'RESEÑAS'] = f"{votos_limpios} reseñas"
                        df.at[index, 'CANTIDAD DE VOTANTES'] = int(votos_limpios)
                    else:
                        df.at[index, 'PUNTAJE'] = "S/P"
                        df.at[index, 'RESEÑAS'] = "0 reseñas"
                        df.at[index, 'CANTIDAD DE VOTANTES'] = 0
                except:
                    df.at[index, 'PUNTAJE'] = "S/P"
                    df.at[index, 'RESEÑAS'] = "N/A"
                    df.at[index, 'CANTIDAD DE VOTANTES'] = 0

                print(f"   ⭐ {df.at[index, 'PUNTAJE']} | 👥 {df.at[index, 'CANTIDAD DE VOTANTES']} votantes")

            except Exception:
                continue

        # Guardamos el archivo con todos los datos (viejos y nuevos)
        df.to_excel(archivo, index=False)
        print(f"\n✅ ¡Actualización finalizada! Se procesaron todos los locales pendientes.")
        await browser.close()

asyncio.run(enriquecer_datos())