import io
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium.features import GeoJsonPopup
from folium.plugins import Draw
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, box
from streamlit_folium import st_folium

from calculations import (assess_main_pipe, darcy_weisbach_pressure_loss,
                          geodetic_pressure_correction, required_flow,
                          size_connection_pipe, size_storage_from_demand,
                          suitability_score, truncated_pit_geometry)
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
THEMES = {
    "Standard network": None,
    "Supply pressure [bar]": "p_abs_pres_supply_sim_bar",
    "Return pressure [bar]": "p_abs_pres_return_sim_bar",
    "Supply temperature [°C]": "p_mean_temp_supply_degC",
    "Return temperature [°C]": "p_mean_temp_return_degC",
    "Pressure loss [Pa/m]": "p_pressure_loss_rel_sim_Pa_m",
    "Flow velocity [m/s]": "p_max_flow_velocity_m_s",
    "Power reserve [kW]": "p_power_reserve_abs_kW",
}


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


def add_network(fmap, buildings, pipes, theme_name="Standard network"):
    add_layer(fmap, buildings, "Buildings — click for details", BUILDING_FIELDS,
              {"color": "#555", "weight": 1, "fillColor": "#F3A712", "fillOpacity": .28},
              {"weight": 3, "fillOpacity": .5})
    field = THEMES.get(theme_name)
    if field and field in pipes.columns:
        values = pd.to_numeric(pipes[field], errors="coerce")
        low, high = values.min(), values.max()
        colors = ["#313695", "#74add1", "#ffffbf", "#f46d43", "#a50026"]
        def themed_style(feature):
            try:
                value = float(feature["properties"].get(field))
                fraction = 0 if high == low else (value - low) / (high - low)
                color = colors[min(4, max(0, int(fraction * 4.999)))]
            except (TypeError, ValueError):
                color = "#999999"
            return {"color": color, "weight": 5, "opacity": .9}
        fields = [f for f in PIPE_FIELDS if f in pipes.columns]
        folium.GeoJson(pipes, name=theme_name, style_function=themed_style,
                       highlight_function=lambda _: {"color": "#00FFFF", "weight": 8},
                       popup=GeoJsonPopup(fields, [PIPE_FIELDS[f] for f in fields], localize=True)).add_to(fmap)
        legend = f"<div style='position:fixed;bottom:35px;left:35px;z-index:9999;background:white;padding:10px;border:1px solid #777'><b>{theme_name}</b><br>Low&nbsp; <span style='color:#313695'>■</span> <span style='color:#74add1'>■</span> <span style='color:#ffffbf'>■</span> <span style='color:#f46d43'>■</span> <span style='color:#a50026'>■</span>&nbsp; High<br>{low:.2f} – {high:.2f}</div>"
        fmap.get_root().html.add_child(folium.Element(legend))
    else:
        add_layer(fmap, pipes, "Pipes — click for details", PIPE_FIELDS,
                  {"color": "#1677FF", "weight": 4}, {"color": "#00B8D9", "weight": 7})


def marker(fmap, name, lat, lon, result=None):
    text = f"<b>{name}</b><br>Latitude: {lat:.6f}<br>Longitude: {lon:.6f}"
    if result:
        branch_dn = result.get("Branch DN", result.get("DN", "Not available"))
        main_dn = result.get("Main DN", "Not available")
        text += (
            f"<br>Score: {result['Score [%]']:.1f}%"
            f"<br>Status: {result['Status']}"
            f"<br>Connection: {result['Connection [m]']:.1f} m"
            f"<br>Main pipe DN: {main_dn}"
            f"<br>PTES branch DN: {branch_dn}"
        )
    folium.Marker([lat, lon], tooltip=name, popup=folium.Popup(text, max_width=320),
                  icon=folium.Icon(color=COLORS[name], icon="info-sign")).add_to(fmap)


with st.sidebar:
    uploaded = st.file_uploader("Upload nPro GeoJSON", type=["geojson", "json"])
    st.header("PTES design")
    annual_demand = st.number_input("Annual system heat demand [MWh/year]", 1.0, value=20000.0)
    storage_type = st.selectbox("Storage type", ["Seasonal", "Weekly", "Daily"])
    coverage = st.slider("Demand shifted by storage [%]", 1.0, 100.0, 30.0)
    tmax = st.number_input("Maximum temperature [°C]", value=90.0)
    tmin = st.number_input("Minimum temperature [°C]", value=15.0)
    efficiency = st.slider("Efficiency", .5, 1.0, .8)
    power = st.number_input("Charge/discharge power [kW]", 1.0, value=3300.0)
    delta_t = st.number_input("Design ΔT [K]", 1.0, value=30.0)
    operating_mode = st.selectbox("Operating mode", ["Charging", "Discharging", "Idle"])
    with st.expander("Advanced geometry and pressure"):
        depth = st.number_input("Usable pit depth [m]", 1.0, value=15.0)
        side_slope = st.number_input("Side slope H:V", .1, value=2.0)
        aspect_ratio = st.number_input("Length-to-width ratio", .2, value=1.0)
        rotation = st.number_input("Footprint rotation [degrees]", value=0.0)
        elevation_offset = st.number_input("Candidate elevation above nearest pipe [m]", value=0.0)
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
map_theme = st.selectbox("Colour pipelines by", list(THEMES))
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
add_network(select_map, buildings_wgs, pipes_wgs, map_theme)
for name, xy in st.session_state.candidates.items():
    marker(select_map, name, xy["lat"], xy["lon"])
    if xy.get("route"):
        folium.PolyLine([[lat, lon] for lon, lat in xy["route"]], color=COLORS[name], weight=6,
                        tooltip=f"{name} manually routed connection").add_to(select_map)
Draw(export=False, position="topleft",
     draw_options={"polyline": True, "polygon": False, "rectangle": False,
                   "circle": False, "marker": False, "circlemarker": False},
     edit_options={"edit": True, "remove": True}).add_to(select_map)
folium.LayerControl(collapsed=False).add_to(select_map)
state = st_folium(select_map, height=620, width=None, key="selection",
                  returned_objects=["last_clicked", "all_drawings"])
clicked = state.get("last_clicked") if state else None
if placement and clicked:
    point = {"lat": float(clicked["lat"]), "lon": float(clicked["lng"])}
    previous = st.session_state.candidates.get(slot, {})
    point["route"] = previous.get("route")
    if previous.get("lat") != point["lat"] or previous.get("lon") != point["lon"]:
        st.session_state.candidates[slot] = point
        st.rerun()
drawings = state.get("all_drawings") if state else None
if drawings:
    lines = [item for item in drawings if item.get("geometry", {}).get("type") == "LineString"]
    if lines and slot in st.session_state.candidates:
        route = lines[-1]["geometry"]["coordinates"]
        if st.session_state.candidates[slot].get("route") != route:
            st.session_state.candidates[slot]["route"] = route
            st.rerun()
st.caption("Click to place a storage. Use the polyline tool to draw a multi-bend route for the selected storage. Turn placement off to inspect popups.")

candidate_table = pd.DataFrame([{"Candidate": n, "Latitude": v["lat"], "Longitude": v["lon"],
                                 "Manual route": bool(v.get("route"))} for n, v in st.session_state.candidates.items()])
if not candidate_table.empty:
    st.dataframe(candidate_table, hide_index=True, use_container_width=True)

if st.button("Analyse and compare", type="primary", disabled=candidate_table.empty):
    try:
        storage = size_storage_from_demand(annual_demand, coverage, storage_type, tmax, tmin, efficiency)
        geometry = truncated_pit_geometry(storage["volume_m3"], depth, side_slope, aspect_ratio)
        flow = required_flow(power, delta_t)
        _, dn, diameter, velocity = size_connection_pipe(flow["volume_flow_m3_s"])
        required_land = geometry["top_area_m2"] * land_factor
        rows, map_items = [], []
        for candidate in candidate_table.to_dict("records"):
            pt = gpd.GeoSeries([Point(candidate["Longitude"], candidate["Latitude"])], crs=4326).to_crs(metric_crs).iloc[0]
            saved = st.session_state.candidates[candidate["Candidate"]]
            if saved.get("route"):
                route_wgs = gpd.GeoSeries([LineString(saved["route"])], crs=4326)
                route_m = route_wgs.to_crs(metric_crs).iloc[0]
                route_end = Point(route_m.coords[-1])
                nearest, final_link = nearest_pipe_connection(route_end, pipes_m)
                full_line = LineString(list(route_m.coords) + list(final_link.geometry.iloc[0].coords)[1:])
                connection = gpd.GeoDataFrame({"length_m": [full_line.length]}, geometry=[full_line], crs=metric_crs)
            else:
                nearest, connection = nearest_pipe_connection(pt, pipes_m)
            distance = float(connection["length_m"].iloc[0])
            demand = nearby_demand(pt, buildings_m, demand_col)
            demand500 = float(demand.loc[demand["Radius [m]"] == 500, "Annual demand [MWh]"].iloc[0])
            pressure = darcy_weisbach_pressure_loss(distance, diameter, velocity)
            def number(field):
                value = nearest.get(field)
                try:
                    return None if pd.isna(value) else float(value)
                except (TypeError, ValueError):
                    return None
            pipe_height = number("p_geo_height_m")
            candidate_height = None if pipe_height is None else pipe_height + elevation_offset
            supply_before = number("p_abs_pres_supply_sim_bar") or number("p_abs_pres_supply_bar")
            return_before = number("p_abs_pres_return_sim_bar") or number("p_abs_pres_return_bar")
            supply_at_candidate = geodetic_pressure_correction(supply_before, pipe_height, candidate_height)
            return_at_candidate = geodetic_pressure_correction(return_before, pipe_height, candidate_height)
            existing_flow_day = number("p_max_flow_rates_sim_m3_day")
            main_check = assess_main_pipe(
                None if existing_flow_day is None else existing_flow_day / 24,
                flow["volume_flow_m3_h"], number("p_diameter_DN"),
                number("p_max_power_possible_kW"), number("p_power_reserve_abs_kW"),
                power, operating_mode,
            )
            score, status, _ = suitability_score(available_land / required_land, distance, demand500, pressure["pressure_risk"], reference_demand)
            row = {"Candidate": candidate["Candidate"], "Latitude": candidate["Latitude"], "Longitude": candidate["Longitude"],
                   "Score [%]": score, "Status": status, "Connection [m]": distance, "Demand 500 m [MWh/year]": demand500,
                   "Storage volume [m³]": storage["volume_m3"], "Energy/cycle [MWh]": storage["energy_per_cycle_mwh"],
                   "Top area [m²]": geometry["top_area_m2"], "Flow [m³/h]": flow["volume_flow_m3_h"],
                   "Main DN": main_check["main_dn"], "Branch DN": dn, "Velocity [m/s]": velocity,
                   "Pressure loss [bar]": pressure["pressure_loss_bar"], "Pressure risk": pressure["pressure_risk"],
                   "Pipe elevation [m]": pipe_height, "Candidate elevation [m]": candidate_height,
                   "Supply pressure at candidate [bar]": supply_at_candidate,
                   "Return pressure at candidate [bar]": return_at_candidate,
                   "Main flow after scenario [m³/h]": main_check["new_flow_m3_h"],
                   "Capacity status": main_check["capacity_status"]}
            footprint = translate(rotate(box(-geometry["top_length_m"]/2, -geometry["top_width_m"]/2,
                                                 geometry["top_length_m"]/2, geometry["top_width_m"]/2),
                                         rotation, origin=(0, 0)), pt.x, pt.y)
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
    add_network(result_map, buildings_wgs, pipes_wgs, map_theme)
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
