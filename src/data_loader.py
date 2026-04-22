import streamlit as st
import pandas as pd
from pathlib import Path

# Path konfigurasi
DATA_DIR = Path("data")

@st.cache_data
def get_station_list():
    df = pd.read_csv(DATA_DIR / "metadata" / "Master_Referensi_Stasiun_Lengkap.csv")
    return df

@st.cache_data
def load_monthly_climatology():
    return pd.read_parquet(DATA_DIR / "stats" / "station_monthly_climatology.parquet")

@st.cache_data
def load_station_trends():
    return pd.read_parquet(DATA_DIR / "stats" / "station_trends.parquet")

@st.cache_data
def load_extreme_counts():
    return pd.read_parquet(DATA_DIR / "stats" / "station_extreme_counts.parquet")

@st.cache_data
def load_modular_station_data(indices_selected, wmo_id):
    """Membaca data harian modular dan menggabungkannya"""
    combined_df = None
    for idx in indices_selected:
        file_path = DATA_DIR / "stations" / f"{idx}_daily_station.parquet"
        if file_path.exists():
            df = pd.read_parquet(file_path)
            df_st = df[df['WMO_ID'] == wmo_id].copy()
            df_st['time'] = pd.to_datetime(df_st['time'])
            
            if combined_df is None:
                combined_df = df_st
            else:
                # Gabungkan kolom index dan P95-nya saja
                cols_to_use = ['time', 'WMO_ID', idx, f'P95_{idx}']
                combined_df = pd.merge(combined_df, df_st[cols_to_use], on=['time', 'WMO_ID'], how='outer')
    return combined_df

@st.cache_data
def load_spatial_data(index_name):
    file_path = DATA_DIR / "spatial" / f"{index_name}_map_climatology.parquet"
    if file_path.exists():
        return pd.read_parquet(file_path)
    return None