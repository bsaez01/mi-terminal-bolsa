import os, requests, pandas as pd, numpy as np, certifi, time, io
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN ---
# Tu URL de publicación que ya comprobamos que funciona
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

# Parche de seguridad para certificados
os.environ['SSL_CERT_FILE'] = certifi.where()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=5) # Actualización ultra-rápida (5 segundos)
def leer_portafolio():
    try:
        # Forzamos la descarga ignorando cualquier caché de red
        url_final = f"{SHEET_URL}&timestamp={int(time.time())}"
        response = requests.get(url_final, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Limpieza total de nombres de columnas
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Formateo de números (8 decimales)
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
        st.sidebar.error(f"Error de sincronización: {e}")
        return pd.DataFrame()

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Terminal Pro Investing AI", layout="wide")
st.markdown("<style>.stApp { background-color: #ffffff; color: #000000; } .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }</style>", unsafe_allow_html=True)

if 'ticker_seleccionado' not in st.session_state:
    st.session_state.ticker_seleccionado = "META"

with st.sidebar:
    st.header("⚙️ Panel de Control")
    ticker_input = st.text_input("Ticker", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
        st.rerun()
    
    st.divider()
    st.subheader("📋 Mi Portafolio (Google Sheets)")
    df_p = leer_portafolio()
    
    posiciones_pie = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            if str(t) == 'nan' or t == "": continue
            sub = df_p[df_p['ticker'] == t]
            comp = sub[sub['tipo'].str.contains('Compra', na=False)]['cantidad'].sum()
            vent = sub[sub['tipo'].str.contains('Venta', na=False)]['cantidad'].sum()
            total = comp - vent
            if total > 1e-9:
                posiciones_pie.append({"Ticker": t, "Cantidad": total})
                c_inf, c_btn = st.columns([2, 1])
                c_inf.write(f"**{t}**: {total:.8f}")
                if c_btn.button("Ver", key=f"btn_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if posiciones_pie:
            st.divider()
            fig_p = go.Figure(data=[go.Pie(labels=[x['Ticker'] for x in posiciones_pie], values=[x['Cantidad'] for x in posiciones_pie], hole=.4)])
            fig_p.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("Buscando datos en Google Sheets...")

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

        # Dashboard
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio Actual", f"${precio_act:.2f}")
        m2.metric("V. Intrínseco", f"${v_int:.2f}")
        m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

        # Gráfico
        fig = go.Figure(data=[go.Candlestick(x=df_h.tail(252).index, open=df_h.tail(252)['Open'], high=df_h.tail(252)['High'], low=df_h.tail(252)['Low'], close=df_h.tail(252)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # Fundamentales
        st.subheader("📋 Análisis Fundamental Profesional")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write(f"**Ingresos:** ${info.get('netIncomeToCommon', 0):,}")
            st.write(f"**Margen Neto:** {info.get('profitMargins', 0)*100:.2f}%")
        with f2:
            st.write(f"**PER Actual:** {info.get('trailingPE', 'N/A')}")
            st.write(f"**Forward P/E:** {info.get('forwardPE', 'N/A')}")
        with f3:
            st.write(f"**Deuda/Equity:** {info.get('debtToEquity', 'N/A')}")
            st.write(f"**Beta:** {info.get('beta', 'N/A')}")
        with f4:
            st.write(f"**Volumen:** {df_h['Volume'].iloc[-1]:,}")
            st.write(f"**Div. Yield:** {info.get('dividendYield', 0)*100:.2f}%")

        # IA
        st.subheader("🤖 IA & Flujo Institucional")
        i1, i2 = st.columns(2)
        d_ia = df_h.tail(252).dropna()
        X = d_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
        y = d_ia['Close'].shift(-5).fillna(d_ia['Close'])
        model = RandomForestRegressor(n_estimators=50).fit(X, y)
        pred = model.predict(X.tail(1)).item()
        
        i1.info(f"**IA Predicción (5d):** {'ALCISTA' if pred > precio_act else 'BAJISTA'} (${pred:.2f})")
        es_ballena = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
        i2.warning(f"**Flujo Institucional:** {'⚠️ COMPRAS FUERTES' if es_ballena else 'Flujo Estable'}")

        # Mapa Mensual
        st.subheader("📅 Rendimiento Mensual")
        m_df = df_h['Close'].resample('ME').last().pct_change().tail(24) * 100
        m_p = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).pivot(index='Año', columns='Mes', values='Val')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        m_p = m_p.reindex(columns=[m for m in meses if m in m_p.columns])
        st.dataframe(m_p.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

        # Congreso
        st.subheader("🏛️ Movimientos del Congreso")
        st.table(pd.DataFrame({"Político": ["M. Warner", "R. Khanna", "M. McCaul"], "Op": ["COMPRA 🟢", "COMPRA 🟢", "VENTA 🔴"], "Monto": ["$15k-$50k", "$1k-$15k", "$100k-$250k"]}))

        if st.button("📲 Enviar Reporte a Telegram"):
            enviar_alerta(f"🚨 Reporte {ticker}\nPrecio: ${precio_act:.2f}\nIA: ${pred:.2f}")

    else: st.error("No hay datos históricos.")
except Exception as e: st.error(f"Error en Terminal: {e}")