import os, requests, pandas as pd, numpy as np, certifi, io, time
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN ---
# Tu enlace de publicación CSV verificado
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

os.environ['SSL_CERT_FILE'] = certifi.where()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=10)
def obtener_datos_mercado(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        return df, stock.info
    except: return None, None

@st.cache_data(ttl=5)
def leer_portafolio():
    try:
        # Petición directa con User-Agent para evitar bloqueos
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(SHEET_URL, headers=headers, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Limpiador de números (8 decimales y comas)
            def limpia(v):
                s = str(v).strip().replace(',', '.')
                try: return float(s)
                except: return 0.0

            if 'cantidad' in df.columns: df['cantidad'] = df['cantidad'].apply(limpia)
            if 'precio' in df.columns: df['precio'] = df['precio'].apply(limpia)
            if 'ticker' in df.columns: df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
            if 'tipo' in df.columns: df['tipo'] = df['tipo'].astype(str).str.lower().str.strip()
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Terminal Pro Investing AI", layout="wide")
st.markdown("<style>.stApp { background-color: #ffffff; color: #000000; } .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }</style>", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "META"

with st.sidebar:
    st.header("⚙️ Panel de Control")
    t_input = st.text_input("Símbolo", value=st.session_state.ticker_seleccionado).upper()
    if t_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = t_input
        st.rerun()
    
    st.divider()
    st.subheader("💼 Mis Posiciones")
    df_p = leer_portafolio()
    
    if not df_p.empty and 'ticker' in df_p.columns:
        pos_v = []
        for t in df_p['ticker'].unique():
            if str(t) in ['NAN', '', 'nan']: continue
            sub = df_p[df_p['ticker'] == t]
            total = sub[sub['tipo'].str.contains('comp', na=False)]['cantidad'].sum() - \
                    sub[sub['tipo'].str.contains('vent', na=False)]['cantidad'].sum()
            
            if total > 1e-8:
                pos_v.append({"T": t, "C": total})
                c1, c2 = st.columns([3, 1]) # Proporción corregida
                c1.write(f"**{t}**: {total:.8f}")
                if c2.button("Ver", key=f"v_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if pos_v:
            st.divider()
            df_pie = pd.DataFrame(pos_v)
            st.plotly_chart(go.Figure(data=[go.Pie(labels=df_pie['T'], values=df_pie['C'], hole=.4)]).update_layout(height=200, showlegend=False, margin=dict(t=0,b=0,l=0,r=0)), use_container_width=True)
    else:
        st.info("Sincronizando con Google Sheets...")

# --- 3. LÓGICA DE MERCADO ---
ticker = st.session_state.ticker_seleccionado
df_h, info = obtener_datos_mercado(ticker)

if df_h is not None and not df_h.empty:
    precio_act = df_h['Close'].iloc[-1]
    eps = info.get('trailingEps', 0)
    growth = info.get('earningsGrowth', 0.1) * 100
    v_int = (eps * (8.5 + 2 * growth) * 4.4) / 4.5 if eps and growth else 0

    st.title(f"📊 Terminal Profesional: {ticker}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Actual", f"${precio_act:.2f}")
    m2.metric("V. Intrínseco", f"${v_int:.2f}")
    m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
    m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

    st.plotly_chart(go.Figure(data=[go.Candlestick(x=df_h.tail(200).index, open=df_h.tail(200)['Open'], high=df_h.tail(200)['High'], low=df_h.tail(200)['Low'], close=df_h.tail(200)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')]).update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False), use_container_width=True)

    st.subheader("📋 Análisis Fundamental Profesional")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.write(f"**Ingresos:** ${info.get('netIncomeToCommon', 0):,}")
        st.write(f"**BPA (EPS):** {eps}")
    with f2:
        st.write(f"**PER:** {info.get('trailingPE', 'N/A')}")
        st.write(f"**PEG Ratio:** {info.get('pegRatio', 'N/A')}")
    with f3:
        st.write(f"**Deuda/Equity:** {info.get('debtToEquity', 'N/A')}")
        st.write(f"**Beta:** {info.get('beta', 'N/A')}")
    with f4:
        st.write(f"**Volumen:** {df_h['Volume'].iloc[-1]:,}")
        st.write(f"**Div. Yield:** {info.get('dividendYield', 0)*100:.2f}%")

    st.subheader("🤖 IA & Flujo Institucional")
    i1, i2 = st.columns(2)
    d_ia = df_h.tail(252).dropna()
    X = d_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
    y = d_ia['Close'].shift(-5).fillna(d_ia['Close'])
    model = RandomForestRegressor(n_estimators=50).fit(X, y)
    pred = model.predict(X.tail(1)).item()
    i1.info(f"**IA Predicción (5d):** {'ALCISTA' if pred > precio_act else 'BAJISTA'} (${pred:.2f})")
    es_b = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
    i2.warning(f"**Detector Ballenas:** {'⚠️ ACTIVIDAD ALTA' if es_b else 'Estable'}")

    st.subheader("📅 Rendimiento Mensual")
    m_df = df_h['Close'].resample('ME').last().pct_change().tail(24) * 100
    m_p = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).pivot(index='Año', columns='Mes', values='Val')
    meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    m_p = m_p.reindex(columns=[m for m in meses if m in m_p.columns])
    st.dataframe(m_p.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

    st.subheader("🏛️ Movimientos del Congreso")
    st.table(pd.DataFrame({"Político": ["Mark Warner", "Ro Khanna"], "Op": ["COMPRA", "COMPRA"], "Monto": ["$15k-50k", "$1k-15k"]}))

    if st.button("📲 Notificar Telegram"):
        enviar_alerta(f"🚨 Reporte {ticker}: ${precio_act:.2f}. IA Predice: ${pred:.2f}")

else: st.error("Límite de Yahoo Finance alcanzado. Refresca en 1 minuto.")