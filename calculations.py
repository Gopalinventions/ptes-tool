"""Engineering calculations for preliminary PTES screening."""

from __future__ import annotations

import math
import pandas as pd


DN_DIAMETERS_M = {
    50: 0.053,
    65: 0.068,
    80: 0.082,
    100: 0.107,
    125: 0.132,
    150: 0.160,
    200: 0.210,
    250: 0.263,
    300: 0.312,
}


def size_storage_from_demand(annual_demand_mwh: float, coverage_percent: float,
                             storage_type: str, t_max_c: float, t_min_c: float,
                             efficiency: float) -> dict:
    """Convert demand allocated to one operating cycle into water volume."""
    if annual_demand_mwh <= 0:
        raise ValueError("Annual demand must be greater than zero.")
    if not 0 < coverage_percent <= 100:
        raise ValueError("Storage coverage must be between 0 and 100 percent.")
    if t_max_c <= t_min_c or not 0 < efficiency <= 1:
        raise ValueError("Check storage temperatures and efficiency.")
    cycles = {"Seasonal": 1, "Weekly": 52, "Daily": 365}[storage_type]
    annual_shifted_mwh = annual_demand_mwh * coverage_percent / 100
    energy_per_cycle_mwh = annual_shifted_mwh / cycles
    delta_t_k = t_max_c - t_min_c
    volume_m3 = energy_per_cycle_mwh * 1000 / (1.163 * delta_t_k * efficiency)
    return {
        "cycles_per_year": cycles,
        "annual_shifted_mwh": annual_shifted_mwh,
        "energy_per_cycle_mwh": energy_per_cycle_mwh,
        "volume_m3": volume_m3,
        "delta_t_k": delta_t_k,
    }


def truncated_pit_geometry(volume_m3: float, depth_m: float, side_slope_h_to_v: float = 2.0,
                           length_width_ratio: float = 1.0) -> dict:
    """Solve top dimensions for a truncated rectangular-pyramid PTES."""
    if min(volume_m3, depth_m, side_slope_h_to_v, length_width_ratio) <= 0:
        raise ValueError("Pit geometry inputs must be positive.")
    offset = 2 * depth_m * side_slope_h_to_v

    def volume_for_width(top_width):
        top_length = length_width_ratio * top_width
        bottom_width = max(0.01, top_width - offset)
        bottom_length = max(0.01, top_length - offset)
        top_area = top_length * top_width
        bottom_area = bottom_length * bottom_width
        return depth_m / 3 * (top_area + bottom_area + math.sqrt(top_area * bottom_area))

    low, high = offset + 0.01, max(offset + 1, math.sqrt(volume_m3 / depth_m) * 3)
    while volume_for_width(high) < volume_m3:
        high *= 1.5
    for _ in range(80):
        middle = (low + high) / 2
        if volume_for_width(middle) < volume_m3:
            low = middle
        else:
            high = middle
    top_width = (low + high) / 2
    top_length = length_width_ratio * top_width
    bottom_width = max(0, top_width - offset)
    bottom_length = max(0, top_length - offset)
    return {
        "top_length_m": top_length,
        "top_width_m": top_width,
        "top_area_m2": top_length * top_width,
        "bottom_length_m": bottom_length,
        "bottom_width_m": bottom_width,
        "bottom_area_m2": bottom_length * bottom_width,
        "depth_m": depth_m,
    }


def geodetic_pressure_correction(reference_pressure_bar: float | None,
                                 reference_height_m: float | None,
                                 candidate_height_m: float | None,
                                 water_density_kg_m3: float = 1000.0) -> float | None:
    """Correct absolute pressure for elevation; higher locations have lower pressure."""
    if reference_pressure_bar is None or reference_height_m is None or candidate_height_m is None:
        return None
    return reference_pressure_bar - water_density_kg_m3 * 9.80665 * (candidate_height_m - reference_height_m) / 100000


def assess_main_pipe(existing_flow_m3_h: float | None, ptes_flow_m3_h: float,
                     main_dn: float | None, max_power_kw: float | None,
                     reserve_power_kw: float | None, ptes_power_kw: float,
                     operating_mode: str) -> dict:
    """Local capacity screen. Network-wide redistribution still requires nPro."""
    sign = 1 if operating_mode == "Charging" else -1 if operating_mode == "Discharging" else 0
    new_flow = None if existing_flow_m3_h is None else max(0.0, existing_flow_m3_h + sign * ptes_flow_m3_h)
    reserve_after = None if reserve_power_kw is None else reserve_power_kw - ptes_power_kw
    power_ok = None if max_power_kw is None else ptes_power_kw <= max_power_kw
    reserve_ok = None if reserve_power_kw is None else ptes_power_kw <= reserve_power_kw
    status = "Detailed simulation required"
    if reserve_ok is False or power_ok is False:
        status = "Insufficient main-pipe capacity"
    elif reserve_ok is True:
        status = "Preliminarily compatible"
    return {
        "existing_flow_m3_h": existing_flow_m3_h,
        "new_flow_m3_h": new_flow,
        "main_dn": main_dn,
        "reserve_after_kw": reserve_after,
        "capacity_status": status,
    }


def storage_capacity(volume_m3: float, t_max_c: float, t_min_c: float, efficiency: float) -> dict:
    if volume_m3 <= 0:
        raise ValueError("Storage volume must be greater than zero.")
    if t_max_c <= t_min_c:
        raise ValueError("Maximum temperature must be higher than minimum temperature.")
    if not 0 < efficiency <= 1:
        raise ValueError("Efficiency must be between 0 and 1.")

    delta_t_k = t_max_c - t_min_c
    gross_mwh = volume_m3 * 1.163 * delta_t_k / 1000
    return {
        "delta_t_k": delta_t_k,
        "gross_capacity_mwh": gross_mwh,
        "useful_capacity_mwh": gross_mwh * efficiency,
    }


def required_flow(power_kw: float, delta_t_k: float) -> dict:
    if power_kw <= 0 or delta_t_k <= 0:
        raise ValueError("Power and design temperature difference must be greater than zero.")

    mass_flow_kg_s = power_kw / (4.18 * delta_t_k)
    volume_flow_m3_s = mass_flow_kg_s / 1000
    return {
        "mass_flow_kg_s": mass_flow_kg_s,
        "volume_flow_m3_s": volume_flow_m3_s,
        "volume_flow_m3_h": volume_flow_m3_s * 3600,
    }


def size_connection_pipe(volume_flow_m3_s: float, min_velocity: float = 0.6, max_velocity: float = 2.0):
    rows = []
    for dn, diameter_m in DN_DIAMETERS_M.items():
        area_m2 = math.pi * diameter_m**2 / 4
        velocity_m_s = volume_flow_m3_s / area_m2
        rows.append({"DN": dn, "inner_diameter_m": diameter_m, "velocity_m_s": velocity_m_s})

    table = pd.DataFrame(rows)
    valid = table[table["velocity_m_s"].between(min_velocity, max_velocity)]
    if not valid.empty:
        selected = valid.iloc[0]
    else:
        below_limit = table[table["velocity_m_s"] <= max_velocity]
        selected = below_limit.iloc[0] if not below_limit.empty else table.iloc[-1]

    return table, int(selected["DN"]), float(selected["inner_diameter_m"]), float(selected["velocity_m_s"])


def darcy_weisbach_pressure_loss(length_m: float, diameter_m: float, velocity_m_s: float,
                                 friction_factor: float = 0.025, local_loss_factor: float = 2.0) -> dict:
    """Screening calculation for straight pipe plus a user-independent allowance for fittings."""
    rho_kg_m3 = 1000.0
    dynamic_pressure_pa = rho_kg_m3 * velocity_m_s**2 / 2
    straight_loss_pa = friction_factor * (length_m / diameter_m) * dynamic_pressure_pa
    local_loss_pa = local_loss_factor * dynamic_pressure_pa
    loss_bar = (straight_loss_pa + local_loss_pa) / 100_000
    risk = "Low" if loss_bar < 0.3 else "Medium" if loss_bar < 0.8 else "High"
    return {"pressure_loss_bar": loss_bar, "pressure_risk": risk}


def suitability_score(land_ratio: float, connection_m: float, demand_500_mwh: float,
                      pressure_risk: str, reference_demand_mwh: float) -> tuple[float, str, pd.DataFrame]:
    """Five criteria with weights normalized to exactly 100 percent."""
    land = 100 if land_ratio >= 1.3 else 80 if land_ratio >= 1.1 else 60 if land_ratio >= 1 else 30 if land_ratio >= 0.8 else 0
    pipe = 100 if connection_m < 100 else 90 if connection_m < 250 else 75 if connection_m < 500 else 50 if connection_m < 1000 else 25
    demand = min(100, demand_500_mwh / max(reference_demand_mwh, 1) * 100)
    hydraulic = {"Low": 100, "Medium": 65, "High": 25}[pressure_risk]
    data_quality = 80  # Explicit preliminary-data allowance; replace with a project-specific check later.

    criteria = pd.DataFrame({
        "Criterion": ["Land availability", "Pipe proximity", "Nearby demand", "Hydraulics", "Data quality"],
        "Score": [land, pipe, demand, hydraulic, data_quality],
        "Weight": [0.25, 0.25, 0.20, 0.20, 0.10],
    })
    criteria["Weighted score"] = criteria["Score"] * criteria["Weight"]
    score = float(criteria["Weighted score"].sum())
    status = "Good" if score >= 80 else "Moderate" if score >= 60 else "Weak"
    return score, status, criteria
