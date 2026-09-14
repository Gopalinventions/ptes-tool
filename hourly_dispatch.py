"""Transparent hourly source-dispatch screen for preliminary PTES planning."""

from __future__ import annotations

import pandas as pd


def run_hourly_dispatch(
    frame: pd.DataFrame, *, storage_capacity_mwh: float, initial_soc_fraction: float,
    bhkw_thermal_kw: float, bhkw_electrical_kw: float, bhkw_price_threshold: float,
    bhkw_fuel_per_mwh_e: float, bhkw_active_months: tuple[int, ...], heat_pump_thermal_kw: float, heat_pump_cop: float,
    heat_pump_max_price: float, waste_heat_kw: float, monthly_loss_percent: float,
) -> pd.DataFrame:
    """Run a heat-acceptance-limited merit order on aligned hourly profiles.

    Source order is solar, waste heat, price-qualified BHKW, then
    price-qualified heat pump.  PTES receives surplus and discharges before
    boiler heat.  Partial-load operation is permitted; minimum loads, starts,
    ramps and network hydraulics are intentionally not claimed here.
    """
    required = {"Timestamp", "Demand [MWh]", "Solar [MWh]", "Price [€/MWh]"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Hourly dispatch input is missing: {', '.join(sorted(missing))}.")
    if storage_capacity_mwh <= 0 or not 0 <= initial_soc_fraction <= 1:
        raise ValueError("Storage capacity must be positive and initial state of charge must be 0–100%.")
    if heat_pump_cop <= 0:
        raise ValueError("Heat-pump COP must be greater than zero.")
    data = frame.sort_values("Timestamp").reset_index(drop=True).copy()
    for column in required.difference({"Timestamp"}):
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0).clip(lower=0.0)
    hourly_loss = (monthly_loss_percent / 100) / (30.4375 * 24)
    soc = storage_capacity_mwh * initial_soc_fraction
    rows = []
    for row in data.itertuples(index=False):
        demand, solar, price = row[1], row[2], row[3]
        loss = soc * hourly_loss
        soc = max(0.0, soc - loss)
        headroom = max(0.0, storage_capacity_mwh - soc)
        direct_solar = min(demand, solar)
        remaining = demand - direct_solar
        solar_surplus = solar - direct_solar
        waste = min(waste_heat_kw / 1000, remaining + headroom)
        direct_waste = min(remaining, waste)
        remaining -= direct_waste
        waste_surplus = waste - direct_waste
        headroom -= solar_surplus + waste_surplus
        bhkw_eligible = row[0].month in bhkw_active_months and price >= bhkw_price_threshold
        bhkw = min(bhkw_thermal_kw / 1000 if bhkw_eligible else 0.0, remaining + max(0.0, headroom))
        direct_bhkw = min(remaining, bhkw)
        remaining -= direct_bhkw
        bhkw_surplus = bhkw - direct_bhkw
        headroom -= bhkw_surplus
        hp_eligible = price <= heat_pump_max_price
        hp = min(heat_pump_thermal_kw / 1000 if hp_eligible else 0.0, remaining + max(0.0, headroom))
        direct_hp = min(remaining, hp)
        remaining -= direct_hp
        hp_surplus = hp - direct_hp
        total_charge = min(max(0.0, solar_surplus + waste_surplus + bhkw_surplus + hp_surplus), max(0.0, storage_capacity_mwh - soc))
        soc += total_charge
        discharge = min(remaining, soc)
        soc -= discharge
        boiler = remaining - discharge
        bhkw_electricity = bhkw * (bhkw_electrical_kw / bhkw_thermal_kw) if bhkw_thermal_kw else 0.0
        rows.append({
            "Timestamp": row[0], "Demand [MWh]": demand, "Solar [MWh]": solar,
            "Waste heat [MWh]": waste, "BHKW heat [MWh]": bhkw,
            "BHKW electricity [MWh]": bhkw_electricity,
            "BHKW fuel [MWh]": bhkw_electricity * bhkw_fuel_per_mwh_e,
            "Heat pump heat [MWh]": hp, "Heat-pump electricity [MWh]": hp / heat_pump_cop,
            "PTES charge [MWh]": total_charge, "PTES discharge [MWh]": discharge,
            "PTES loss [MWh]": loss, "State of charge [MWh]": soc,
            "Boiler heat [MWh]": boiler, "Price [€/MWh]": price,
            "BHKW electricity revenue [€]": bhkw_electricity * price,
        })
    return pd.DataFrame(rows)
