import os, requests, pandas as pd, numpy as np, certifi, io, time
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

# --- 1. CONFIGURACIÓN ---
# Tu enlace de publicación que ya verificamos que conecta bien
SHEET_URL = "https://google.com"
TOKEN = "8627985111:AAHRXCMzkTFeL_k3au9pqw6dNhHBljBFVFQ"
CHAT_ID = "8702457652"

# Parche de seguridad para certificados en la nube
os.environ['SSL_CERT_FILE'] = certifi.where()

def enviar_alerta(mensaje):
    url = f"https://telegram.org{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={mensaje}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=10)
def leer_portafolio():
    try:
        # Forzamos la descarga ignorando caché de red
        response = requests.get(f"{SHEET_URL}&cb={time.time()}", timeout=10)
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
                # Detectamos compra o venta sin importar mayúsculas
                df['tipo_clean'] = df['tipo'].astype(str).str.lower().str.strip()
                df.loc[df['tipo_clean'].str.contains('comp', na=False), 'tipo'] = 'Compra'
                df.loc[df['tipo_clean'].str.contains('vent', na=False), 'tipo'] = 'Venta'
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- 2. INTERFAZ PROFESIONAL ---
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
    ticker_input = st.text_input("Ticker", value=st.session_state.ticker_seleccionado).upper()
    if ticker_input != st.session_state.ticker_seleccionado:
        st.session_state.ticker_seleccionado = ticker_input
        st.rerun()
    
    st.divider()
    st.subheader("📋 Mi Portafolio (Cloud)")
    df_p = leer_portafolio()
    
    posiciones_validas = []
    if not df_p.empty and 'ticker' in df_p.columns:
        for t in df_p['ticker'].unique():
            if str(t) in ['NAN', '', 'None', 'nan']: continue
            sub = df_p[df_p['ticker'] == t]
            compra = sub[sub['tipo'] == 'Compra']['cantidad'].sum()
            venta = sub[sub['tipo'] == 'Venta']['cantidad'].sum()
            total = compra - venta
            
            if total > 1e-9:
                posiciones_validas.append({"Ticker": t, "Cantidad": total})
                # Definimos 2 columnas con proporción 2:1
                c_inf, c_btn = st.columns([2, 1])
                c_inf.write(f"**{t}**: {total:.8f}")
                if c_btn.button("Ver", key=f"btn_{t}"):
                    st.session_state.ticker_seleccionado = t
                    st.rerun()
        
        if posiciones_validas:
            st.divider()
            fig_pie = go.Figure(data=[go.Pie(labels=[x['Ticker'] for x in posiciones_validas], values=[x['Cantidad'] for x in posiciones_validas], hole=.4)])
            fig_pie.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Escribe tus datos en la hoja de Google.")

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

        # MÉTRICAS PRINCIPALES
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Precio Actual", f"${precio_act:.2f}")
        m2.metric("V. Intrínseco", f"${v_int:.2f}")
        m3.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        m4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

        # GRÁFICO DE VELAS
        fig = go.Figure(data=[go.Candlestick(x=df_h.tail(252).index, open=df_h.tail(252)['Open'], high=df_h.tail(252)['High'], low=df_h.tail(252)['Low'], close=df_h.tail(252)['Close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_white", height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # ANÁLISIS FUNDAMENTAL PROFESIONAL (RESTAURADO)
        st.subheader("📋 Análisis Fundamental Profesional")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write("**Rentabilidad**")
            st.write(f"Ingresos: ${info.get('netIncomeToCommon', 0):,}")
            st.write(f"BPA (EPS): {eps}")
            st.write(f"Margen Neto: {info.get('profitMargins', 0)*100:.2f}%")
        with f2:
            st.write("**Valoración**")
            st.write(f"PER Actual: {info.get('trailingPE', 'N/A')}")
            st.write(f"Forward P/E: {info.get('forwardPE', 'N/A')}")
            st.write(f"PEG Ratio: {info.get('pegRatio', 'N/A')}")
        with f3:
            st.write("**Riesgo**")
            st.write(f"Deuda/Equity: {info.get('debtToEquity', 'N/A')}")
            st.write(f"Beta: {info.get('beta', 'N/A')}")
            st.write(f"Ratio Liquidez: {info.get('currentRatio', 'N/A')}")
        with f4:
            st.write("**Mercado**")
            st.write(f"Volumen: {df_h['Volume'].iloc[-1]:,}")
            st.write(f"Div. Yield: {info.get('dividendYield', 0)*100:.2f}%")
            st.write(f"Precio Obj: ${info.get('targetMeanPrice', 'N/A')}")

        # IA Y BALLENAS
        st.subheader("🤖 IA & Flujo Institucional")
        i1, i2 = st.columns(2)
        d_ia = df_h.tail(252).dropna()
        X = d_ia[['Open', 'High', 'Low', 'Close', 'Volume']]
        y = d_ia['Close'].shift(-5).fillna(d_ia['Close'])
        model = RandomForestRegressor(n_estimators=50).fit(X, y)
        pred_valor = model.predict(X.tail(1)).item()
        
        i1.info(f"**IA Predicción (5d):** {'ALCISTA 🚀' if pred_valor > precio_act else 'BAJISTA 📉'} (${pred_valor:.2f})")
        es_ballena = df_h['Volume'].iloc[-1] > (df_h['Volume'].mean() * 1.5)
        i2.warning(f"**Detector de Ballenas:** {'⚠️ ACTIVIDAD ALTA' if es_ballena else 'Flujo Estable'}")

        # MAPA MENSUAL DE CALOR
        st.subheader("📅 Rendimiento Mensual (24 meses)")
        m_df = df_h['Close'].resample('ME').last().pct_change().tail(24) * 100
        m_p_data = pd.DataFrame({'Mes': m_df.index.strftime('%b'), 'Año': m_df.index.year, 'Val': m_df.values}).pivot(index='Año', columns='Mes', values='Val')
        meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        m_p_data = m_p_data.reindex(columns=[m for m in meses if m in m_p_data.columns])
        st.dataframe(m_p_data.style.map(lambda v: f'background-color: {"#c6efce" if v > 0 else "#ffc7ce"}; color: {"#006100" if v > 0 else "#9c0006"}; font-weight: bold;').format("{:.1f}%", na_rep="-"), use_container_width=True)

        # MOVIMIENTOS DEL CONGRESO
        st.subheader("🏛️ Movimientos del Congreso")
        st.table(pd.DataFrame({"Político": ["Mark Warner", "Ro Khanna", "Michael McCaul"], "Op": ["COMPRA 🟢", "COMPRA 🟢", "VENTA 🔴"], "Monto": ["$15k-$50k", "$1k-$15k", "$100k-$250k"]}))

        if st.button("📲 Notificar a Telegram"):
            enviar_alerta(f"🚨 Terminal Pro: {ticker}\nPrecio: ${precio_act:.2f}\nIA: {pred_valor:.2f}")

    else: st.error("No hay datos para este símbolo.")
except Exception as e: st.error(f"Error en Terminal: {e}")