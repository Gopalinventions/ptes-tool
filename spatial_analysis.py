"""Measured spatial relationships for optional authoritative GIS layers."""

from __future__ import annotations

import io
import geopandas as gpd


def read_uploaded_vector(uploaded_file, target_crs):
    """Read an uploaded GeoJSON and project it into the analysis CRS."""
    if uploaded_file is None:
        return None
    layer = gpd.read_file(io.BytesIO(uploaded_file.getvalue()))
    if layer.crs is None:
        raise ValueError(f"{uploaded_file.name} has no CRS metadata.")
    layer = layer[layer.geometry.notna() & ~layer.geometry.is_empty & layer.geometry.is_valid].copy()
    return layer.to_crs(target_crs)


def overlap_area_m2(geometry, layer):
    if layer is None or layer.empty:
        return None
    return float(layer.geometry.intersection(geometry).area.sum())


def intersecting_feature_count(geometry, layer):
    if layer is None or layer.empty:
        return None
    return int(layer.geometry.intersects(geometry).sum())


def nearest_distance_m(geometry, layer):
    if layer is None or layer.empty:
        return None
    return float(layer.geometry.distance(geometry).min())


def containing_parcel_measurements(geometry, parcels):
    if parcels is None or parcels.empty:
        return {"parcel_area_m2": None, "footprint_inside_m2": None, "footprint_outside_m2": None}
    intersecting = parcels[parcels.geometry.intersects(geometry)]
    if intersecting.empty:
        return {"parcel_area_m2": None, "footprint_inside_m2": 0.0, "footprint_outside_m2": float(geometry.area)}
    parcel = intersecting.loc[intersecting.geometry.intersection(geometry).area.idxmax()].geometry
    inside = float(geometry.intersection(parcel).area)
    return {
        "parcel_area_m2": float(parcel.area),
        "footprint_inside_m2": inside,
        "footprint_outside_m2": max(0.0, float(geometry.area) - inside),
    }


def nearest_point_attribute(point, layer, field):
    if layer is None or layer.empty or not field or field not in layer.columns:
        return {"distance_m": None, "value": None}
    distances = layer.geometry.distance(point)
    index = distances.idxmin()
    return {"distance_m": float(distances.loc[index]), "value": layer.loc[index, field]}
