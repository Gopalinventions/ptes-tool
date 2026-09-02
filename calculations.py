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
