"""GIS helpers for PTES location screening."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points


def split_layers(gdf: gpd.GeoDataFrame):
    buildings = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    pipes = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    if buildings.empty or pipes.empty:
        raise ValueError("The file must contain polygon buildings and line-based pipes.")
    return buildings, pipes


def local_metric_crs(gdf: gpd.GeoDataFrame):
    """Estimate a suitable UTM CRS from the dataset instead of hard-coding Germany zone 32."""
    estimated = gdf.estimate_utm_crs()
    if estimated is None:
        raise ValueError("A local metric coordinate system could not be determined.")
    return estimated


def clean_geometry(gdf: gpd.GeoDataFrame):
    return gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty & gdf.geometry.is_valid].copy()


def nearest_pipe_connection(point: Point, pipes: gpd.GeoDataFrame):
    distances = pipes.geometry.distance(point)
    nearest_pipe = pipes.loc[distances.idxmin()]
    endpoint = nearest_points(point, nearest_pipe.geometry)[1]
    line = LineString([point, endpoint])
    connection = gpd.GeoDataFrame(
        {"length_m": [line.length]}, geometry=[line], crs=pipes.crs
    )
    return nearest_pipe, connection


def nearby_demand(point: Point, buildings: gpd.GeoDataFrame, demand_column: str):
    points = buildings.copy()
    points.geometry = buildings.geometry.centroid
    rows = []
    for radius in (250, 500, 1000):
        selected = points[points.geometry.within(point.buffer(radius))]
        rows.append({
            "Radius [m]": radius,
            "Buildings": len(selected),
            "Annual demand [MWh]": float(selected[demand_column].sum()),
        })
    return pd.DataFrame(rows)
