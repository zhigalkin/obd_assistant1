"""
Streamlit дашборд для живого мониторинга OBD-II данных.
Запуск: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import time
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

st.set_page_config(page_title="OBD Диагностика", page_icon="🚗", layout="wide")

st.markdown("""
<style>
.metric-ok { color: #a6e3a1; }
.metric-warn { color: #f9e2af; }
.metric-error { color: #f38ba8; }
</style>
""", unsafe_allow_html=True)

st.title("🚗 OBD-II Дашборд — Живой Мониторинг")

def load_latest_session(db_path):
    if not os.path.exists(db_path):
        return None, []
    try:
        conn = sqlite3.connect(db_path)
        session = pd.read_sql("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 1", conn)
        if session.empty:
            conn.close()
            return None, []
        sid = session.iloc[0]['id']
        readings = pd.read_sql(f"SELECT * FROM readings WHERE session_id={sid}", conn)
        conn.close()
        return session.iloc[0], readings
    except Exception as e:
        return None, []

def load_history(db_path, limit=50):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql("""
            SELECT s.timestamp, r.pid_name, r.value, r.unit, r.is_anomaly
            FROM readings r JOIN sessions s ON r.session_id = s.id
            ORDER BY s.timestamp DESC LIMIT ?
        """, conn, params=(limit,))
        conn.close()
        return df
    except:
        return pd.DataFrame()

# Боковая панель
with st.sidebar:
    st.header("⚙️ Настройки")
    db_path = st.text_input("Путь к БД", config.DB_PATH)
    auto_refresh = st.checkbox("Автообновление (5 сек)", value=True)
    st.markdown("---")
    st.info("Запустите main.py для сбора данных")

# Основной контент
tab1, tab2, tab3 = st.tabs(["📊 Последнее сканирование", "📈 История", "🔴 Аномалии"])

with tab1:
    session, readings = load_latest_session(db_path)
    if session is None:
        st.warning("База данных пуста. Запустите диагностику в main.py")
    else:
        st.subheader(f"Сессия: {session.get('timestamp', '?')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VIN", session.get('vin', 'Н/Д') or 'Н/Д')
        with col2:
            st.metric("Марка", session.get('car_brand', 'generic'))
        with col3:
            anomaly_count = readings[readings['is_anomaly'] == 1].shape[0] if not isinstance(readings, list) and len(readings) > 0 else 0
            st.metric("Аномалий", anomaly_count, delta=None)

        if not isinstance(readings, list) and len(readings) > 0:
            st.dataframe(
                readings[['pid_name', 'value', 'unit', 'is_anomaly', 'anomaly_msg']].rename(columns={
                    'pid_name': 'Параметр', 'value': 'Значение', 'unit': 'Ед.',
                    'is_anomaly': 'Аномалия', 'anomaly_msg': 'Описание'
                }),
                use_container_width=True
            )

            # Графики ключевых параметров
            key_pids = ['RPM', 'SPEED', 'COOLANT_TEMP', 'THROTTLE_POS', 'ENGINE_LOAD']
            key_data = readings[readings['pid_name'].isin(key_pids)]
            if not key_data.empty:
                fig = px.bar(key_data, x='pid_name', y='value', color='is_anomaly',
                            color_discrete_map={0: '#a6e3a1', 1: '#f38ba8'},
                            title="Ключевые параметры", labels={'pid_name': 'Параметр', 'value': 'Значение'})
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    history = load_history(db_path, 200)
    if history.empty:
        st.info("История пуста")
    else:
        pid_options = history['pid_name'].unique().tolist()
        selected_pid = st.selectbox("Выбери параметр", pid_options)
        pid_history = history[history['pid_name'] == selected_pid].copy()
        pid_history['value'] = pd.to_numeric(pid_history['value'], errors='coerce')
        pid_history = pid_history.dropna(subset=['value'])
        if not pid_history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=pid_history['timestamp'], y=pid_history['value'],
                mode='lines+markers', name=selected_pid,
                line=dict(color='#89b4fa')
            ))
            fig.update_layout(title=f"История: {selected_pid}", xaxis_title="Время", yaxis_title="Значение")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    history = load_history(db_path, 500)
    if not history.empty:
        anomalies = history[history['is_anomaly'] == 1]
        if anomalies.empty:
            st.success("✅ Аномалий не обнаружено")
        else:
            st.error(f"⚠️ Найдено {len(anomalies)} аномальных показаний")
            st.dataframe(anomalies[['timestamp', 'pid_name', 'value', 'unit']].rename(columns={
                'timestamp': 'Время', 'pid_name': 'Параметр', 'value': 'Значение', 'unit': 'Ед.'
            }), use_container_width=True)
    else:
        st.info("Нет данных")

if auto_refresh:
    time.sleep(5)
    st.rerun()
