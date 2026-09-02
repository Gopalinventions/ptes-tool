import io
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium.features import GeoJsonPopup
from shapely.affinity import rotate, translate
from shapely.geometry import Point, box
from streamlit_folium import st_folium

from calculations import storage_capacity, required_flow, size_connection_pipe, darcy_weisbach_pressure_loss, suitability_score
from gis_analysis import clean_geometry, local_metric_crs, nearby_demand, nearest_pipe_connection, split_layers

st.set_page_config(page_title="PTES Comparison Tool", page_icon="♨️", layout="wide")
st.title("PTES Location and Network Integration Tool")
st.caption("Place and compare Storage A, B and C. Click buildings and pipes to inspect nPro data.")

if "candidates" not in st.session_state:
    st.session_state.candidates = {}

BUILDING_FIELDS = {
    "b_building_name": "Building", "b_addr_street": "Street",
    "b_addr_house_number": "House number", "b_building_type": "Building type",
    "b_year_constr": "Construction year", "b_floor_area_m2": "Floor area [m²]",
    "b_heat_import_sum_MWh": "Heat import [MWh/year]",
    "b_space_heat_sum_MWh": "Space heat [MWh/year]",
    "b_heat_import_max_kW": "Peak heat [kW]",
    "b_supply_temp_heat_degC": "Supply temperature [°C]",
}
PIPE_FIELDS = {
    "p_pipe_id": "Pipe ID", "p_pipe_model": "Pipe model", "p_diameter_DN": "DN",
    "p_length_m": "Length [m]", "p_is_existing_option": "Existing pipe",
    "p_mean_temp_supply_degC": "Supply temperature [°C]",
    "p_mean_temp_return_degC": "Return temperature [°C]",
    "p_abs_pres_supply_bar": "Supply pressure [bar]",
    "p_abs_pres_return_bar": "Return pressure [bar]",
    "p_abs_pres_supply_sim_bar": "Simulated supply pressure [bar]",
    "p_abs_pres_return_sim_bar": "Simulated return pressure [bar]",
    "p_pressure_loss_rel_sim_Pa_m": "Simulated loss [Pa/m]",
    "p_max_flow_velocity_m_s": "Maximum velocity [m/s]",
    "p_max_power_possible_kW": "Possible power [kW]",
}
COLORS = {"Storage A": "green", "Storage B": "orange", "Storage C": "purple"}


def json_safe(layer):
    layer = layer.copy()
    for col in layer.columns:
        if col != layer.geometry.name:
            layer[col] = layer[col].map(lambda x: None if pd.isna(x) else x if isinstance(x, (str, int, float, bool)) else str(x))
    return layer


def add_layer(fmap, layer, name, definitions, style, highlight):
    fields = [f for f in definitions if f in layer.columns]
    popup = GeoJsonPopup(fields, [definitions[f] for f in fields], localize=True) if fields else None
    folium.GeoJson(layer, name=name, style_function=lambda _: style,
                   highlight_function=lambda _: highlight, popup=popup).add_to(fmap)


def add_network(fmap, buildings, pipes):
    add_layer(fmap, buildings, "Buildings — click for details", BUILDING_FIELDS,
              {"color": "#555", "weight": 1, "fillColor": "#F3A712", "fillOpacity": .28},
              {"weight": 3, "fillOpacity": .5})
    add_layer(fmap, pipes, "Pipes — click for details", PIPE_FIELDS,
              {"color": "#1677FF", "weight": 4}, {"color": "#00B8D9", "weight": 7})


def marker(fmap, name, lat, lon, result=None):
    text = f"<b>{name}</b><br>Latitude: {lat:.6f}<br>Longitude: {lon:.6f}"
    if result:
        text += f"<br>Score: {result['Score [%]']:.1f}%<br>Status: {result['Status']}<br>Connection: {result['Connection [m]']:.1f} m<br>DN: {result['DN']}"
    folium.Marker([lat, lon], tooltip=name, popup=folium.Popup(text, max_width=320),
                  icon=folium.Icon(color=COLORS[name], icon="info-sign")).add_to(fmap)


with st.sidebar:
    uploaded = st.file_uploader("Upload nPro GeoJSON", type=["geojson", "json"])
    st.header("PTES design")
    volume = st.number_input("Storage volume [m³]", 1.0, value=138000.0)
    tmax = st.number_input("Maximum temperature [°C]", value=90.0)
    tmin = st.number_input("Minimum temperature [°C]", value=15.0)
    efficiency = st.slider("Efficiency", .5, 1.0, .8)
    power = st.number_input("Charge/discharge power [kW]", 1.0, value=3300.0)
    delta_t = st.number_input("Design ΔT [K]", 1.0, value=30.0)
    length = st.number_input("Top length [m]", 1.0, value=124.0)
    width = st.number_input("Top width [m]", 1.0, value=115.0)
    rotation = st.number_input("Rotation [degrees]", value=0.0)
    land_factor = st.number_input("Land allowance factor", 1.0, value=1.5)
    available_land = st.number_input("Available land [m²]", 1.0, value=25000.0)
    reference_demand = st.number_input("Reference demand [MWh/year]", 1.0, value=10000.0)

if uploaded is None:
    st.info("Upload an nPro GeoJSON file to start.")
    st.stop()

try:
    data = gpd.read_file(io.BytesIO(uploaded.getvalue()))
    if data.crs is None:
        data = data.set_crs(4326)
        st.warning("No CRS was supplied; EPSG:4326 was assumed.")
    buildings, pipes = split_layers(data)
    metric_crs = local_metric_crs(data)
    buildings_m, pipes_m = clean_geometry(buildings.to_crs(metric_crs)), clean_geometry(pipes.to_crs(metric_crs))
except Exception as exc:
    st.error(f"Could not prepare GeoJSON: {exc}")
    st.stop()

demand_options = [c for c in buildings_m.columns if c != "geometry"]
preferred = next((c for c in ("b_heat_import_sum_MWh", "b_space_heat_sum_MWh") if c in demand_options), demand_options[0])
demand_col = st.selectbox("Annual heat-demand column", demand_options, index=demand_options.index(preferred))
buildings_m[demand_col] = pd.to_numeric(buildings_m[demand_col], errors="coerce").fillna(0)
buildings_wgs, pipes_wgs = json_safe(buildings_m.to_crs(4326)), json_safe(pipes_m.to_crs(4326))
b = pipes_wgs.total_bounds
center = [(b[1] + b[3]) / 2, (b[0] + b[2]) / 2]

st.subheader("Candidate placement")
slot = st.radio("Candidate to place", list(COLORS), horizontal=True)
placement = st.toggle("Placement mode", True, help="Turn off to inspect popups without moving a candidate.")
c1, c2, _ = st.columns([1, 1, 4])
if c1.button("Remove selected"):
    st.session_state.candidates.pop(slot, None)
    st.rerun()
if c2.button("Clear all"):
    st.session_state.candidates = {}
    st.rerun()

select_map = folium.Map(center, zoom_start=15)
add_network(select_map, buildings_wgs, pipes_wgs)
for name, xy in st.session_state.candidates.items():
    marker(select_map, name, xy["lat"], xy["lon"])
folium.LayerControl(collapsed=False).add_to(select_map)
state = st_folium(select_map, height=620, width=None, key="selection", returned_objects=["last_clicked"])
clicked = state.get("last_clicked") if state else None
if placement and clicked:
    point = {"lat": float(clicked["lat"]), "lon": float(clicked["lng"])}
    if st.session_state.candidates.get(slot) != point:
        st.session_state.candidates[slot] = point
        st.rerun()
st.caption("Placement ON: click to position the selected storage. Placement OFF: inspect building and pipeline popups.")

candidate_table = pd.DataFrame([{"Candidate": n, "Latitude": v["lat"], "Longitude": v["lon"]} for n, v in st.session_state.candidates.items()])
if not candidate_table.empty:
    st.dataframe(candidate_table, hide_index=True, use_container_width=True)

if st.button("Analyse and compare", type="primary", disabled=candidate_table.empty):
    try:
        capacity = storage_capacity(volume, tmax, tmin, efficiency)
        flow = required_flow(power, delta_t)
        _, dn, diameter, velocity = size_connection_pipe(flow["volume_flow_m3_s"])
        required_land = length * width * land_factor
        rows, map_items = [], []
        for candidate in candidate_table.to_dict("records"):
            pt = gpd.GeoSeries([Point(candidate["Longitude"], candidate["Latitude"])], crs=4326).to_crs(metric_crs).iloc[0]
            nearest, connection = nearest_pipe_connection(pt, pipes_m)
            distance = float(connection["length_m"].iloc[0])
            demand = nearby_demand(pt, buildings_m, demand_col)
            demand500 = float(demand.loc[demand["Radius [m]"] == 500, "Annual demand [MWh]"].iloc[0])
            pressure = darcy_weisbach_pressure_loss(distance, diameter, velocity)
            score, status, _ = suitability_score(available_land / required_land, distance, demand500, pressure["pressure_risk"], reference_demand)
            row = {"Candidate": candidate["Candidate"], "Latitude": candidate["Latitude"], "Longitude": candidate["Longitude"],
                   "Score [%]": score, "Status": status, "Connection [m]": distance, "Demand 500 m [MWh/year]": demand500,
                   "Useful capacity [MWh]": capacity["useful_capacity_mwh"], "Flow [m³/h]": flow["volume_flow_m3_h"],
                   "DN": dn, "Velocity [m/s]": velocity, "Pressure loss [bar]": pressure["pressure_loss_bar"], "Pressure risk": pressure["pressure_risk"]}
            footprint = translate(rotate(box(-length/2, -width/2, length/2, width/2), rotation, origin=(0, 0)), pt.x, pt.y)
            footprint_gdf = gpd.GeoDataFrame({"Candidate": [candidate["Candidate"]]}, geometry=[footprint], crs=metric_crs)
            rows.append(row)
            map_items.append((row, connection.to_crs(4326), footprint_gdf.to_crs(4326)))
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        st.stop()

    ranking = pd.DataFrame(rows).sort_values("Score [%]", ascending=False).reset_index(drop=True)
    st.subheader("Candidate comparison")
    a, b, c = st.columns(3)
    a.metric("Best candidate", ranking.iloc[0]["Candidate"])
    b.metric("Best score", f"{ranking.iloc[0]['Score [%]']:.1f}%")
    c.metric("Shortest connection", f"{ranking['Connection [m]'].min():.1f} m")
    st.dataframe(ranking.round(3), hide_index=True, use_container_width=True)
    st.bar_chart(ranking.set_index("Candidate")[["Score [%]"]])

    result_map = folium.Map(center, zoom_start=15)
    add_network(result_map, buildings_wgs, pipes_wgs)
    for result, connection, footprint in map_items:
        name, color = result["Candidate"], COLORS[result["Candidate"]]
        folium.GeoJson(connection, name=f"{name} connection", style_function=lambda _, col=color: {"color": col, "weight": 6},
                       tooltip=f"{name}: {result['Connection [m]']:.1f} m").add_to(result_map)
        folium.GeoJson(footprint, name=f"{name} footprint", style_function=lambda _, col=color: {"color": col, "weight": 3, "fillColor": col, "fillOpacity": .38}).add_to(result_map)
        marker(result_map, name, result["Latitude"], result["Longitude"], result)
    folium.LayerControl(collapsed=False).add_to(result_map)
    st.subheader("Combined interactive result map")
    st_folium(result_map, height=700, width=None, key="results", returned_objects=[])
    st.download_button("Download interactive HTML map", result_map.get_root().render().encode("utf-8"), "ptes_candidate_comparison_map.html", "text/html")
    st.download_button("Download comparison CSV", ranking.to_csv(index=False).encode("utf-8"), "ptes_candidate_comparison.csv", "text/csv")

st.divider()
st.caption("Preliminary screening only. Validate topology, pumps, boundary pressures, pipe roughness, fittings and operating cases in nPro.")
