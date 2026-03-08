import streamlit as st
import pandas as pd
import time
import os
import io
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. CONFIGURACIÓN Y ESTILOS VISUALES (CSS) ---
st.set_page_config(page_title="Lead Hunter Pro", layout="centered")

# Estilos para que los resultados parezcan tarjetas de una App
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em; 
        background-color: #FF4B4B; 
        color: white; 
        font-weight: bold;
        border: none;
    }
    .lead-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 6px solid #FF4B4B;
        color: #1f1f1f;
    }
    .lead-card h3 { margin-top: 0; color: #d32f2f; font-size: 1.3em; }
    .call-button {
        display: block;
        padding: 12px;
        background-color: #25D366;
        color: white !important;
        text-decoration: none;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
        margin-top: 15px;
        font-size: 1.1em;
    }
    .status-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85em;
        font-weight: bold;
        background-color: #ffebee;
        color: #c62828;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTERFAZ DE USUARIO ---
st.title("🎯 Lead Hunter Pro")
st.markdown("Busca negocios en Google Maps que necesitan una página web.")

with st.sidebar:
    st.header("Configuración")
    rubro = st.text_input("Rubro", placeholder="Ej: Veterinaria")
    depto = st.text_input("Ciudad / Depto", placeholder="Ej: Paysandú")
    limite = st.slider("Locales a analizar", 5, 50, 15)
    st.divider()
    btn_buscar = st.button("🚀 INICIAR BÚSQUEDA")

# --- 3. LÓGICA DEL BOT (EXTRACCIÓN) ---
def ejecutar_escaneo(rubro, depto, limite):
    opts = Options()
    opts.add_argument("--headless")  # Obligatorio para servidores
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    
    # Compatibilidad con Linux (Streamlit Cloud / Railway)
    if os.path.exists("/usr/bin/chromium"):
        opts.binary_location = "/usr/bin/chromium"

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        
        # Búsqueda en Google Maps
        query = f"{rubro} en {depto}"
        driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        time.sleep(5)

        leads = []
        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        
        progreso = st.progress(0)
        status = st.empty()

        for i, el in enumerate(elementos[:limite]):
            progreso.progress((i + 1) / min(len(elementos), limite))
            try:
                el.click()
                time.sleep(2.5)
                
                nombre = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text
                status.text(f"Analizando: {nombre}...")

                # Extraer Teléfono
                try:
                    tel_el = driver.find_element(By.CSS_SELECTOR, "[data-tooltip='Copiar el número de teléfono']")
                    tel = tel_el.get_attribute("aria-label").replace("Teléfono: ", "")
                except:
                    tel = "No disponible"

                # Lógica de Prospecto (CORREGIDA)
                es_prospecto = False
                nota = ""
                try:
                    # Línea corregida para evitar el SyntaxError
                    web_btn = driver.find_element(By.CSS_SELECTOR, "a[aria-label*='Sitio web']")
                    web_url = web_btn.get_attribute("href").lower()
                    
                    # Si tiene web pero es solo una red social, nos interesa
                    redes = ["facebook.com", "instagram.com", "linktr.ee", "whatsapp.com", "twitter.com"]
                    if any(red in web_url for red in redes):
                        es_prospecto = True
                        nota = "Solo redes sociales"
                except:
                    # Si no hay botón de sitio web, es un prospecto perfecto
                    es_prospecto = True
                    nota = "Sin sitio web"

                if es_prospecto:
                    leads.append({
                        "nombre": nombre,
                        "tel": tel,
                        "nota": nota
                    })
            except:
                continue
        
        driver.quit()
        status.empty()
        return leads
    except Exception as e:
        st.error(f"Error en el navegador: {e}")
        return []

# --- 4. PRESENTACIÓN DE RESULTADOS ---
if btn_buscar:
    if rubro and depto:
        with st.spinner(f"Escaneando {rubro} en {depto}..."):
            resultados = ejecutar_escaneo(rubro, depto, limite)
            
        if resultados:
            st.success(f"¡Se encontraron {len(resultados)} prospectos calificados!")
            
            for lead in resultados:
                # Limpiar el teléfono para el enlace tel:
                tel_link = lead['tel'].replace(" ", "").replace("-", "")
                
                # Diseño de Tarjeta HTML
                st.markdown(f"""
                    <div class="lead-card">
                        <span class="status-tag">{lead['nota']}</span>
                        <h3>📍 {lead['nombre']}</h3>
                        <p><b>Teléfono:</b> {lead['tel']}</p>
                        <a href="tel:{tel_link}" class="call-button">📞 LLAMAR AHORA</a>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Opción de descargar todo en Excel/CSV
            df = pd.DataFrame(resultados)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Descargar lista (CSV)", csv, f"leads_{depto}.csv", "text/csv")
        else:
            st.info("No se encontraron locales que cumplan los requisitos en esta zona.")
    else:
        st.error("Por favor completa los campos 'Rubro' y 'Ciudad'.")
