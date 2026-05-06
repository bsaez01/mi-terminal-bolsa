import os, requests, pandas as pd, numpy as np, certifi, io, time
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN ---
# Tu URL de publicación web (CSV)
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

# Forzamos certificados para evitar errores SSL en la nube
os.environ['SSL_CERT_FILE'] = certifi.where()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=10)
def leer_portafolio():
    try:
        # Engañamos al servidor para que parezca un navegador real (evita bloqueos)
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Añadimos un número al azar al final para que Google siempre mande datos nuevos
        response = requests.get(f"{SHEET_URL}&cb={time.time()}", headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Limpiamos nombres de columnas (quita espacios y pone minúsculas)
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Limpieza de números (8 decimales y comas latinas)
            for col in ['cantidad', 'precio']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            if 'ticker' in df.columns:
                df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
            if 'tipo' in df.columns:
                df['tipo'] = df['tipo'].astype(str).str.strip().str.capitalize()
            return df
        return pd.DataFrame()
    except Exception as e:
        # Si hay error, lo mostramos brevemente para saber qué es
        st.sidebar.error(f"Error de red: {e}")
        return pd.DataFrame()

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
    st.subheader("📋 Mi Portafolio (Cloud)")
    df_p = leer_portafolio()
    
    posiciones_validas = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            if str(t) == 'NAN' or t == "": continue
            sub = df_p[df_p['ticker'] == t]
            compra = sub[sub['tipo'].str.contains('Compra', na=False, case=False)]['cantidad'].sum()
            venta = sub[sub['tipo'].str.contains('Venta', na=False, case=False)]['cantidad'].sum()
            total = compra - venta
            if total > 1e-9:
                posiciones_validas.append({"Ticker": t, "Cantidad": total})
                c_inf, c_btn = st.columns([3, 1]) # Definimos proporción para que no de error
                c_inf.write(f"**{t}**: {total:.4f}")
                if c_btn.button("Ver", key=f"btn_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if posiciones_validas:
            st.divider()
            df_pie = pd.DataFrame(posiciones_validas)
            fig_p = go.Figure(data=[go.Pie(labels=df_pie['Ticker'], values=df_pie['Cantidad'], hole=.4)])
            fig_p.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("Escribe tus datos en la hoja de Google...")

# --- 3. LÓGICA DE MERCADO ---
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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio Actual", f"${precio_act:.2f}")
        m2.metric("V. Intrínseco", f"${v_int:.2f}")
        m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

        fig = go.Figure(data=[go.Candlestick(x=df_h.tail(252).index, open=df_h.tail(252)['Open'], high=df_h.tail(252)['High'], low=df_h.tail(252)['Low'], close=df_h.tail(252)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Análisis Fundamental")
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
        es_ballena = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
        i2.warning(f"**Flujo Ballenas:** {'⚠️ ACTIVIDAD ALTA' if es_ballena else 'Estable'}")

        st.subheader("📅 Rendimiento Mensual")
        m_df = df_h['Close'].resample('ME').last().pct_change() * 100
        m_p = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).tail(24)
        pivot_df = m_p.pivot(index='Año', columns='Mes', values='Val')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        pivot_df = pivot_df.reindex(columns=[m for m in meses if m in pivot_df.columns])
        st.dataframe(pivot_df.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

        st.subheader("🏛️ Movimientos del Congreso")
        st.table(pd.DataFrame({"Político": ["Mark Warner", "Ro Khanna"], "Op": ["COMPRA 🟢", "COMPRA 🟢"], "Monto": ["$15k-$50k", "$1k-$15k"]}))

        if st.button("📲 Reporte a Telegram"):
            enviar_alerta(f"🚨 Terminal Pro: {ticker}\nPrecio: ${precio_act:.2f}\nIA: {pred:.2f}")

    else: st.error("No hay datos históricos.")
except Exception as e: st.error(f"Error: {e}")