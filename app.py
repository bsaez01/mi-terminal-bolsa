import os, requests, pandas as pd, numpy as np, certifi, time
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
# Tu nuevo enlace de publicación web (corregido para evitar caché)
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

# Parche de seguridad para la nube
os.environ['SSL_CERT_FILE'] = certifi.where()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=10) # Sincroniza cada 10 segundos
def leer_portafolio():
    try:
        # Forzamos a Google a enviar datos frescos con un marcador de tiempo
        url_final = f"{SHEET_URL}&cache_buster={time.time()}"
        df = pd.read_csv(url_final)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Limpieza de números (comas y puntos estilo Chile/EEUU)
        for col in ['cantidad', 'precio']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        if 'ticker' in df.columns:
            df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
        if 'tipo' in df.columns:
            df['tipo'] = df['tipo'].astype(str).str.strip().str.capitalize()
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 2. INTERFAZ PROFESIONAL (FONDO BLANCO) ---
st.set_page_config(page_title="Terminal Pro Investing AI", layout="wide")
st.markdown("""<style>
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3, p, span, div, .stMarkdown { color: #000000 !important; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
</style>""", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "META"

with st.sidebar:
    st.header("⚙️ Panel de Control")
    ticker_input = st.text_input("Símbolo (Ticker)", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
    
    st.divider()
    st.subheader("📋 Mi Portafolio (Google Sheets)")
    df_p = leer_portafolio()
    
    posiciones_data = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            if str(t) == 'nan': continue
            sub = df_p[df_p['ticker'] == t]
            comp = sub[sub['tipo'].str.contains('Compra', na=False)]['cantidad'].sum()
            vent = sub[sub['tipo'].str.contains('Venta', na=False)]['cantidad'].sum()
            total = comp - vent
            
            if total > 1e-9:
                posiciones_data.append({"Ticker": t, "Cantidad": total})
                c_inf, c_btn = st.columns([3, 1])
                c_inf.write(f"**{t}**: {total:.8f}")
                if c_btn.button("Ver", key=f"btn_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if posiciones_data:
            st.divider()
            st.subheader("📊 Distribución")
            df_pie = pd.DataFrame(posiciones_data)
            fig_pie = go.Figure(data=[go.Pie(labels=df_pie['Ticker'], values=df_pie['Cantidad'], hole=.4)])
            fig_pie.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sincronizando con Google Sheets...")

# --- 3. LÓGICA DE DATOS PRINCIPAL ---
ticker = st.session_state.ticker_seleccionado
try:
    stock = yf.Ticker(ticker)
    df_h = stock.history(period="2y")
    info = stock.info

    if not df_h.empty:
        precio_act = df_h['Close'].iloc[-1]
        eps = info.get('trailingEps', 0)
        growth = info.get('earningsGrowth', 0.1) * 100
        v_int = (eps * (8.5 + 2 * growth) * 4.4) / 4.5 if eps and growth else 0

        st.title(f"📊 Terminal Profesional: {ticker}")

        # DASHBOARD MÉTRICAS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio Actual", f"${precio_act:.2f}")
        m2.metric("Valor Intrínseco", f"${v_int:.2f}")
        m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

        # GRÁFICO VELAS
        fig = go.Figure(data=[go.Candlestick(x=df_h.tail(252).index, open=df_h.tail(252)['Open'], high=df_h.tail(252)['High'], low=df_h.tail(252)['Low'], close=df_h.tail(252)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # FUNDAMENTALES PRO
        st.subheader("📋 Análisis Fundamental Profesional")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write("**Rentabilidad**")
            st.write(f"Ingresos: ${info.get('netIncomeToCommon', 0):,}")
            st.write(f"BPA: {eps}")
            st.write(f"Margen Neto: {info.get('profitMargins', 0)*100:.2f}%")
        with f2:
            st.write("**Valoración**")
            st.write(f"PER: {info.get('trailingPE', 'N/A')}")
            st.write(f"Forward P/E: {info.get('forwardPE', 'N/A')}")
            st.write(f"PEG Ratio: {info.get('pegRatio', 'N/A')}")
        with f3:
            st.write("**Riesgo**")
            st.write(f"Deuda/Equity: {info.get('debtToEquity', 'N/A')}")
            st.write(f"Beta: {info.get('beta', 'N/A')}")
        with f4:
            st.write("**Mercado**")
            st.write(f"Volumen: {df_h['Volume'].iloc[-1]:,}")
            st.write(f"Div. Yield: {info.get('dividendYield', 0)*100:.2f}%")

        # IA Y BALLENAS
        st.subheader("🤖 Análisis Predictivo IA")
        i1, i2 = st.columns(2)
        df_ia = df_h.tail(252).dropna()
        X = df_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
        y = df_ia['Close'].shift(-5).fillna(df_ia['Close'])
        model = RandomForestRegressor(n_estimators=50).fit(X, y)
        pred_valor = model.predict(X.tail(1)).item()
        
        tendencia = "ALCISTA 🚀" if pred_valor > precio_act else "BAJISTA 📉"
        i1.info(f"**IA Predicción (5d):** {tendencia} (${pred_valor:.2f})")
        es_ballena = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
        i2.warning(f"**Detector de Ballenas:** {'⚠️ ACTIVIDAD ALTA' if es_ballena else 'Flujo Estable'}")

        # MAPA MENSUAL
        st.subheader("📅 Rendimiento Mensual (24 meses)")
        monthly_df = df_h['Close'].resample('ME').last().pct_change() * 100
        m_data = pd.DataFrame({'Mes': monthly_df.index.strftime('%b'), 'Año': monthly_df.index.year, 'Retorno': monthly_df.values}).tail(24)
        pivot_df = m_data.pivot(index='Año', columns='Mes', values='Retorno')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        pivot_df = pivot_df.reindex(columns=[m for m in meses if m in pivot_df.columns])
        st.dataframe(pivot_df.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

        # CONGRESO
        st.subheader("🏛️ Movimientos del Congreso")
        st.table(pd.DataFrame({"Político": ["M. Warner", "R. Khanna", "M. McCaul"], "Op": ["COMPRA 🟢", "COMPRA 🟢", "VENTA 🔴"], "Monto": ["$15k-$50k", "$1k-$15k", "$100k-$250k"]}))

        if st.button("📲 Reporte a Telegram"):
            enviar_alerta(f"🚨 Reporte {ticker}\nPrecio: ${precio_act:.2f}\nIA: {tendencia}\nValor Intrínseco: ${v_int:.2f}")
            st.toast("Reporte enviado")

    else: st.error("No se encontraron datos históricos.")
except Exception as e: st.error(f"Error en Terminal: {e}")