"""Streamlit user interface for the PTES screening tool."""

from __future__ import annotations

import io
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium

from calculations import (
    darcy_weisbach_pressure_loss,
    required_flow,
    size_connection_pipe,
    storage_capacity,
    suitability_score,
)
from gis_analysis import clean_geometry, local_metric_crs, nearby_demand, nearest_pipe_connection, split_layers


st.set_page_config(page_title="PTES Screening Tool", page_icon="♨️", layout="wide")
st.title("PTES Location Screening and Design Tool")
st.caption("Preliminary spatial, thermal and hydraulic screening—not a final engineering design.")

with st.sidebar:
    st.header("1. Network data")
    uploaded = st.file_uploader("Upload nPro GeoJSON", type=["geojson", "json"])
    st.header("2. PTES design")
    volume = st.number_input("Storage volume [m³]", min_value=1.0, value=138000.0)
    t_max = st.number_input("Maximum temperature [°C]", value=90.0)
    t_min = st.number_input("Minimum temperature [°C]", value=15.0)
    efficiency = st.slider("Storage efficiency", 0.50, 1.00, 0.80)
    power = st.number_input("Charge/discharge power [kW]", min_value=1.0, value=3300.0)
    design_delta_t = st.number_input("Hydraulic design ΔT [K]", min_value=1.0, value=30.0)
    length = st.number_input("PTES top length [m]", min_value=1.0, value=124.0)
    width = st.number_input("PTES top width [m]", min_value=1.0, value=115.0)
    land_factor = st.number_input("Land allowance factor", min_value=1.0, value=1.5)
    available_land = st.number_input("Available land [m²]", min_value=1.0, value=25000.0)
    reference_demand = st.number_input("Reference demand [MWh/year]", min_value=1.0, value=10000.0)

if uploaded is None:
    st.info("Upload an nPro GeoJSON file to begin.")
    st.stop()

try:
    gdf = gpd.read_file(io.BytesIO(uploaded.getvalue()))
    if gdf.crs is None:
        st.warning("The uploaded file has no CRS. EPSG:4326 is being assumed.")
        gdf = gdf.set_crs(4326)
    buildings, pipes = split_layers(gdf)
    metric_crs = local_metric_crs(gdf)
    buildings_m = clean_geometry(buildings.to_crs(metric_crs))
    pipes_m = clean_geometry(pipes.to_crs(metric_crs))
except Exception as exc:
    st.error(f"The GeoJSON could not be prepared: {exc}")
    st.stop()

candidate_columns = [c for c in buildings_m.columns if c != "geometry"]
suggested = [c for c in candidate_columns if any(k in c.lower() for k in ("heat", "demand", "mwh", "wärme", "waerme"))]
default_index = candidate_columns.index(suggested[0]) if suggested else 0
demand_col = st.selectbox("Annual heat-demand column", candidate_columns, index=default_index)
buildings_m[demand_col] = pd.to_numeric(buildings_m[demand_col], errors="coerce").fillna(0)

buildings_wgs = buildings_m.to_crs(4326)
pipes_wgs = pipes_m.to_crs(4326)
bounds = pipes_wgs.total_bounds
center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
fmap = folium.Map(location=center, zoom_start=15, tiles="OpenStreetMap")
folium.GeoJson(buildings_wgs, name="Buildings", style_function=lambda _: {"color": "#666", "weight": 1, "fillColor": "#f6a623", "fillOpacity": 0.25}).add_to(fmap)
folium.GeoJson(pipes_wgs, name="District-heating pipes", style_function=lambda _: {"color": "#1677ff", "weight": 3}).add_to(fmap)
folium.LayerControl().add_to(fmap)

st.subheader("Select the candidate location")
st.write("Click once on the map. The selected coordinates will appear below it.")
map_state = st_folium(fmap, height=560, width=None, returned_objects=["last_clicked"])
clicked = map_state.get("last_clicked") if map_state else None

if not clicked:
    st.info("Waiting for a PTES location: click on the map.")
    st.stop()

latitude, longitude = clicked["lat"], clicked["lng"]
st.write(f"Selected point: **{latitude:.6f}, {longitude:.6f}**")

if st.button("Run PTES analysis", type="primary"):
    try:
        point_wgs = gpd.GeoSeries([Point(longitude, latitude)], crs=4326)
        point_m = point_wgs.to_crs(metric_crs).iloc[0]
        _, connection = nearest_pipe_connection(point_m, pipes_m)
        connection_m = float(connection["length_m"].iloc[0])
        demand_table = nearby_demand(point_m, buildings_m, demand_col)
        demand_500 = float(demand_table.loc[demand_table["Radius [m]"] == 500, "Annual demand [MWh]"].iloc[0])

        capacity = storage_capacity(volume, t_max, t_min, efficiency)
        flow = required_flow(power, design_delta_t)
        dn_table, dn, diameter, velocity = size_connection_pipe(flow["volume_flow_m3_s"])
        pressure = darcy_weisbach_pressure_loss(connection_m, diameter, velocity)
        required_land = length * width * land_factor
        score, status, criteria = suitability_score(
            available_land / required_land, connection_m, demand_500,
            pressure["pressure_risk"], reference_demand,
        )
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        st.stop()

    a, b, c, d = st.columns(4)
    a.metric("Suitability", status)
    b.metric("Score", f"{score:.1f}%")
    c.metric("Connection", f"{connection_m:.1f} m")
    d.metric("Recommended pipe", f"DN {dn}")
    e, f, g, h = st.columns(4)
    e.metric("Useful capacity", f"{capacity['useful_capacity_mwh']:.0f} MWh")
    f.metric("Required flow", f"{flow['volume_flow_m3_h']:.1f} m³/h")
    g.metric("Pressure loss", f"{pressure['pressure_loss_bar']:.3f} bar")
    h.metric("Demand within 500 m", f"{demand_500:.0f} MWh/a")

    tab1, tab2, tab3 = st.tabs(["Demand", "Pipe sizing", "Suitability"])
    tab1.dataframe(demand_table, use_container_width=True)
    tab2.dataframe(dn_table, use_container_width=True)
    tab3.dataframe(criteria, use_container_width=True)

    summary = pd.DataFrame({
        "Parameter": ["Latitude", "Longitude", "Useful capacity [MWh]", "Connection [m]", "DN", "Flow [m³/h]", "Pressure loss [bar]", "Demand 500 m [MWh/a]", "Score [%]", "Status"],
        "Value": [latitude, longitude, capacity["useful_capacity_mwh"], connection_m, dn, flow["volume_flow_m3_h"], pressure["pressure_loss_bar"], demand_500, score, status],
    })
    st.download_button("Download result CSV", summary.to_csv(index=False).encode("utf-8"), "ptes_result.csv", "text/csv")

st.divider()
st.caption("Verify pipe material, internal diameter, roughness, fittings, operating cases and network constraints in detailed engineering software before design approval.")
