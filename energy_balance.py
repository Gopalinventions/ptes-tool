"""Generic preliminary monthly energy balance for PTES planning.

This module deliberately does not prescribe one project size.  It is a
transparent planning screen that links source capacities and operating hours
to a selected PTES volume.  Hourly dispatch, starts, ramps and detailed
thermal losses require uploaded time-series data and are outside this model.
"""

from __future__ import annotations

from dataclasses import dataclass


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# A transparent default for early planning only.  It may be replaced by an
# uploaded monthly/hourly demand profile in the next model stage.
DEFAULT_DEMAND_SHARES = (0.155, 0.138, 0.110, 0.078, 0.064, 0.034,
                         0.031, 0.034, 0.039, 0.078, 0.110, 0.129)
# Net useful solar heat, after collector-field losses, as a typical planning
# distribution.  It is not a replacement for a site-specific solar model.
DEFAULT_SOLAR_SHARES = (0.022, 0.039, 0.105, 0.131, 0.134, 0.145,
                        0.120, 0.132, 0.088, 0.037, 0.027, 0.020)


@dataclass(frozen=True)
class EnergySystemInputs:
    annual_demand_mwh: float
    storage_volume_m3: float
    hot_c: float
    cold_c: float
    usable_capacity_factor: float
    solar_net_annual_mwh: float
    bhkw_thermal_kw: float
    bhkw_summer_hours: float
    heat_pump_thermal_kw: float
    heat_pump_summer_hours: float
    heat_pump_cop: float
    waste_heat_kw: float
    waste_heat_summer_hours: float
    monthly_storage_loss_percent: float = 0.0


def _summer_distribution(total_mwh: float) -> list[float]:
    """Distribute a summer-only source by May–September calendar days."""
    days = (31, 30, 31, 31, 30)
    return [0.0] * 4 + [total_mwh * d / sum(days) for d in days] + [0.0] * 3


def validate_inputs(x: EnergySystemInputs) -> None:
    numeric = (x.annual_demand_mwh, x.storage_volume_m3, x.solar_net_annual_mwh,
               x.bhkw_thermal_kw, x.bhkw_summer_hours, x.heat_pump_thermal_kw,
               x.heat_pump_summer_hours, x.waste_heat_kw, x.waste_heat_summer_hours)
    if any(value < 0 for value in numeric):
        raise ValueError("Demand, volume, capacities and operating hours cannot be negative.")
    if x.storage_volume_m3 <= 0:
        raise ValueError("PTES water volume must be greater than zero.")
    if x.hot_c <= x.cold_c:
        raise ValueError("Storage hot temperature must be higher than cold temperature.")
    if not 0 < x.usable_capacity_factor <= 1:
        raise ValueError("Usable capacity factor must be between 0 and 1.")
    if x.heat_pump_cop <= 0:
        raise ValueError("Heat-pump COP must be greater than zero.")
    if not 0 <= x.monthly_storage_loss_percent < 100:
        raise ValueError("Monthly storage loss must be from 0 up to (but not including) 100%.")


def simulate_monthly_balance(x: EnergySystemInputs) -> dict:
    """Calculate source-first supply, PTES charge/discharge and remaining heat.

    Solar, BHKW, heat-pump and waste heat first meet monthly demand. Surplus
    charges PTES; the PTES discharges for deficits before an external boiler
    covers the balance. Sources other than solar are intentionally summer-only
    planning inputs so the model does not invent winter operation.
    """
    validate_inputs(x)
    capacity_mwh = x.storage_volume_m3 * 1.163 * (x.hot_c - x.cold_c) / 1000 * x.usable_capacity_factor
    demand = [x.annual_demand_mwh * share for share in DEFAULT_DEMAND_SHARES]
    solar = [x.solar_net_annual_mwh * share for share in DEFAULT_SOLAR_SHARES]
    bhkw = _summer_distribution(x.bhkw_thermal_kw * x.bhkw_summer_hours / 1000)
    heat_pump = _summer_distribution(x.heat_pump_thermal_kw * x.heat_pump_summer_hours / 1000)
    waste_heat = _summer_distribution(x.waste_heat_kw * x.waste_heat_summer_hours / 1000)
    monthly_loss = x.monthly_storage_loss_percent / 100
    soc = 0.0
    rows = []
    for index, month in enumerate(MONTHS):
        soc_before_loss = soc
        standing_loss = soc_before_loss * monthly_loss
        soc = max(0.0, soc_before_loss - standing_loss)
        source_total = solar[index] + bhkw[index] + heat_pump[index] + waste_heat[index]
        direct_supply = min(demand[index], source_total)
        surplus = max(0.0, source_total - demand[index])
        accepted_charge = min(surplus, max(0.0, capacity_mwh - soc))
        curtailed = surplus - accepted_charge
        soc += accepted_charge
        deficit = max(0.0, demand[index] - source_total)
        discharge = min(deficit, soc)
        soc -= discharge
        boiler = deficit - discharge
        rows.append({
            "Month": month, "Demand [MWh]": demand[index], "Solar [MWh]": solar[index],
            "BHKW heat [MWh]": bhkw[index], "Heat pump heat [MWh]": heat_pump[index],
            "Waste heat [MWh]": waste_heat[index], "Direct source supply [MWh]": direct_supply,
            "PTES charge [MWh]": accepted_charge, "PTES discharge [MWh]": discharge,
            "PTES loss [MWh]": standing_loss, "PTES state of charge [MWh]": soc,
            "Curtailment [MWh]": curtailed, "Remaining boiler heat [MWh]": boiler,
            "Heat-pump electricity [MWh]": heat_pump[index] / x.heat_pump_cop,
        })
    totals = {key: sum(row[key] for row in rows) for key in rows[0] if key != "Month"}
    return {
        "capacity_mwh": capacity_mwh,
        "rows": rows,
        "totals": totals,
        "maximum_soc_mwh": max(row["PTES state of charge [MWh]"] for row in rows),
        "end_soc_mwh": rows[-1]["PTES state of charge [MWh]"],
        "model_status": "Preliminary monthly planning balance — replace defaults with uploaded hourly profiles for dispatch decisions.",
    }
