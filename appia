import os, shutil, certifi, requests, pandas as pd, numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN Y PARCHE ---
SHEET_URL = "https://google.com"
SHEET_ID = "1R9Jmk5Q781KcqJrkGkahojvGPnSKoYjX_LacmrrU6Wo"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

# Parche de seguridad para Windows
cert_folder = "C:\\TempCert"
if not os.path.exists(cert_folder): os.makedirs(cert_folder)
try:
    shutil.copy(certifi.where(), os.path.join(cert_folder, "cacert.pem"))
    os.environ['SSL_CERT_FILE'] = os.path.join(cert_folder, "cacert.pem")
except: pass

# --- 2. FUNCIONES DE GOOGLE SHEETS ---
def leer_portafolio():
    try:
        # Lee la hoja de Google directamente como un CSV
        return pd.read_csv(SHEET_URL)
    except:
        return pd.DataFrame(columns=['ticker', 'cantidad', 'precio', 'tipo', 'fecha'])

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

# --- 3. INTERFAZ ---
st.set_page_config(page_title="Terminal Pro AI Cloud", layout="wide")
st.markdown("<style>.stApp { background-color: #ffffff; color: #000000; }</style>", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "NVDA"

with st.sidebar:
    st.header("⚙️ Configuración")
    ticker_input = st.text_input("Símbolo", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
    
    st.divider()
    st.subheader("📋 Mi Portafolio en Google")
    df_port = leer_portafolio()
    
    posiciones = []
    if not df_port.empty:
        for t in df_port['ticker'].unique():
            sub = df_port[df_port['ticker'] == t]
            total = sub[sub['tipo']=='Compra']['cantidad'].sum() - sub[sub['tipo']=='Venta']['cantidad'].sum()
            if total > 1e-8:
                posiciones.append({"Ticker": t, "Cantidad": total})
                c_inf, c_btn = st.columns(2)
                c_inf.write(f"**{t}**: {total:.4f}")
                if c_btn.button("Ver", key=f"btn_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()

    if posiciones:
        st.divider()
        df_pie = pd.DataFrame(posiciones)
        fig_pie = go.Figure(data=[go.Pie(labels=df_pie['Ticker'], values=df_pie['Cantidad'], hole=.4)])
        fig_pie.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# --- 4. LÓGICA PRINCIPAL ---
ticker = st.session_state.ticker_seleccionado
try:
    stock = yf.Ticker(ticker)
    df_hist = stock.history(period="2y")
    df = df_hist.tail(252)
    info = stock.info

    if not df_hist.empty:
        precio_actual = df_hist['Close'].iloc[-1]
        st.title(f"📊 Terminal Profesional: {ticker}")

        # Dashboard y Gráfico (Igual que antes)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio Actual", f"${precio_actual:.2f}")
        m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # IA CON ESCUDO Y ALERTA AUTOMÁTICA
        st.subheader("🤖 Análisis Predictivo IA")
        df_ia = df.copy().dropna()
        X = df_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
        y = df_ia['Close'].shift(-5).fillna(df_ia['Close'])
        model = RandomForestRegressor(n_estimators=50).fit(X, y)
        pred_valor = model.predict(X.tail(1)).item()
        
        tendencia = "ALCISTA 🚀" if pred_valor > precio_actual else "BAJISTA 📉"
        st.info(f"**IA Predicción (5d):** {tendencia} (${pred_valor:.2f})")

        # MAPA MENSUAL
        st.subheader("📅 Rendimiento Mensual")
        monthly_df = df_hist['Close'].resample('ME').last().pct_change() * 100
        m_data = pd.DataFrame({'Mes': monthly_df.index.strftime('%b'), 'Año': monthly_df.index.year, 'Retorno': monthly_df.values}).tail(24)
        pivot_df = m_data.pivot(index='Año', columns='Mes', values='Retorno')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        pivot_df = pivot_df.reindex(columns=[m for m in meses if m in pivot_df.columns])
        st.dataframe(pivot_df.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

        # CONGRESO
        st.subheader("🏛️ Movimientos del Congreso")
        st.table(pd.DataFrame({"Político": ["M. Warner", "R. Khanna"], "Op": ["COMPRA", "COMPRA"], "Monto": ["$15k-50k", "$1k-15k"]}))

        # ALERTA AUTOMÁTICA (Si estás en la nube, esto te avisará)
        if st.button("📲 Probar Alerta Manual"):
            enviar_alerta(f"🚨 Reporte {ticker}\nPrecio: ${precio_actual:.2f}\nIA: {tendencia}")

    else: st.error("Sin datos.")
except Exception as e: st.error(f"Error: {e}")