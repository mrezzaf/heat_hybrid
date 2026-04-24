import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# --- KONFIGURASI GLOBAL (UNIFIED & LOCKED) ---
RISK_COLORS = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c'] # Hijau, Kuning, Oranye, Merah
RISK_MATRIX = np.array([[1, 1, 2, 2], [1, 1, 2, 3], [1, 2, 3, 3], [1, 2, 3, 4]])
STATUS_ICONS = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}
RISK_LABELS = ["1. Normal", "2. Low", "3. Moderate", "4. High"]

# --- 1. TIME SERIES: HIGHLIGHT EKSTREM & RISK BANDS (LOCKED) ---
def plot_interactive_timeseries(df, index_name, config_idx):
    bins = config_idx['bins']
    fig = go.Figure()
    for i in range(len(bins)):
        y0 = bins[i-1] if i > 0 else config_idx['min']
        fig.add_hrect(y0=y0, y1=bins[i], fillcolor=RISK_COLORS[i], opacity=0.1, line_width=0)
    fig.add_hrect(y0=bins[-1], y1=config_idx['max'], fillcolor=RISK_COLORS[-1], opacity=0.1, line_width=0)

    heat_load_area = np.where(df[index_name] > df[f'P95_{index_name}'], df[index_name], df[f'P95_{index_name}'])
    fig.add_trace(go.Scatter(x=df['time'], y=df[f'P95_{index_name}'], name='Baseline P95',
                             line=dict(color='rgba(231, 76, 60, 0.8)', width=2, dash='dash'), hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=df['time'], y=heat_load_area, fill='tonexty', 
                             fillcolor='rgba(231, 76, 60, 0.4)', mode='none', name='Heat Load', hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=df['time'], y=df[index_name], name=f'Daily {index_name}',
                             line=dict(color='#2c3e50', width=1.5), mode='lines'))
    fig.update_layout(title=dict(text=f"Analisis Temporal {index_name} & Heat Load Intensity", font=dict(size=18)),
                      yaxis_title=f"Nilai {index_name} ({config_idx.get('unit', 'unit')})",
                      yaxis=dict(range=[config_idx['min'], config_idx['max']]),
                      hovermode="x unified", template="plotly_white", 
                      xaxis=dict(rangeslider=dict(visible=True), type="date"))
    return fig

# --- 2. RADAR CHART (LOCKED) ---
def plot_radar_chart(df_clim, indices):
    values = df_clim[indices].mean().tolist()
    values += values[:1]
    categories = indices + [indices[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself',
                                         fillcolor='rgba(0, 51, 102, 0.3)', line=dict(color='#003366', width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, gridcolor="lightgrey")), title="Karakteristik Thermal", template="plotly_white")
    return fig

# --- 3. SPATIAL MAPS (VALUE & HAZARD EXPOSURE) ---
def plot_spatial_map(df_map, month_selected, index_name):
    df_plot = df_map[df_map['month'] == month_selected].copy()
    vmin, vmax = df_plot['value'].quantile(0.02), df_plot['value'].quantile(0.98)
    fig = px.scatter_mapbox(df_plot, lat='lat', lon='lon', color='value', size_max=5,
                            color_continuous_scale="turbo", range_color=[vmin, vmax],
                            mapbox_style="carto-positron", zoom=3.5, center={"lat": -2.5, "lon": 118},
                            title=f"Peta Klimatologi {index_name}")
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    return fig

def plot_hazard_exposure_map(df_map, month_selected, index_name, config_idx):
    df_plot = df_map[df_map['month'] == month_selected].copy()
    bins = config_idx['bins']
    
    def get_hazard_level(v):
        if v < bins[0]: return RISK_LABELS[0]
        elif v < bins[1]: return RISK_LABELS[1]
        elif v < bins[2]: return RISK_LABELS[2]
        else: return RISK_LABELS[3]

    df_plot['hazard_level'] = df_plot['value'].apply(get_hazard_level)

    # --- PERBAIKAN: TITIK GHOIB AGAR LEGENDA SERAGAM ---
    # Taruh dummy ke koordinat 90 (Kutub Utara) agar tidak terlihat di zoom Indonesia
    dummy_rows = pd.DataFrame({
        'lat': [90.0] * len(RISK_LABELS),
        'lon': [0.0] * len(RISK_LABELS),
        'hazard_level': RISK_LABELS,
        'value': [0] * len(RISK_LABELS)
    })
    df_final = pd.concat([df_plot, dummy_rows], ignore_index=True)
    
    # Berikan ukuran konstan 1 untuk SEMUA data (asli maupun dummy)
    df_final['marker_size'] = 1

    fig = px.scatter_mapbox(
        df_final, 
        lat='lat', lon='lon', 
        color='hazard_level',
        size='marker_size', # Gunakan kolom marker_size yang seragam
        category_orders={"hazard_level": RISK_LABELS}, 
        color_discrete_map={L: C for L, C in zip(RISK_LABELS, RISK_COLORS)},
        size_max=6,
        mapbox_style="carto-positron", 
        zoom=3.5, 
        center={"lat": -2.5, "lon": 118},
        title=f"Hazard Exposure Map: {index_name}"
    )
    
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0}, 
        legend_title_text="Risk Level",
        legend=dict(itemsizing='constant') # Memastikan ukuran di legenda tetap sama
    )
    return fig

# --- 4. TRENDS & BOXPLOTS (LOCKED) ---
def plot_extreme_trend(df_ext, index_name):
    col_name = f'extreme_days_{index_name}'
    fig = go.Figure(go.Bar(x=df_ext['Year'], y=df_ext[col_name], name='Days', marker_color='rgba(44, 62, 80, 0.6)'))
    if len(df_ext) > 1:
        slope, intercept = np.polyfit(df_ext['Year'], df_ext[col_name], 1)
        fig.add_trace(go.Scatter(x=df_ext['Year'], y=slope*df_ext['Year']+intercept, mode='lines', name='Trend', line=dict(color='red', dash='dash')))
    fig.update_layout(title=f"Trend Kejadian Ekstrem", template="plotly_white")
    return fig

def plot_monthly_boxplot(df, index_name):
    fig = go.Figure(go.Box(x=df['time'].dt.month, y=df[index_name], name=index_name, marker_color='#003366'))
    p95_mean = df[f'P95_{index_name}'].mean()
    fig.add_shape(type="line", x0=0.5, x1=12.5, y0=p95_mean, y1=p95_mean, line=dict(color="Red", width=2, dash="dash"))
    fig.update_layout(title="Distribusi Bulanan", template="plotly_white")
    return fig

# --- 5. RISK MATRIX (FIXED AXES & STAR ICON) ---
def plot_climatological_risk_matrix(df_trend, df_ext, index_name, config_idx):
    sev_labels = ["Normal", "Low", "Moderate", "High"]
    freq_labels = ["Rare", "Occasional", "Frequent", "Persistent"]
    val_to_check = 30 
    sev_idx = min(np.digitize(val_to_check, config_idx['bins']), 3)
    avg_freq = df_ext.tail(5)[f'extreme_days_{index_name}'].mean()
    freq_idx = min(np.digitize(avg_freq, [10, 30, 60]), 3)
    risk_lvl = RISK_MATRIX[freq_idx, sev_idx]
    
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=RISK_MATRIX, x=sev_labels, y=freq_labels,
        colorscale=[[0, RISK_COLORS[0]], [0.33, RISK_COLORS[1]], [0.66, RISK_COLORS[2]], [1, RISK_COLORS[3]]],
        showscale=False, opacity=0.4, text=RISK_MATRIX, texttemplate="%{text}"
    ))
    fig.add_trace(go.Scatter(
        x=[sev_labels[sev_idx]], y=[freq_labels[freq_idx]],
        mode='markers+text',
        marker=dict(size=40, color=RISK_COLORS[risk_lvl-1], symbol='star', line=dict(color='white', width=3)),
        text=[f"LEVEL {risk_lvl}"], textposition="top center",
        name='Current Status'
    ))
    fig.update_layout(
        title=f"Matriks Risiko Klimatologis: {index_name}",
        xaxis_title="Keparahan (Severity Index)",
        yaxis_title="Frekuensi (Frequency of Extremes)",
        template="plotly_white", height=450,
        xaxis={'categoryorder':'array', 'categoryarray':sev_labels},
        yaxis={'categoryorder':'array', 'categoryarray':freq_labels}
    )
    return fig, risk_lvl

def plot_yearly_boxplot(df, index_name):
    # Buat kolom tahun jika belum ada
    if 'year' not in df.columns:
        df['year'] = df['time'].dt.year

    fig = go.Figure()

    fig.add_trace(go.Box(
        x=df['year'],
        y=df[index_name],
        name=index_name,
        marker_color='#2c3e50',
        boxpoints='outliers',
        line=dict(width=1)
    ))

    # Tambahkan garis tren median
    yearly_median = df.groupby('year')[index_name].median()
    fig.add_trace(go.Scatter(
        x=yearly_median.index,
        y=yearly_median.values,
        mode='lines',
        name='Trend Median',
        line=dict(color='red', width=1),
        hoverinfo='skip'
    ))

    # --- BAGIAN YANG DIUBAH ---
    fig.update_layout(
        title=dict(text=f"Variabilitas Tahunan {index_name} (1981-2024)", font=dict(size=18)),
        xaxis_title="Tahun",
        yaxis_title="Nilai Indeks",
        template="plotly_white",
        showlegend=False,
        xaxis=dict(
            tickmode='linear', # Memastikan label mengikuti interval linear
            tick0=1981,        # Tahun awal
            dtick=1,           # Loncat setiap 2 tahun (ubah jadi 1 jika ingin tiap tahun)
            tickangle=-90,     # Membuat label tegak lurus (vertikal)
            type='category'    # Menganggap tahun sebagai kategori agar boxplot tidak renggang
        )
    )
    
    return fig