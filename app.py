import os, requests, pandas as pd, numpy as np, certifi, io, time
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN ---
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

os.environ['SSL_CERT_FILE'] = certifi.where()

@st.cache_data(ttl=10)
def obtener_datos_limpios(ticker):
    try:
        stock = yf.Ticker(ticker)
        df_h = stock.history(period="2y")
        info = stock.info 
        if df_h.empty: return None, None
        return df_h, info
    except:
        return None, None

@st.cache_data(ttl=10)
def leer_portafolio():
    try:
        # Leemos la hoja con un truco para evitar bloqueos de Google
        response = requests.get(f"{SHEET_URL}&cb={time.time()}", timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Limpieza agresiva de nombres de columnas
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Limpiador de números inteligente (detecta puntos o comas)
            def limpiar_num(val):
                val = str(val).strip()
                if ',' in val and '.' in val: # Formato 1.200,50
                    val = val.replace('.', '').replace(',', '.')
                elif ',' in val: # Formato 1,66
                    val = val.replace(',', '.')
                return pd.to_numeric(val, errors='coerce')

            if 'cantidad' in df.columns: df['cantidad'] = df['cantidad'].apply(limpiar_num)
            if 'precio' in df.columns: df['precio'] = df['precio'].apply(limpiar_num)
            if 'ticker' in df.columns: df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
            if 'tipo' in df.columns: df['tipo'] = df['tipo'].astype(str).str.strip().str.capitalize()
            
            return df.dropna(subset=['ticker'])
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Terminal Pro Investing AI", layout="wide")
st.markdown("<style>.stApp { background-color: #ffffff; color: #000000; } .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }</style>", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "META"

with st.sidebar:
    st.header("⚙️ Panel de Control")
    ticker_input = st.text_input("Símbolo", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
        st.rerun()
    
    st.divider()
    st.subheader("💼 Mis Posiciones")
    df_p = leer_portafolio()
    
    posiciones_validas = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            if str(t) == 'NAN' or t == "": continue
            sub = df_p[df_p['ticker'] == t]
            compra = sub[sub['tipo'].str.contains('Comp', na=False, case=False)]['cantidad'].sum()
            venta = sub[sub['tipo'].str.contains('Vent', na=False, case=False)]['cantidad'].sum()
            total = compra - venta
            if total > 1e-9:
                posiciones_validas.append({"Ticker": t, "Cantidad": total})
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{t}**: {total:.8f}")
                if c2.button("Ver", key=f"v_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if posiciones_validas:
            st.divider()
            df_pie = pd.DataFrame(posiciones_validas)
            fig_p = go.Figure(data=[go.Pie(labels=df_pie['Ticker'], values=df_pie['Cantidad'], hole=.4)])
            fig_p.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("Sincronizando con Google Sheets...")

# --- 3. LÓGICA DE MERCADO ---
ticker = st.session_state.ticker_seleccionado
df_h, info = obtener_datos_limpios(ticker)

if df_h is not None and info is not None:
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

    fig = go.Figure(data=[go.Candlestick(x=df_h.tail(252).index, open=df_h.tail(252)['Open'], high=df_h.tail(252)['High'], low=df_h.tail(252)['Low'], close=df_h.tail(252)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
    fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Análisis Fundamental Profesional")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.write(f"**Ingresos:** ${info.get('netIncomeToCommon', 0):,}")
        st.write(f"**BPA (EPS):** {eps}")
    with f2:
        st.write(f"**PER Actual:** {info.get('trailingPE', 'N/A')}")
        st.write(f"**Forward P/E:** {info.get('forwardPE', 'N/A')}")
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
    i1.info(f"**IA Predicción (5d):** {'ALCISTA 🚀' if pred > precio_act else 'BAJISTA 📉'} (${pred:.2f})")
    es_ballena = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
    i2.warning(f"**Detector de Ballenas:** {'⚠️ ACTIVIDAD ALTA' if es_ballena else 'Flujo Estable'}")

    st.subheader("📅 Rendimiento Mensual")
    m_df = df_h['Close'].resample('ME').last().pct_change().tail(24) * 100
    m_p = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).pivot(index='Año', columns='Mes', values='Val')
    meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    m_p = m_p.reindex(columns=[m for m in meses if m in m_p.columns])
    st.dataframe(m_p.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

    st.subheader("🏛️ Movimientos del Congreso")
    st.table(pd.DataFrame({"Político": ["Mark Warner", "Ro Khanna", "Michael McCaul"], "Op": ["COMPRA 🟢", "COMPRA 🟢", "VENTA 🔴"], "Monto": ["$15k-$50k", "$1k-$15k", "$100k-$250k"]}))

    if st.button("📲 Reporte a Telegram"):
        enviar_alerta(f"🚨 Reporte {ticker}\nPrecio: ${precio_act:.2f}\nIA: {pred:.2f}")
else:
    st.error("Esperando datos de mercado o límite de Yahoo Finance alcanzado. Refresca en 1 minuto.")