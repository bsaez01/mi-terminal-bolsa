import os, shutil, certifi, requests, pandas as pd, numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- CONFIGURACIÓN ---
SHEET_ID = "1R9Jmk5Q781KcqJrkGkahojvGPnSKoYjX_LacmrrU6Wo"
SHEET_URL = f"https://google.com{SHEET_ID}/export?format=csv"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

@st.cache_data(ttl=15)
def leer_portafolio():
    try:
        # Leemos el CSV de Google
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        
        # PARCHE DE PRECISIÓN: Limpia comas/puntos y fuerza 8 decimales
        for col in ['cantidad', 'precio']:
            if col in df.columns:
                # Convertimos a string, quitamos puntos de miles, cambiamos coma decimal por punto
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                # Convertimos a número flotante de alta precisión
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'tipo' in df.columns:
            df['tipo'] = df['tipo'].str.strip().str.capitalize()
        return df
    except:
        return pd.DataFrame()

# --- INTERFAZ ---
st.set_page_config(page_title="Terminal Pro AI Precisión", layout="wide")
st.markdown("<style>.stApp { background-color: #ffffff; color: #000000; }</style>", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "META"

with st.sidebar:
    st.header("⚙️ Configuración")
    ticker_input = st.text_input("Símbolo", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
    
    st.divider()
    st.subheader("📋 Mi Portafolio (Alta Precisión)")
    df_p = leer_portafolio()
    
    posiciones = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            sub = df_p[df_p['ticker'] == t]
            comp = sub[sub['tipo'] == 'Compra']['cantidad'].sum()
            vent = sub[sub['tipo'] == 'Venta']['cantidad'].sum()
            total = comp - vent
            
            if total > 1e-9:
                posiciones.append({"Ticker": t, "Cantidad": total})
                c_inf, c_btn = st.columns([3, 1])
                # FORZAMOS VISUALIZACIÓN DE 8 DECIMALES AQUÍ
                c_inf.write(f"**{t}**: {total:.8f}")
                if c_btn.button("Ver", key=f"v_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
    else:
        st.info("Sincronizando con Google Sheets...")

# --- LÓGICA PRINCIPAL ---
ticker = st.session_state.ticker_seleccionado
try:
    stock = yf.Ticker(ticker)
    df_h = stock.history(period="2y")
    if not df_h.empty:
        precio_act = df_h['Close'].iloc[-1]
        st.title(f"📊 Terminal: {ticker}")
        
        # Gráfico
        fig = go.Figure(data=[go.Candlestick(x=df_h.tail(200).index, open=df_h.tail(200)['Open'], high=df_h.tail(200)['High'], low=df_h.tail(200)['Low'], close=df_h.tail(200)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # IA
        st.subheader("🤖 Análisis IA")
        d_ia = df_h.tail(252).dropna()
        X = d_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
        y = d_ia['Close'].shift(-5).fillna(d_ia['Close'])
        model = RandomForestRegressor(n_estimators=50).fit(X, y)
        p_val = model.predict(X.tail(1)).item()
        st.info(f"Predicción 5 días: {'ALCISTA 🚀' if p_val > precio_act else 'BAJISTA 📉'} (${p_val:.2f})")

        # Tabla Mensual
        st.subheader("📅 Rendimiento Mensual")
        m_df = df_h['Close'].resample('ME').last().pct_change().tail(24) * 100
        m_p = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).pivot(index='Año', columns='Mes', values='Val')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        m_p = m_p.reindex(columns=[m for m in meses if m in m_p.columns])
        st.dataframe(m_p.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"};').format("{:.1f}%", na_rep="-"), use_container_width=True)

    else: st.error("No hay datos.")
except Exception as e: st.error(f"Error: {e}")