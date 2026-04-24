import streamlit as st
import numpy as np
import pandas as pd
from src.data_loader import *
from src.plots import *

# --- 1. CONFIGURATION & CONSTANTS ---
CONFIG = {
    "hi":   {'bins': [27, 32, 41], 'min': 20, 'max': 50, 'unit': '°C', 'lbl': 'HI'},
    "utci": {'bins': [26, 32, 38], 'min': 15, 'max': 45, 'unit': '°C', 'lbl': 'UTCI'},
    "wbgt": {'bins': [25, 28, 30], 'min': 15, 'max': 35, 'unit': '°C', 'lbl': 'WBGT'},
    "thi":  {'bins': [21, 24, 27], 'min': 15, 'max': 35, 'unit': '°C', 'lbl': 'THI'},
    "at":   {'bins': [27, 32, 41], 'min': 20, 'max': 45, 'unit': '°C', 'lbl': 'AT'},
    "net":  {'bins': [21, 24, 27], 'min': 15, 'max': 35, 'unit': '°C', 'lbl': 'NET'},
    "ichi": {'bins': [26, 32, 38], 'min': 15, 'max': 45, 'unit': '°C', 'lbl': 'ICHI'},
}

STATUS_ICONS = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}
RISK_LEVEL_NAMES = {1: "Normal", 2: "Low", 3: "Moderate", 4: "High"}
ICHI_LABELS = {0: "Comfortable", 1: "Low Risk", 2: "Moderate Risk", 3: "High Risk"}

# --- 2. STREAMLIT SETUP ---
st.set_page_config(layout="wide", page_title="BMKG Heat Index Explorer", page_icon="🌡️")

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.image("https://www.bmkg.go.id/asset/img/logo/logo-bmkg.png", width=80)
st.sidebar.title("Kontrol Analisis")

st_list = get_station_list()
selected_st_name = st.sidebar.selectbox("Pilih Stasiun", st_list['NAME'])
wmo_id = st_list[st_list['NAME'] == selected_st_name]['WMO_ID'].values[0]

indices = ["HI", "THI", "NET", "AT", "WBGT", "UTCI", "ICHI"]
selected_idx = st.sidebar.selectbox("Pilih Indeks Panas", indices, index=6)

cfg = CONFIG.get(selected_idx.lower(), {'bins': [27, 32, 41], 'min': 20, 'max': 50, 'unit': 'unit'})

# --- 4. DATA INITIALIZATION ---
df_daily = load_modular_station_data([selected_idx], wmo_id)

# Penentuan Status Berdasarkan Data 30 Hari Terakhir
current_val = df_daily[selected_idx].tail(30).mean()
sev_idx = np.digitize(current_val, cfg['bins']) + 1
status_icon = STATUS_ICONS.get(sev_idx, "⚪")
status_name = RISK_LEVEL_NAMES.get(sev_idx, "Unknown")

# --- 5. HEADER SECTION ---
col_head1, col_head2 = st.columns([0.8, 0.2])
with col_head1:
    st.title(f"{status_icon} {selected_st_name}: Level {status_name}")
    if selected_idx.lower() == "ichi":
        label_ichi = ICHI_LABELS.get(sev_idx - 1, "Unknown")
        st.subheader(f"Kategori Kenyamanan: **{label_ichi}**")
with col_head2:
    st.info(f"**WMO ID:** {wmo_id}")

st.info(f"📍 Koordinat: {st_list[st_list['WMO_ID']==wmo_id]['CURRENT_LATITUDE'].values[0]}, {st_list[st_list['WMO_ID']==wmo_id]['CURRENT_LONGITUDE'].values[0]}")

# --- 6. MAIN CONTENT (TABS) ---
tab1, tab2, tab3 = st.tabs(["📊 Station Profile", "🗺️ Spatial Map", "📈 Long-term Trends"])

# --- TAB 1: PROFILE STASIUN ---
with tab1:
    col1, col2 = st.columns([2, 1])
    df_clim = load_monthly_climatology()
    df_clim_st = df_clim[df_clim['WMO_ID'] == wmo_id]
    
    with col1:
        # Grafik Utama: Time Series
        st.plotly_chart(plot_interactive_timeseries(df_daily, selected_idx, cfg), use_container_width=True)
    with col2:
        # Radar Chart
        st.plotly_chart(plot_radar_chart(df_clim_st, indices), use_container_width=True)
    
    st.divider()
    
    # BAGIAN DISTRIBUSI (LAYOUT VERTIKAL / ATAS-BAWAH)
    st.subheader(f"🔍 Analisis Distribusi Historis: {selected_idx}")
    
    # Grafik 1: Boxplot Bulanan
    st.write("#### 🗓️ Siklus Tahunan (Variasi per Bulan)")
    st.info("Grafik ini menunjukkan pola musiman dan kapan biasanya nilai ekstrem muncul dalam satu tahun.")
    st.plotly_chart(plot_monthly_boxplot(df_daily, selected_idx), use_container_width=True, key="box_monthly_main")
    
    st.write("") # Spacer agar tidak terlalu mepet
    
    # Grafik 2: Boxplot Tahunan
    st.write("#### ⏳ Tren Distribusi Tahunan (1981-2024)")
    st.info("Grafik ini menunjukkan bagaimana rentang nilai (interquartile) bergeser naik dari dekade ke dekade.")
    st.plotly_chart(plot_yearly_boxplot(df_daily, selected_idx), use_container_width=True, key="box_yearly_main")

# --- TAB 2: ANALISIS SPASIAL ---
with tab2:
    st.subheader("Analisis Spasial: Heat Hazard & Exposure")
    map_type = st.radio(
        "Pilih Tipe Tampilan Peta:", 
        ["Nilai Klimatologi (Raw)", "Hazard Exposure Map (Normal - High)"], 
        horizontal=True
    )
    month = st.slider("Pilih Bulan", 1, 12, 10)
    
    df_map = load_spatial_data(selected_idx)
    if df_map is not None:
        if "Raw" in map_type:
            st.plotly_chart(plot_spatial_map(df_map, month, selected_idx), use_container_width=True)
        else:
            st.plotly_chart(plot_hazard_exposure_map(df_map, month, selected_idx, cfg), use_container_width=True)
    else:
        st.error(f"Data spasial untuk {selected_idx} tidak ditemukan.")

# --- TAB 3: TREN & RISIKO ---
with tab3:
    st.subheader("Analisis Tren & Kejadian Ekstrem")
    df_trend = load_station_trends()
    st_trend = df_trend[(df_trend['WMO_ID'] == wmo_id) & (df_trend['index_name'] == selected_idx)]
    
    if not st_trend.empty:
        val_trend = st_trend['slope_per_decade'].values[0]
        sig = "Signifikan (p < 0.05)" if st_trend['significant'].values[0] else "Tidak Signifikan"
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Laju Perubahan per Dekade", f"{val_trend:+.2f} unit", 
                      delta=f"{val_trend*4.4:+.2f} total (44thn)", delta_color="inverse")
        with c2:
            st.info(f"**Status Statistik:** {sig}")

    st.divider()
    df_ext = load_extreme_counts()
    df_ext_st = df_ext[df_ext['WMO_ID'] == wmo_id].sort_values('Year')
    
    if not df_ext_st.empty:
        st.plotly_chart(plot_extreme_trend(df_ext_st, selected_idx), use_container_width=True)
        
        st.divider()
        st.subheader("⚠️ Climatological Risk Assessment")
        col_mat1, col_mat2 = st.columns([1.2, 0.8])
        
        with col_mat1:
            fig_mat, risk_lvl = plot_climatological_risk_matrix(df_trend, df_ext_st, selected_idx, cfg)
            st.plotly_chart(fig_mat, use_container_width=True)
        
        with col_mat2:
            status_diag = RISK_LEVEL_NAMES.get(risk_lvl, "Unknown")
            st.write(f"### Diagnosis Risiko: {STATUS_ICONS.get(risk_lvl, '⚪')} {status_diag}")
            st.title(f"Status: {status_diag}")
            st.markdown(f"""
            Berdasarkan integrasi data historis, stasiun ini dikategorikan dalam profil risiko **{status_diag}**.
            
            **Metodologi Diagnosis:**
            * **Severity (X):** Intensitas thermal terhadap ambang batas fisik.
            * **Frequency (Y):** Persistensi kejadian ekstrem (>P95).
            """)
            st.warning("Gunakan kategori ini untuk menentukan prioritas mitigasi.")
    else:
        st.warning("Data kejadian ekstrem tidak tersedia untuk stasiun ini.")

# --- 7. FOOTER ---
st.sidebar.divider()
st.sidebar.caption("© 2026 BMKG - Analisis Hybrid ERA5 & FKlim")