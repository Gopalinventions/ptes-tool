"""Weather-derived heat-demand profiles for preliminary PTES screening."""

from __future__ import annotations

import io
import pandas as pd


TIMESTAMP_HINTS = ("timestamp", "valid_time", "time", "datetime", "date", "datum", "messzeit")
TEMPERATURE_HINTS = (
    "outdoor_temperature_c", "temperature", "temperature_2m", "2m_temperature",
    "t2m", "temp", "t", "lufttemperatur", "drybulb",
)


def read_weather_table(file_bytes: bytes) -> pd.DataFrame:
    """Read common DWD, ERA5 and generic CSV/TXT formats."""
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            table = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python", encoding=encoding,
                                comment="*")
            if len(table.columns) == 1:
                table = pd.read_csv(io.BytesIO(file_bytes), sep=r"\s+", engine="python",
                                    encoding=encoding, comment="*")
            normalized = {str(column).strip().lower(): column for column in table.columns}
            if not any(hint in normalized for hint in TIMESTAMP_HINTS):
                month = normalized.get("mm") or normalized.get("month") or normalized.get("monat")
                day = normalized.get("dd") or normalized.get("day") or normalized.get("tag")
                hour = normalized.get("hh") or normalized.get("hour") or normalized.get("stunde")
                year = normalized.get("year") or normalized.get("yyyy") or normalized.get("jahr")
                if month and day and hour:
                    hours = pd.to_numeric(table[hour], errors="coerce").fillna(1).astype(int)
                    # DWD TRY commonly numbers hours 1–24; convert to 0–23.
                    hours = hours.where(~hours.between(1, 24), hours - 1)
                    years = pd.to_numeric(table[year], errors="coerce").fillna(2015).astype(int) if year else 2015
                    table["timestamp"] = pd.to_datetime({
                        "year": years,
                        "month": pd.to_numeric(table[month], errors="coerce"),
                        "day": pd.to_numeric(table[day], errors="coerce"),
                        "hour": hours,
                    }, errors="coerce", utc=True)
            return table
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read weather table: {last_error}")


def suggested_column(columns, hints):
    lowered = {str(column).lower().strip(): column for column in columns}
    for hint in hints:
        if hint in lowered:
            return lowered[hint]
    for column in columns:
        text = str(column).lower()
        if any(hint in text for hint in hints):
            return column
    return columns[0]


def build_weather_demand_profile(
    table: pd.DataFrame,
    timestamp_column: str,
    temperature_column: str,
    annual_demand_mwh: float,
    domestic_hot_water_percent: float,
    heating_limit_c: float,
) -> pd.DataFrame:
    """Distribute annual demand using hourly heating-degree weights."""
    if annual_demand_mwh <= 0:
        raise ValueError("Annual demand must be greater than zero.")
    if not 0 <= domestic_hot_water_percent < 100:
        raise ValueError("Domestic-hot-water share must be from 0 to below 100 percent.")
    frame = table[[timestamp_column, temperature_column]].copy()
    frame.columns = ["timestamp", "outdoor_temperature_c"]
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame["outdoor_temperature_c"] = pd.to_numeric(frame["outdoor_temperature_c"], errors="coerce")
    frame = frame.dropna().sort_values("timestamp").drop_duplicates("timestamp")
    if frame.empty:
        raise ValueError("No valid timestamp and temperature rows were found.")
    if frame["outdoor_temperature_c"].median() > 100:
        frame["outdoor_temperature_c"] -= 273.15
    if not frame["outdoor_temperature_c"].between(-50, 60).all():
        raise ValueError("Temperature values fall outside the expected outdoor range after unit conversion.")

    dhw_annual = annual_demand_mwh * domestic_hot_water_percent / 100
    space_annual = annual_demand_mwh - dhw_annual
    frame["heating_degree_weight"] = (heating_limit_c - frame["outdoor_temperature_c"]).clip(lower=0)
    weight_sum = frame["heating_degree_weight"].sum()
    if weight_sum <= 0:
        raise ValueError("Weather contains no hours below the selected heating-limit temperature.")
    frame["space_heat_mwh"] = space_annual * frame["heating_degree_weight"] / weight_sum
    frame["dhw_mwh"] = dhw_annual / len(frame)
    frame["heat_demand_mwh"] = frame["space_heat_mwh"] + frame["dhw_mwh"]
    month = frame["timestamp"].dt.month
    frame["season"] = "Transition"
    frame.loc[month.isin([11, 12, 1, 2, 3]), "season"] = "Winter"
    frame.loc[month.isin([6, 7, 8]), "season"] = "Summer"
    return frame


def seasonal_summary(profile: pd.DataFrame, usable_storage_mwh: float | None = None) -> pd.DataFrame:
    result = profile.groupby("season", as_index=False).agg(
        demand_mwh=("heat_demand_mwh", "sum"),
        space_heat_mwh=("space_heat_mwh", "sum"),
        dhw_mwh=("dhw_mwh", "sum"),
        mean_temperature_c=("outdoor_temperature_c", "mean"),
        minimum_temperature_c=("outdoor_temperature_c", "min"),
        hours=("timestamp", "count"),
    )
    result["annual_demand_share_percent"] = result["demand_mwh"] / profile["heat_demand_mwh"].sum() * 100
    if usable_storage_mwh is not None:
        result["one_full_store_coverage_percent"] = (
            usable_storage_mwh / result["demand_mwh"].replace(0, pd.NA) * 100
        ).clip(upper=100)
    order = pd.Categorical(result["season"], ["Winter", "Transition", "Summer"], ordered=True)
    return result.assign(_order=order).sort_values("_order").drop(columns="_order").reset_index(drop=True)


def monthly_summary(profile: pd.DataFrame) -> pd.DataFrame:
    result = profile.set_index("timestamp").resample("MS").agg(
        demand_mwh=("heat_demand_mwh", "sum"),
        space_heat_mwh=("space_heat_mwh", "sum"),
        dhw_mwh=("dhw_mwh", "sum"),
        mean_temperature_c=("outdoor_temperature_c", "mean"),
    ).reset_index()
    result["month"] = result["timestamp"].dt.strftime("%Y-%m")
    return result
