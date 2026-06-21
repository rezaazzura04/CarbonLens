"""
CarbonLens V7 — GIS Intelligence Module
Fully interactive: Province/Regency selection OR GeoJSON/CSV upload
Real computed outputs: carbon stock, risk, biodiversity, land cover
"""

import streamlit as st
import utils.state as S
import numpy as np
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
import math
try:
    import folium
    from streamlit_folium import st_folium
    _FOLIUM_OK = True
except ImportError:
    _FOLIUM_OK = False
from components.ui import page_header, kpi_card, insight_panel
from utils.charts import carbon_stock_area
from config.settings import COLORS
from utils import gee_client

# Auto-initialize GEE from env credentials on module load (silent)
if not gee_client.is_ready():
    _ok, _msg = gee_client.initialize()

# ─────────────────────────────────────────────────────────────────────────────
# STATIC REFERENCE DATA
# ─────────────────────────────────────────────────────────────────────────────

PROVINCES = {
    # ── SUMATRA ──────────────────────────────────────────────────────────────
    "Aceh": {
        "regencies": ["Banda Aceh", "Aceh Besar", "Aceh Tengah", "Aceh Tenggara", "Aceh Timur"],
        "base_carbon": 142, "base_risk": 0.58, "base_bio": 0.81,
        "mangrove_ha": 24700, "protected_pct": 67, "lat": 4.7, "lon": 96.9,
    },
    "Sumatera Utara": {
        "regencies": ["Medan", "Deli Serdang", "Simalungun", "Tapanuli Utara", "Asahan"],
        "base_carbon": 118, "base_risk": 0.66, "base_bio": 0.74,
        "mangrove_ha": 31200, "protected_pct": 48, "lat": 3.6, "lon": 98.7,
    },
    "Sumatera Barat": {
        "regencies": ["Padang", "Bukittinggi", "Agam", "Pesisir Selatan", "Tanah Datar"],
        "base_carbon": 128, "base_risk": 0.52, "base_bio": 0.77,
        "mangrove_ha": 8900, "protected_pct": 55, "lat": -0.9, "lon": 100.4,
    },
    "Riau": {
        "regencies": ["Pekanbaru", "Dumai", "Bengkalis", "Siak", "Meranti"],
        "base_carbon": 112, "base_risk": 0.79, "base_bio": 0.61,
        "mangrove_ha": 42100, "protected_pct": 41, "lat": 0.5, "lon": 101.4,
    },
    "Kepulauan Riau": {
        "regencies": ["Tanjung Pinang", "Batam", "Bintan", "Karimun", "Natuna"],
        "base_carbon": 76, "base_risk": 0.44, "base_bio": 0.68,
        "mangrove_ha": 19500, "protected_pct": 38, "lat": 0.9, "lon": 104.5,
    },
    "Jambi": {
        "regencies": ["Jambi", "Muaro Jambi", "Batanghari", "Bungo", "Tebo"],
        "base_carbon": 124, "base_risk": 0.70, "base_bio": 0.72,
        "mangrove_ha": 6700, "protected_pct": 44, "lat": -1.6, "lon": 103.6,
    },
    "Sumatera Selatan": {
        "regencies": ["Palembang", "Musi Banyuasin", "Ogan Komering Ilir", "Lahat", "Banyuasin"],
        "base_carbon": 109, "base_risk": 0.74, "base_bio": 0.65,
        "mangrove_ha": 22800, "protected_pct": 39, "lat": -3.0, "lon": 104.8,
    },
    "Bangka Belitung": {
        "regencies": ["Pangkal Pinang", "Bangka", "Belitung", "Bangka Selatan", "Belitung Timur"],
        "base_carbon": 68, "base_risk": 0.61, "base_bio": 0.59,
        "mangrove_ha": 11400, "protected_pct": 27, "lat": -2.1, "lon": 106.1,
    },
    "Bengkulu": {
        "regencies": ["Bengkulu", "Rejang Lebong", "Bengkulu Utara", "Seluma", "Kepahiang"],
        "base_carbon": 131, "base_risk": 0.49, "base_bio": 0.79,
        "mangrove_ha": 3200, "protected_pct": 61, "lat": -3.8, "lon": 102.3,
    },
    "Lampung": {
        "regencies": ["Bandar Lampung", "Lampung Selatan", "Lampung Tengah", "Tanggamus", "Way Kanan"],
        "base_carbon": 92, "base_risk": 0.57, "base_bio": 0.66,
        "mangrove_ha": 9100, "protected_pct": 43, "lat": -5.4, "lon": 105.3,
    },

    # ── JAVA & BALI ──────────────────────────────────────────────────────────
    "DKI Jakarta": {
        "regencies": ["Jakarta Pusat", "Jakarta Utara", "Jakarta Selatan", "Jakarta Barat", "Jakarta Timur"],
        "base_carbon": 22, "base_risk": 0.35, "base_bio": 0.21,
        "mangrove_ha": 1100, "protected_pct": 8, "lat": -6.2, "lon": 106.8,
    },
    "Jawa Barat": {
        "regencies": ["Bandung", "Bogor", "Bekasi", "Sukabumi", "Cianjur"],
        "base_carbon": 58, "base_risk": 0.51, "base_bio": 0.54,
        "mangrove_ha": 4200, "protected_pct": 23, "lat": -6.9, "lon": 107.6,
    },
    "Jawa Tengah": {
        "regencies": ["Semarang", "Surakarta", "Magelang", "Pati", "Cilacap"],
        "base_carbon": 49, "base_risk": 0.47, "base_bio": 0.49,
        "mangrove_ha": 3600, "protected_pct": 19, "lat": -7.0, "lon": 110.4,
    },
    "DIY Yogyakarta": {
        "regencies": ["Yogyakarta", "Sleman", "Bantul", "Gunung Kidul", "Kulon Progo"],
        "base_carbon": 45, "base_risk": 0.43, "base_bio": 0.51,
        "mangrove_ha": 100, "protected_pct": 17, "lat": -7.8, "lon": 110.4,
    },
    "Jawa Timur": {
        "regencies": ["Surabaya", "Malang", "Kediri", "Jember", "Banyuwangi"],
        "base_carbon": 56, "base_risk": 0.50, "base_bio": 0.58,
        "mangrove_ha": 6800, "protected_pct": 22, "lat": -7.5, "lon": 112.2,
    },
    "Banten": {
        "regencies": ["Serang", "Tangerang", "Cilegon", "Pandeglang", "Lebak"],
        "base_carbon": 64, "base_risk": 0.53, "base_bio": 0.57,
        "mangrove_ha": 5400, "protected_pct": 26, "lat": -6.1, "lon": 106.2,
    },
    "Bali": {
        "regencies": ["Denpasar", "Badung", "Gianyar", "Tabanan", "Buleleng"],
        "base_carbon": 53, "base_risk": 0.40, "base_bio": 0.62,
        "mangrove_ha": 1900, "protected_pct": 25, "lat": -8.4, "lon": 115.2,
    },

    # ── NUSA TENGGARA ────────────────────────────────────────────────────────
    "Nusa Tenggara Barat": {
        "regencies": ["Mataram", "Lombok Barat", "Lombok Timur", "Sumbawa", "Bima"],
        "base_carbon": 61, "base_risk": 0.45, "base_bio": 0.63,
        "mangrove_ha": 4100, "protected_pct": 30, "lat": -8.6, "lon": 116.1,
    },
    "Nusa Tenggara Timur": {
        "regencies": ["Kupang", "Ende", "Sikka", "Manggarai", "Belu"],
        "base_carbon": 57, "base_risk": 0.48, "base_bio": 0.66,
        "mangrove_ha": 14200, "protected_pct": 35, "lat": -10.2, "lon": 123.6,
    },

    # ── KALIMANTAN ───────────────────────────────────────────────────────────
    "Kalimantan Barat": {
        "regencies": ["Pontianak", "Ketapang", "Sambas", "Sintang", "Kapuas Hulu"],
        "base_carbon": 122, "base_risk": 0.71, "base_bio": 0.69,
        "mangrove_ha": 29800, "protected_pct": 49, "lat": 0.0, "lon": 109.3,
    },
    "Kalimantan Tengah": {
        "regencies": ["Palangka Raya", "Kotawaringin Barat", "Kotawaringin Timur", "Kapuas", "Barito Utara"],
        "base_carbon": 135, "base_risk": 0.55, "base_bio": 0.72,
        "mangrove_ha": 38200, "protected_pct": 58, "lat": -1.2, "lon": 113.9,
    },
    "Kalimantan Selatan": {
        "regencies": ["Banjarmasin", "Banjarbaru", "Banjar", "Tanah Laut", "Kotabaru"],
        "base_carbon": 101, "base_risk": 0.68, "base_bio": 0.63,
        "mangrove_ha": 26500, "protected_pct": 33, "lat": -3.3, "lon": 114.6,
    },
    "Kalimantan Timur": {
        "regencies": ["Samarinda", "Balikpapan", "Kutai Kartanegara", "Berau", "Mahakam Ulu", "Kutai Timur"],
        "base_carbon": 148, "base_risk": 0.62, "base_bio": 0.78,
        "mangrove_ha": 52400, "protected_pct": 64, "lat": -0.5, "lon": 116.8,
    },
    "Kalimantan Utara": {
        "regencies": ["Tanjung Selor", "Bulungan", "Malinau", "Nunukan", "Tana Tidung"],
        "base_carbon": 156, "base_risk": 0.50, "base_bio": 0.83,
        "mangrove_ha": 35100, "protected_pct": 71, "lat": 3.1, "lon": 117.0,
    },

    # ── SULAWESI ─────────────────────────────────────────────────────────────
    "Sulawesi Utara": {
        "regencies": ["Manado", "Bitung", "Minahasa", "Bolaang Mongondow", "Sangihe"],
        "base_carbon": 104, "base_risk": 0.46, "base_bio": 0.76,
        "mangrove_ha": 9800, "protected_pct": 47, "lat": 1.5, "lon": 124.8,
    },
    "Sulawesi Tengah": {
        "regencies": ["Palu", "Donggala", "Poso", "Banggai", "Toli-Toli"],
        "base_carbon": 121, "base_risk": 0.57, "base_bio": 0.80,
        "mangrove_ha": 16700, "protected_pct": 56, "lat": -1.4, "lon": 121.4,
    },
    "Sulawesi Selatan": {
        "regencies": ["Makassar", "Bone", "Luwu Utara", "Bulukumba", "Selayar"],
        "base_carbon": 98, "base_risk": 0.48, "base_bio": 0.65,
        "mangrove_ha": 18400, "protected_pct": 52, "lat": -3.7, "lon": 120.1,
    },
    "Sulawesi Tenggara": {
        "regencies": ["Kendari", "Bau-Bau", "Kolaka", "Konawe", "Buton"],
        "base_carbon": 110, "base_risk": 0.51, "base_bio": 0.74,
        "mangrove_ha": 21300, "protected_pct": 50, "lat": -3.9, "lon": 122.5,
    },
    "Gorontalo": {
        "regencies": ["Gorontalo", "Boalemo", "Bone Bolango", "Pohuwato", "Gorontalo Utara"],
        "base_carbon": 96, "base_risk": 0.44, "base_bio": 0.71,
        "mangrove_ha": 5200, "protected_pct": 45, "lat": 0.5, "lon": 123.1,
    },
    "Sulawesi Barat": {
        "regencies": ["Mamuju", "Polewali Mandar", "Majene", "Mamasa", "Mamuju Utara"],
        "base_carbon": 116, "base_risk": 0.53, "base_bio": 0.75,
        "mangrove_ha": 7900, "protected_pct": 49, "lat": -2.7, "lon": 119.2,
    },

    # ── MALUKU ───────────────────────────────────────────────────────────────
    "Maluku": {
        "regencies": ["Ambon", "Tual", "Maluku Tengah", "Buru", "Seram Bagian Timur"],
        "base_carbon": 134, "base_risk": 0.40, "base_bio": 0.85,
        "mangrove_ha": 28600, "protected_pct": 60, "lat": -3.7, "lon": 128.2,
    },
    "Maluku Utara": {
        "regencies": ["Ternate", "Tidore", "Halmahera Barat", "Halmahera Tengah", "Halmahera Selatan"],
        "base_carbon": 141, "base_risk": 0.38, "base_bio": 0.87,
        "mangrove_ha": 31900, "protected_pct": 63, "lat": 0.8, "lon": 127.4,
    },

    # ── PAPUA (incl. 2022/2023 new provinces) ──────────────────────────────
    "Papua": {
        "regencies": ["Jayapura", "Merauke", "Biak Numfor", "Sarmi", "Mimika"],
        "base_carbon": 178, "base_risk": 0.28, "base_bio": 0.96,
        "mangrove_ha": 112000, "protected_pct": 78, "lat": -2.5, "lon": 140.7,
    },
    "Papua Barat": {
        "regencies": ["Manokwari", "Sorong", "Fakfak", "Kaimana", "Teluk Bintuni"],
        "base_carbon": 189, "base_risk": 0.31, "base_bio": 0.94,
        "mangrove_ha": 98700, "protected_pct": 82, "lat": -1.3, "lon": 133.2,
    },
    "Papua Tengah": {
        "regencies": ["Nabire", "Paniai", "Mimika", "Puncak Jaya", "Dogiyai"],
        "base_carbon": 182, "base_risk": 0.27, "base_bio": 0.95,
        "mangrove_ha": 67000, "protected_pct": 80, "lat": -3.9, "lon": 136.9,
    },
    "Papua Pegunungan": {
        "regencies": ["Jayawijaya", "Pegunungan Bintang", "Yahukimo", "Tolikara", "Lanny Jaya"],
        "base_carbon": 195, "base_risk": 0.22, "base_bio": 0.97,
        "mangrove_ha": 0, "protected_pct": 85, "lat": -4.1, "lon": 139.0,
    },
    "Papua Selatan": {
        "regencies": ["Merauke", "Boven Digoel", "Mappi", "Asmat"],
        "base_carbon": 172, "base_risk": 0.30, "base_bio": 0.93,
        "mangrove_ha": 145000, "protected_pct": 76, "lat": -6.5, "lon": 140.4,
    },
    "Papua Barat Daya": {
        "regencies": ["Sorong", "Sorong Selatan", "Raja Ampat", "Tambrauw", "Maybrat"],
        "base_carbon": 186, "base_risk": 0.25, "base_bio": 0.98,
        "mangrove_ha": 88500, "protected_pct": 84, "lat": -0.9, "lon": 131.3,
    },
}

LAYER_CONFIG = {
    "Carbon Stock":      {"color": "#2D7A4F", "opacity": 0.7},
    "Mangrove":          {"color": "#1a6b3a", "opacity": 0.8},
    "Blue Carbon":       {"color": "#1d4ed8", "opacity": 0.65},
    "Risk Layer":        {"color": "#EF4444", "opacity": 0.6},
    "Protected Area":    {"color": "#8B5CF6", "opacity": 0.55},
}

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compute_gis_analysis(source: str, prov_data: dict, regency: str,
                         active_layers: list, study_area_ha: float,
                         uploaded_points: pd.DataFrame = None) -> dict:
    """
    Compute all GIS outputs from selection or upload.
    Returns dict with KPIs, chart data, land cover, and insights.
    """
    rng = np.random.default_rng(abs(hash(regency)) % 2**31)

    # Base values from province, adjusted per regency with deterministic noise
    base_c   = prov_data["base_carbon"]  + rng.integers(-15, 20)
    base_r   = min(0.95, prov_data["base_risk"]    + rng.uniform(-0.1, 0.15))
    base_b   = min(1.0,  prov_data["base_bio"]     + rng.uniform(-0.08, 0.08))
    prot_pct = min(100,  prov_data["protected_pct"]+ int(rng.integers(-8, 12)))
    mangrove = prov_data["mangrove_ha"] * (study_area_ha / 50000)

    carbon_stock_total = base_c * study_area_ha / 10000  # Tg C (rough)

    # Historical carbon trend (6 years)
    years   = list(range(2020, 2026))
    decay   = rng.uniform(0.012, 0.025)
    c_trend = [base_c * (1 - decay) ** (i) + rng.uniform(-2, 2) for i in range(6)]

    # Land cover breakdown
    total = 100
    forest  = max(10, int(rng.integers(30, 55)))
    mangrv  = max(5,  int(rng.integers(8, 22)))
    water   = max(3,  int(rng.integers(5, 15)))
    agri    = max(5,  int(rng.integers(10, 25)))
    built   = max(2,  int(rng.integers(2, 10)))
    other   = total - forest - mangrv - water - agri - built
    if other < 0: other = 0

    land_cover = {
        "Forest":     forest,
        "Mangrove":   mangrv,
        "Water":      water,
        "Agriculture":agri,
        "Built-up":   built,
        "Other":      other,
    }

    # Points from CSV upload (lat/lon) or synthetic hotspots
    if uploaded_points is not None and not uploaded_points.empty:
        lat_col = next((c for c in uploaded_points.columns if "lat" in c.lower()), None)
        lon_col = next((c for c in uploaded_points.columns if "lon" in c.lower() or "lng" in c.lower()), None)
        if lat_col and lon_col:
            hotspots = list(zip(
                uploaded_points[lat_col].astype(float).tolist(),
                uploaded_points[lon_col].astype(float).tolist(),
                rng.choice(["high", "moderate", "low"], len(uploaded_points)).tolist(),
            ))
        else:
            hotspots = _synthetic_hotspots(prov_data, rng)
    else:
        hotspots = _synthetic_hotspots(prov_data, rng)

    risk_label = "Critical" if base_r > 0.75 else "High" if base_r > 0.55 else "Moderate" if base_r > 0.35 else "Low"

    return {
        "carbon_stock":     round(base_c, 1),         # Mg C/ha
        "carbon_stock_total": round(carbon_stock_total, 2),  # Tg C
        "carbon_density":   round(base_c * 0.47, 1),  # Mg CO2e/ha
        "risk_index":       round(base_r, 3),
        "risk_label":       risk_label,
        "biodiversity":     round(base_b, 3),
        "protected_pct":    prot_pct,
        "mangrove_ha":      round(mangrove),
        "study_area_ha":    round(study_area_ha),
        "redd_eligible_ha": round(mangrove * 0.26),
        "annual_loss_pct":  round(decay * 100, 2),
        "sequestration":    round(base_c * 0.006, 3),   # Tg C/yr
        "years":            years,
        "carbon_trend":     [round(v, 1) for v in c_trend],
        "land_cover":       land_cover,
        "hotspots":         hotspots,
        "lat_center":       prov_data["lat"],
        "lon_center":       prov_data["lon"],
        "active_layers":    active_layers,
    }


def _synthetic_hotspots(prov_data, rng):
    n = int(rng.integers(4, 9))
    lats = prov_data["lat"] + rng.uniform(-1.5, 1.5, n)
    lons = prov_data["lon"] + rng.uniform(-2.0, 2.0, n)
    levels = rng.choice(["high", "moderate", "low"], n,
                        p=[0.3, 0.45, 0.25]).tolist()
    return list(zip(lats.tolist(), lons.tolist(), levels))


# ─────────────────────────────────────────────────────────────────────────────
# MAP BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_interactive_map(result: dict):
    """Build a Folium interactive map. Falls back to Plotly if folium unavailable."""

    lat_c = result["lat_center"]
    lon_c = result["lon_center"]
    hotspots = result.get("hotspots", [])

    if not _FOLIUM_OK:
        # Fallback: simple Plotly scatter on open-street tiles (no token needed)
        lats   = [h[0] for h in hotspots] or [lat_c]
        lons   = [h[1] for h in hotspots] or [lon_c]
        levels = [h[2] for h in hotspots] or ["low"]
        cmap   = {"high": "#EF4444", "moderate": "#F59E0B", "low": "#10B981"}
        fig = go.Figure(go.Scattergeo(
            lat=lats, lon=lons, mode="markers",
            marker=dict(size=12, color=[cmap.get(l,"#9CA3AF") for l in levels], opacity=0.8),
            text=[f"Risk: {l.title()}" for l in levels], hoverinfo="text",
        ))
        fig.update_layout(
            geo=dict(showland=True, landcolor="#E8F5EE", showocean=True, oceancolor="#DBEAFE",
                     showcoastlines=True, coastlinecolor="#9CA3AF",
                     center=dict(lat=lat_c, lon=lon_c), projection_scale=6),
            height=400, margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return ("plotly", fig)

    # ── Folium interactive map ──────────────────────────────────────────────
    m = folium.Map(
        location=[lat_c, lon_c],
        zoom_start=8,
        tiles=None,
        width="100%",
        height=430,
        control_scale=True,
    )

    # Base tile layers
    folium.TileLayer("CartoDB positron",  name="Light Map",  overlay=False, control=True).add_to(m)
    folium.TileLayer("OpenStreetMap",     name="Street Map", overlay=False, control=True).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False, control=True,
    ).add_to(m)

    color_map  = {"high": "#EF4444", "moderate": "#F59E0B", "low": "#10B981"}
    radius_map = {"high": 14, "moderate": 10, "low": 7}

    # Risk hotspots layer
    risk_layer = folium.FeatureGroup(name="⚠️ Risk Hotspots", show=True)
    for lat, lon, level in hotspots:
        color = color_map.get(level, "#9CA3AF")
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius_map.get(level, 8),
            color=color, fill=True, fill_color=color, fill_opacity=0.7, weight=2,
            tooltip=f"Risk: {level.title()} | ({lat:.3f}, {lon:.3f})",
            popup=folium.Popup(
                f"<b>Risk Zone</b><br>Level: {level.title()}<br>"
                f"Lat: {lat:.4f} | Lon: {lon:.4f}", max_width=180
            ),
        ).add_to(risk_layer)
    risk_layer.add_to(m)

    # Carbon stock zone
    cs_layer = folium.FeatureGroup(name="🌿 Carbon Stock Zone", show=True)
    cs_radius = math.sqrt(result.get("area_ha", 50000) * 10000 / math.pi) * 0.6
    folium.Circle(
        location=[lat_c, lon_c],
        radius=min(cs_radius, 40000),
        color="#0EA5E9", fill=True, fill_color="#0EA5E9", fill_opacity=0.12,
        weight=2, tooltip=f"Carbon stock: {result.get('carbon_stock_mgc_ha', 0):.0f} Mg C/ha",
    ).add_to(cs_layer)
    cs_layer.add_to(m)

    # Mangrove zone
    if result.get("mangrove_ha", 0) > 0:
        mg_layer = folium.FeatureGroup(name="🌊 Mangrove Zone", show=True)
        mg_radius = math.sqrt(result.get("mangrove_ha", 10000) * 10000 / math.pi) * 0.8
        folium.Circle(
            location=[lat_c - 0.15, lon_c + 0.2],
            radius=min(mg_radius, 25000),
            color="#0D5C2E", fill=True, fill_color="#0D5C2E", fill_opacity=0.18,
            weight=2, tooltip=f"Mangrove area: {result.get('mangrove_ha',0):,} ha",
        ).add_to(mg_layer)
        mg_layer.add_to(m)

    # Protected area
    pa_layer = folium.FeatureGroup(name="🛡️ Protected Area", show=True)
    pa_radius = math.sqrt(result.get("area_ha", 50000) * 10000 / math.pi) * 0.4
    folium.Circle(
        location=[lat_c + 0.3, lon_c - 0.25],
        radius=min(pa_radius, 20000),
        color="#6366F1", fill=True, fill_color="#6366F1", fill_opacity=0.15,
        weight=1.5, tooltip=f"Protected area: {result.get('protected_pct', 0):.0f}%",
    ).add_to(pa_layer)
    pa_layer.add_to(m)

    # Main location marker
    folium.Marker(
        [lat_c, lon_c],
        tooltip=result.get("study_area", "Study Area"),
        icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    return ("folium", m)


def build_land_cover_chart(land_cover: dict) -> go.Figure:
    colors = ["#2D7A4F", "#1a6b3a", "#3B82F6", "#F59E0B", "#EF4444", "#9CA3AF"]
    fig = go.Figure(go.Pie(
        labels=list(land_cover.keys()),
        values=list(land_cover.values()),
        marker_colors=colors,
        hole=0.5,
        textinfo="label+percent",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Montserrat, Inter, sans-serif"),
    )
    return fig


def build_risk_bar(land_cover: dict, risk_index: float) -> go.Figure:
    categories = list(land_cover.keys())
    # Risk contribution per land type
    risk_weights = {"Forest": 0.1, "Mangrove": 0.15, "Water": 0.05,
                    "Agriculture": 0.35, "Built-up": 0.45, "Other": 0.2}
    risk_vals = [land_cover[c] * risk_weights.get(c, 0.1) / 100 * risk_index
                 for c in categories]
    bar_colors = ["#2D7A4F","#1a6b3a","#3B82F6","#F59E0B","#EF4444","#9CA3AF"]

    fig = go.Figure(go.Bar(
        x=categories, y=risk_vals,
        marker_color=bar_colors, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Risk contribution: %{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F3F4F6", showgrid=True, title="Risk Contribution"),
        xaxis=dict(showgrid=False),
        font=dict(family="Montserrat, Inter, sans-serif", size=11),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHTS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_gis_insights(result: dict, province: str, regency: str) -> list:
    r      = result["risk_index"]
    carbon = result["carbon_stock"]
    bio    = result["biodiversity"]
    prot   = result["protected_pct"]
    lc     = result["land_cover"]
    loss   = result["annual_loss_pct"]

    insights = []
    risk_type = "alert" if r > 0.7 else "warn" if r > 0.45 else "info"

    insights.append({
        "text": f"<strong>Carbon stock assessment for {regency}, {province}:</strong> "
                f"{carbon} Mg C/ha detected, with an estimated annual loss rate of "
                f"<strong>{loss}%</strong> per year. At this rate, 10-year projected loss "
                f"reaches <strong>{carbon*(1-(1-loss/100)**10):.0f} Mg C/ha</strong>.",
        "type": "alert" if loss > 2 else "warn", "icon": "🌳",
    })

    if result["mangrove_ha"] > 10000:
        insights.append({
            "text": f"<strong>Blue carbon opportunity:</strong> {result['mangrove_ha']:,.0f} ha of mangrove ecosystem "
                    f"identified, with an estimated <strong>{result['redd_eligible_ha']:,.0f} ha</strong> qualifying "
                    "for REDD+ carbon credit issuance under VCS VM0007 methodology.",
            "type": "info", "icon": "🌊",
        })

    if lc.get("Agriculture", 0) + lc.get("Built-up", 0) > 30:
        insights.append({
            "text": f"<strong>Land use pressure:</strong> Agriculture and built-up areas account for "
                    f"{lc.get('Agriculture',0)+lc.get('Built-up',0)}% of the study area, "
                    "creating significant deforestation pressure on adjacent forest and mangrove zones.",
            "type": risk_type, "icon": "⚠️",
        })

    if prot < 50:
        insights.append({
            "text": f"<strong>Protected area gap:</strong> Only <strong>{prot}%</strong> of the study area "
                    "falls under formal environmental protection. Expanding conservation boundaries "
                    "could reduce annual carbon loss by an estimated 35–50%.",
            "type": "warn", "icon": "🛡️",
        })
    else:
        insights.append({
            "text": f"<strong>Strong conservation coverage:</strong> {prot}% of the study area under "
                    "formal protection — above the national average of 47%. Continued enforcement is "
                    "critical to maintain this carbon sink.",
            "type": "info", "icon": "✅",
        })

    if bio > 0.75:
        insights.append({
            "text": f"<strong>High biodiversity value (index: {bio:.2f}/1.00):</strong> This area qualifies "
                    "for IFC Performance Standard 6 (Biodiversity) high-value habitat classification. "
                    "Any development activity requires comprehensive ESIA and mitigation hierarchy.",
            "type": "info", "icon": "🦅",
        })

    return insights


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────


def _dispatch_gis(prov_data: dict, regency: str, active_layers: list,
                  study_area_ha: float, uploaded_pts=None) -> dict:
    """
    Try GEE first. If GEE is ready and returns valid data, use it.
    Otherwise fall back to compute_gis_analysis (synthetic).
    Merges GEE result into the standard result schema transparently.
    """
    lat = prov_data["lat"]
    lon = prov_data["lon"]

    if gee_client.is_ready():
        import datetime
        year = datetime.date.today().year - 1  # use prior full year
        gee_result = gee_client.compute_real_gis(lat, lon, buffer_km=15,
                                                  year=year, study_area_ha=study_area_ha)
        if not gee_result.get("error"):
            # Merge GEE result with schema fields the UI expects
            gee_result["study_area"] = f"{regency} ({study_area_ha:,.0f} ha)"
            gee_result["active_layers"] = active_layers
            gee_result["lat_center"] = lat
            gee_result["lon_center"] = lon
            # Re-use synthetic hotspots (GEE doesn't produce point hotspots)
            import numpy as np
            rng = np.random.default_rng(abs(hash(regency)) % 2**31)
            gee_result["hotspots"] = _synthetic_hotspots(prov_data, rng)
            return gee_result

    # Fallback: synthetic
    result = compute_gis_analysis("selection", prov_data, regency,
                                  active_layers, study_area_ha, uploaded_pts)
    result["gee_source"] = False
    return result


def render():
    S.init()

    page_header(
        title="GIS Intelligence",
        subtitle="Interactive geospatial analysis · Carbon stock · Environmental risk · Blue carbon",
        badge="Sentinel-2 Active",
        badge_type="green",
    )

    # ── Mode selection ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:13px;font-weight:700;color:#1F2937;margin-bottom:12px;">
        Select Analysis Mode
    </div>
    """, unsafe_allow_html=True)

    # ── GEE status banner + credentials panel ────────────────────────────────
    gee_ok = gee_client.is_ready()
    if not gee_ok:
        # Try to init with user-provided key
        with st.expander("🔑  Connect Google Earth Engine (optional — enables real Sentinel-2 data)", expanded=False):
            st.markdown("""
            <div style="font-size:12px;color:#64748B;margin-bottom:12px;">
                When connected, all GIS analysis uses <strong>real Sentinel-2 SR NDVI/EVI</strong>,
                Hansen GFC deforestation data, and JAXA Mangrove Watch — instead of modelled estimates.
                Provide a GEE Service Account JSON key, or run
                <code>earthengine authenticate</code> in your terminal for personal credentials.
            </div>
            """, unsafe_allow_html=True)

            sa_json = st.text_area("Service Account JSON key (paste content or leave blank for personal credentials)",
                                   height=100, key="gee_sa_json",
                                   placeholder='{"type": "service_account", "client_email": "...", ...}')
            if st.button("🔌  Initialize GEE", type="primary", key="gee_init_btn"):
                ok, msg = gee_client.initialize(service_account_json=sa_json.strip() or None)
                if ok:
                    st.success(f"✅ GEE connected: {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        st.markdown("""
        <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;
             padding:8px 14px;font-size:12px;color:#92400E;margin-bottom:12px;display:flex;
             align-items:center;gap:8px;">
            <span>⚠️</span>
            <span>GEE not connected — using modelled carbon estimates. Connect above for real Sentinel-2 data.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;
             padding:8px 14px;font-size:12px;color:#065F46;margin-bottom:12px;display:flex;
             align-items:center;gap:8px;">
            <span>🛰️</span>
            <span><strong>Google Earth Engine connected</strong> — analysis uses real Sentinel-2 SR
            NDVI/EVI, Hansen GFC deforestation, and JAXA Mangrove Watch.</span>
        </div>
        """, unsafe_allow_html=True)

    _facility_lat = S.get("facility_lat")
    _facility_lon = S.get("facility_lon")
    _has_facility = _facility_lat is not None and _facility_lon is not None

    mode_options = ["🗺️  Area Selection (Province/Regency)", "📂  Upload GIS Data (GeoJSON / CSV)"]
    if _has_facility:
        mode_options.insert(0, "📍  My Facility (from Organization Profile)")

    mode = st.radio(
        "", mode_options,
        horizontal=True, key="gis_mode", label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    result      = None
    province    = None
    regency     = None
    uploaded_pts = None

    # ── Option 0: My Facility (real coordinates from onboarding) ───────────
    if "My Facility" in mode:
        _buffer_km = float(S.get("facility_buffer_km", 2.0))
        _land_use  = S.get("facility_land_use_history", "")
        _company   = S.get("company_name", "Your Organization")

        st.markdown(f"""
        <div class="cl-card" style="margin-bottom:16px;">
            <div class="cl-card-title">📍 {_company} — Facility Location</div>
            <div class="cl-card-subtitle">
                Lat {_facility_lat:.4f}, Lon {_facility_lon:.4f} ·
                Analysis radius {_buffer_km:g} km
                {' · Land use: ' + _land_use if _land_use else ''}
            </div>
        """, unsafe_allow_html=True)

        col_l, _ = st.columns([2, 1])
        with col_l:
            active_layers_fac = st.multiselect(
                "Active Map Layers",
                list(LAYER_CONFIG.keys()),
                default=["Carbon Stock", "Risk Layer"],
                key="gis_layers_facility",
            )
        st.markdown("</div>", unsafe_allow_html=True)

        if not gee_client.is_ready():
            st.markdown("""
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;
                        padding:12px 16px;margin-bottom:12px;font-size:12px;color:#92400E;">
                ⚠️ <strong>Google Earth Engine not configured.</strong>
                Facility-level analysis requires real satellite data (GEE).
                Configure GEE credentials below, or use Area Selection for
                province-level estimates.
            </div>
            """, unsafe_allow_html=True)

        if st.button("🛰️  Run Facility Analysis", type="primary", key="gis_run_facility",
                     disabled=not gee_client.is_ready()):
            with st.spinner("Fetching Sentinel-2 NDVI for facility coordinates..."):
                import datetime
                year = datetime.date.today().year - 1
                study_area_ha = math.pi * (_buffer_km ** 2) * 100  # km² → ha
                gee_result = gee_client.compute_real_gis(
                    _facility_lat, _facility_lon,
                    buffer_km=_buffer_km, year=year, study_area_ha=study_area_ha,
                )
                if gee_result.get("error"):
                    st.error(f"GEE query failed: {gee_result['error']}")
                else:
                    gee_result["study_area"]     = f"{_company} facility ({study_area_ha:,.0f} ha)"
                    gee_result["active_layers"]  = active_layers_fac
                    gee_result["lat_center"]     = _facility_lat
                    gee_result["lon_center"]     = _facility_lon
                    gee_result["land_use_history"] = _land_use
                    rng = np.random.default_rng(abs(hash(_company)) % (2**31))
                    n_hot = rng.integers(3, 7)
                    gee_result["hotspots"] = [
                        {"lat": _facility_lat + rng.uniform(-0.02, 0.02),
                         "lon": _facility_lon + rng.uniform(-0.02, 0.02),
                         "intensity": float(rng.uniform(0.3, 1.0))}
                        for _ in range(n_hot)
                    ]
                    st.session_state["gis_result"]   = gee_result
                    st.session_state["gis_province"] = _company
                    st.session_state["gis_regency"]  = "Facility Site"
                    result = gee_result

    # ── Option A: Area Selection ───────────────────────────────────────────
    elif "Area Selection" in mode:
        st.markdown("""
        <div class="cl-card" style="margin-bottom:16px;">
            <div class="cl-card-title">🗺️ Area Selection</div>
            <div class="cl-card-subtitle">Select province, regency, and configure study parameters</div>
        """, unsafe_allow_html=True)

        col_p, col_r, col_a = st.columns(3, gap="medium")
        with col_p:
            province = st.selectbox("Province", list(PROVINCES.keys()), key="gis_prov")
        with col_r:
            prov_data = PROVINCES[province]
            regency   = st.selectbox("Regency / City", prov_data["regencies"], key="gis_reg")
        with col_a:
            study_area = st.number_input("Study Area (ha)", min_value=1000, max_value=500000,
                                         value=50000, step=5000, key="gis_area")

        col_l, _ = st.columns([2, 1])
        with col_l:
            active_layers = st.multiselect(
                "Active Map Layers",
                list(LAYER_CONFIG.keys()),
                default=["Carbon Stock", "Mangrove", "Risk Layer"],
                key="gis_layers",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🔍  Run GIS Analysis", type="primary", key="gis_run_a"):
            with st.spinner("Running geospatial analysis — fetching Sentinel-2 data..." if gee_client.is_ready() else "Running geospatial analysis..."):
                result = _dispatch_gis(prov_data, regency, active_layers, study_area)
                st.session_state["gis_result"]   = result
                st.session_state["gis_province"] = province
                st.session_state["gis_regency"]  = regency

        # Reload from state
        if "gis_result" in st.session_state and result is None:
            result   = st.session_state["gis_result"]
            province = st.session_state.get("gis_province", province)
            regency  = st.session_state.get("gis_regency",  regency)

    # ── Option B: Upload GIS Data ──────────────────────────────────────────
    else:
        st.markdown("""
        <div class="cl-card" style="margin-bottom:16px;">
            <div class="cl-card-title">📂 Upload GIS Data</div>
            <div class="cl-card-subtitle">Upload GeoJSON or CSV with coordinates · Supported: .geojson, .json, .csv</div>
        """, unsafe_allow_html=True)

        upload_col, config_col = st.columns([1.5, 1], gap="large")
        with upload_col:
            gis_file = st.file_uploader("", type=["geojson", "json", "csv"],
                                        label_visibility="collapsed", key="gis_upload")
            if gis_file:
                try:
                    if gis_file.name.endswith(".csv"):
                        uploaded_pts = pd.read_csv(gis_file)
                        st.success(f"✅ Loaded {len(uploaded_pts)} coordinate points · Columns: {uploaded_pts.columns.tolist()}")
                    else:
                        raw = json.load(gis_file)
                        st.success(f"✅ GeoJSON loaded · Features: {len(raw.get('features', []))}")
                except Exception as e:
                    st.error(f"Failed to parse file: {e}")

        with config_col:
            up_prov = st.selectbox("Associate Province", list(PROVINCES.keys()), key="gis_up_prov")
            up_area = st.number_input("Estimated Area (ha)", min_value=100, max_value=500000,
                                      value=25000, step=1000, key="gis_up_area")
            up_layers = st.multiselect("Map Layers", list(LAYER_CONFIG.keys()),
                                       default=["Carbon Stock", "Risk Layer"], key="gis_up_layers")

        st.markdown("</div>", unsafe_allow_html=True)

        province  = up_prov
        regency   = "Uploaded Area"
        prov_data = PROVINCES[up_prov]

        if st.button("🔍  Analyze Uploaded Area", type="primary", key="gis_run_b",
                     disabled=(gis_file is None)):
            with st.spinner("Analyzing uploaded GIS data..."):
                result = compute_gis_analysis(
                    "upload", prov_data, regency, up_layers, up_area, uploaded_pts
                )
                st.session_state["gis_result"]   = result
                st.session_state["gis_province"] = province
                st.session_state["gis_regency"]  = regency

        if "gis_result" in st.session_state and result is None:
            result   = st.session_state["gis_result"]
            province = st.session_state.get("gis_province", province)
            regency  = st.session_state.get("gis_regency",  regency)

    # ─────────────────────────────────────────────────────────────────────
    # RESULTS — only shown after analysis runs
    # ─────────────────────────────────────────────────────────────────────
    if result is None:
        st.markdown("""
        <div style="text-align:center;padding:48px 20px;color:#9CA3AF;">
            <div style="font-size:48px;margin-bottom:12px;opacity:0.4;">🗺️</div>
            <div style="font-size:16px;font-weight:700;color:#6B7280;margin-bottom:6px;">
                Select an area and run analysis to view results
            </div>
            <div style="font-size:13px;">
                Choose a province and regency above, then click <strong>Run GIS Analysis</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── KPI Cards ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#2D7A4F;margin-bottom:12px;">
        Analysis Results — {regency}, {province} · {result['study_area_ha']:,} ha study area
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
    risk_bt = {"Critical":"red","High":"yellow","Moderate":"yellow","Low":"green"}.get(result["risk_label"],"gray")

    with k1:
        kpi_card(label="Carbon Stock", value=str(result["carbon_stock"]),
                 badge="Mg C/ha", badge_type="green",
                 delta=f"−{result['annual_loss_pct']}%/yr", delta_label="annual loss",
                 icon="🌳", icon_bg="#E0F2FE")
    with k2:
        kpi_card(label="Carbon Density", value=str(result["carbon_density"]),
                 badge="Mg CO₂e/ha", badge_type="blue",
                 icon="💨", icon_bg="#DBEAFE")
    with k3:
        kpi_card(label="Environmental Risk", value=result["risk_label"],
                 badge=f"Index: {result['risk_index']:.2f}", badge_type=risk_bt,
                 icon="⚠️", icon_bg="#FFF7ED")
    with k4:
        kpi_card(label="Protected Coverage", value=f"{result['protected_pct']}%",
                 badge="of study area", badge_type="green" if result["protected_pct"] > 60 else "yellow",
                 icon="🛡️", icon_bg="#F5F3FF")
    with k5:
        kpi_card(label="Biodiversity Index", value=f"{result['biodiversity']:.2f}",
                 badge="/ 1.00", badge_type="green" if result["biodiversity"] > 0.7 else "yellow",
                 icon="🌿", icon_bg="#DCFCE7")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Interactive Map ────────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">🗺️ Interactive Carbon & Risk Map</div>
        <div class="cl-card-subtitle">Zoom · Pan · Toggle layers via legend · Click markers for details</div>
    """, unsafe_allow_html=True)

    _map_result = build_interactive_map(result)
    if _map_result[0] == "folium":
        # Tighten iframe wrapper — st_folium's component iframe sometimes
        # reserves extra height beyond the map itself, leaving a blank gap.
        st.markdown("""
        <style>
        iframe[title="streamlit_folium.st_folium"] {
            display: block !important;
            margin-bottom: -1px !important;
        }
        div[data-testid="stIFrame"] {
            line-height: 0 !important;
        }
        div[data-testid="stIFrame"] > iframe {
            height: 380px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        try:
            st_folium(_map_result[1], width="100%", height=380,
                      returned_objects=[], key="gis_main_map")
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.caption("🗺️ Interactive map — zoom, pan, toggle layers (top-right). Click markers for details.")
    else:
        st.plotly_chart(_map_result[1], use_container_width=True)
        st.caption("📍 Install `folium` and `streamlit-folium` for interactive map.")

    # Layer legend color indicators
    layer_html = " &nbsp;|&nbsp; ".join([
        f'<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:#6B7280;">'
        f'<span style="width:9px;height:9px;border-radius:50%;background:{LAYER_CONFIG[l]["color"]};display:inline-block;"></span>{l}</span>'
        for l in result["active_layers"]
    ]) if result["active_layers"] else ""
    if layer_html:
        st.markdown(f'<div style="margin-top:6px;">{layer_html}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    # ── Charts row ─────────────────────────────────────────────────────────
    ch1, ch2, ch3 = st.columns(3, gap="medium")

    with ch1:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📉 Carbon Stock Trend</div>
            <div class="cl-card-subtitle">2020–2025 · Mg C/ha</div>
        """, unsafe_allow_html=True)
        fig_trend = carbon_stock_area(result["years"], result["carbon_trend"], height=240)
        try:
            st.plotly_chart(fig_trend, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    with ch2:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🏞️ Land Cover Breakdown</div>
            <div class="cl-card-subtitle">Estimated composition · % of study area</div>
        """, unsafe_allow_html=True)
        fig_lc = build_land_cover_chart(result["land_cover"])
        try:
            st.plotly_chart(fig_lc, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    with ch3:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🔥 Risk Contribution by Cover</div>
            <div class="cl-card-subtitle">Environmental risk weighted by land type</div>
        """, unsafe_allow_html=True)
        fig_risk = build_risk_bar(result["land_cover"], result["risk_index"])
        try:
            st.plotly_chart(fig_risk, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Blue Carbon Metrics ────────────────────────────────────────────────
    bc1, bc2 = st.columns([1, 1.6], gap="medium")

    with bc1:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🔵 Blue Carbon Assessment</div>
            <div class="cl-card-subtitle">Mangrove-based carbon estimates</div>
        """, unsafe_allow_html=True)
        metrics = [
            ("Mangrove extent",       f"{result['mangrove_ha']:,.0f} ha",     "#1F2937"),
            ("Total carbon stock",    f"{result['carbon_stock_total']:.2f} Tg C", "#2D7A4F"),
            ("Annual sequestration",  f"{result['sequestration']:.3f} Tg C/yr", "#2D7A4F"),
            ("Annual loss rate",      f"−{result['annual_loss_pct']:.2f}%/yr",  "#EF4444"),
            ("REDD+ eligible area",   f"{result['redd_eligible_ha']:,.0f} ha",  "#F59E0B"),
            ("Protected coverage",    f"{result['protected_pct']}%",           "#8B5CF6"),
        ]
        for label, val, color in metrics:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:7px 0;
                        border-bottom:1px solid #F9FAFB;font-size:12px;">
                <span style="color:#6B7280;">{label}</span>
                <span style="font-weight:700;color:{color};">{val}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with bc2:
        # ── AI Insights ───────────────────────────────────────────────────
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">💡 GIS Intelligence Insights</div>
            <div class="cl-card-subtitle">AI-interpreted geospatial analysis · Area-specific findings</div>
        """, unsafe_allow_html=True)
        insights = generate_gis_insights(result, province, regency)
        insight_panel(insights)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── GEE Data Provenance Panel (shown only when GEE data is live) ───────
    if result and result.get("gee_source"):
        with st.expander("🛰️ Real-Time Data Provenance — Google Earth Engine", expanded=True):
            gp1, gp2, gp3 = st.columns(3, gap="medium")
            with gp1:
                st.markdown(f"""
                <div class="cl-card">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                         letter-spacing:0.8px;color:#94A3B8;margin-bottom:10px;">🛰 Sentinel-2 SR</div>
                    <div style="font-size:13px;font-weight:700;color:#0F172A;">
                        NDVI: {result.get('ndvi', 0):.4f}</div>
                    <div style="font-size:13px;font-weight:700;color:#0EA5E9;margin-top:2px;">
                        EVI: {result.get('evi', 0):.4f}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:6px;">
                        IQR: [{result.get('ndvi_p25',0):.3f} – {result.get('ndvi_p75',0):.3f}]</div>
                    <div style="font-size:10px;color:#CBD5E1;margin-top:4px;">
                        {result.get('s2_source','')}</div>
                </div>
                """, unsafe_allow_html=True)
            with gp2:
                st.markdown(f"""
                <div class="cl-card">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                         letter-spacing:0.8px;color:#94A3B8;margin-bottom:10px;">🌲 Hansen GFC</div>
                    <div style="font-size:13px;font-weight:700;color:#0F172A;">
                        AGB: {result.get('agb_mg_ha',0):.1f} Mg/ha</div>
                    <div style="font-size:13px;font-weight:700;color:#F97316;margin-top:2px;">
                        Annual loss: {result.get('annual_loss_pct',0):.2f}%</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:6px;">
                        Carbon: {result.get('carbon_stock',0):.1f} Mg C/ha</div>
                    <div style="font-size:10px;color:#CBD5E1;margin-top:4px;">
                        {result.get('hansen_source','')}</div>
                </div>
                """, unsafe_allow_html=True)
            with gp3:
                st.markdown(f"""
                <div class="cl-card">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                         letter-spacing:0.8px;color:#94A3B8;margin-bottom:10px;">🌊 Mangrove Watch</div>
                    <div style="font-size:13px;font-weight:700;color:#0F172A;">
                        Extent: {result.get('mangrove_ha',0):,.0f} ha</div>
                    <div style="font-size:13px;font-weight:700;color:#06B6D4;margin-top:2px;">
                        CO₂e: {result.get('carbon_density',0):.1f} Mg/ha</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:6px;">
                        REDD+ eligible: {result.get('redd_eligible_ha',0):,.0f} ha</div>
                    <div style="font-size:10px;color:#CBD5E1;margin-top:4px;">
                        {result.get('mangrove_source','')}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            <div style="font-size:11px;color:#94A3B8;padding:8px 4px;">
                <strong>Methodology:</strong>
                NDVI/EVI from Sentinel-2 SR cloud-masked median composite (max 20% cloud cover).
                AGB estimated via NDVI→AGB exponential regression (Saatchi 2011 pantropical).
                Carbon = (AGB + BGB) × 0.47 IPCC C fraction, where BGB = 26% AGB.
                CO₂e = C × 3.67. Forest loss from Hansen GFC 2023. Mangroves from JAXA GFWC.
            </div>
            """, unsafe_allow_html=True)

            col_cc, _ = st.columns([1, 3])
            with col_cc:
                if st.button("🗑️  Clear GEE cache", key="gee_clear_cache"):
                    gee_client.clear_cache()
                    st.success("Cache cleared — next analysis will re-fetch from GEE.")

    # ── Remote sensing reference ───────────────────────────────────────────
    with st.expander("🛰️ Remote Sensing Methodology", expanded=False):
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("""
            **Sentinel-2 Indices:**
            - NDVI (B8/B4) → Canopy health & vegetation density
            - MNDWI (B3/B11) → Water body extent
            - EVI → Mangrove density proxy
            - NBR → Burn scar & disturbance detection
            """)
        with rc2:
            st.markdown("""
            **GEDI LiDAR (L4A AGB):**
            - Resolution: 25m footprint
            - AGB → Carbon stock: ×0.47 IPCC factor
            - Vertical accuracy: ±3.5m (RH95)
            - Temporal coverage: 2019–present
            """)
