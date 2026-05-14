#!/usr/bin/env python3
"""
zone_mapper.py
--------------
Assigns each iNaturalist observation to a zone polygon using point-in-polygon
geometry. Outputs the original CSV with an `assigned_zone` column appended.

Requirements:
    pip install pandas

Usage (run from the repo root):
    python scripts/zone_mapper.py
    python scripts/zone_mapper.py --zones spatial/mariposas_zones.geojson \
                                  --obs data/observations.csv \
                                  --out data/observations_zoned.csv

Defaults expect:
    spatial/mariposas_zones.geojson   — your exported zone file
    observations.csv                  — iNaturalist export CSV (in same folder)
    observations_zoned.csv            — output (written to same folder as --obs)

Getting the iNaturalist CSV:
    Project page → Export Observations → keep default columns → download.
    The file needs latitude and longitude columns, which are included by default.

Notes on "outside all zones":
    Historical observations (before zones were drawn) are often logged at the
    site entrance or general address rather than within a specific planting area.
    This is expected — future observations tagged with zone-A1 etc. will be more
    precise. Observations with obscured coordinates (threatened species or private
    geoprivacy) may also fall outside zones.
"""

import json
import argparse
import sys
import os
import pandas as pd


# ---------------------------------------------------------------------------
# Geometry helpers — no external dependencies
# ---------------------------------------------------------------------------

def _ring_area(ring):
    """Shoelace formula for coordinate-space polygon area."""
    area = 0.0
    n = len(ring)
    j = n - 1
    for i in range(n):
        area += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1])
        j = i
    return abs(area / 2.0)


def _feature_area(feature):
    """Approximate area for sorting (smallest zones checked first)."""
    g = feature.get("geometry") or {}
    t = g.get("type")
    if t == "Polygon":
        return _ring_area(g["coordinates"][0])
    if t == "MultiPolygon":
        return sum(_ring_area(p[0]) for p in g["coordinates"])
    return float("inf")  # LineStrings etc. sort last and are skipped anyway


def _pip(lon, lat, ring):
    """Ray-casting point-in-polygon for a single ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_feature(lon, lat, geometry):
    t = geometry.get("type")
    if t == "Polygon":
        return _pip(lon, lat, geometry["coordinates"][0])
    if t == "MultiPolygon":
        return any(_pip(lon, lat, p[0]) for p in geometry["coordinates"])
    return False


# ---------------------------------------------------------------------------
# Zone loading
# ---------------------------------------------------------------------------

_ZONE_ID_KEYS = ["zone_id", "Zone_id", "Zone_ID", "ZONE_ID",
                 "name", "Name", "NAME", "label", "id"]


def _get_zone_id(properties):
    if not properties:
        return None
    for key in _ZONE_ID_KEYS:
        val = properties.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def load_zones(path):
    """Return list of zone dicts sorted by area ascending (smallest first)."""
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    features = gj.get("features", [gj])
    zones = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        zone_id = _get_zone_id(feat.get("properties") or {})
        if not zone_id:
            continue
        zones.append({
            "id": zone_id,
            "geometry": geom,
            "area": _feature_area(feat),
        })
    zones.sort(key=lambda z: z["area"])
    return zones


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

def assign_zone(lon, lat, zones):
    """Return the zone_id of the smallest polygon that contains the point."""
    for zone in zones:
        if _point_in_feature(lon, lat, zone["geometry"]):
            return zone["id"]
    return None


def _get_coord(row, *keys):
    for k in keys:
        val = row.get(k)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return float("nan")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Assign iNaturalist observations to zone polygons."
    )
    parser.add_argument(
        "--zones",
        default=os.path.join("spatial", "mariposas_zones.geojson"),
        help="Zone GeoJSON file (default: spatial/mariposas_zones.geojson)",
    )
    parser.add_argument(
        "--obs",
        default="observations.csv",
        help="iNaturalist observation CSV (default: observations.csv)",
    )
    parser.add_argument(
        "--out",
        default="observations_zoned.csv",
        help="Output CSV filename (default: observations_zoned.csv)",
    )
    args = parser.parse_args()

    # Load zones
    print(f"Loading zones from: {args.zones}")
    try:
        zones = load_zones(args.zones)
    except FileNotFoundError:
        print(f"  ERROR: file not found — {args.zones}")
        sys.exit(1)
    if not zones:
        print("  ERROR: no named polygon features found in the GeoJSON.")
        sys.exit(1)
    print(f"  {len(zones)} zone polygon(s) loaded:")
    for z in zones:
        print(f"    {z['id']}")

    # Load observations
    print(f"\nLoading observations from: {args.obs}")
    try:
        df = pd.read_csv(args.obs, low_memory=False)
    except FileNotFoundError:
        print(f"  ERROR: file not found — {args.obs}")
        sys.exit(1)
    print(f"  {len(df)} observations loaded")

    # Assign zones row by row
    print("\nAssigning zones...")
    assigned = []
    for _, row in df.iterrows():
        lat = _get_coord(row, "latitude", "Latitude", "lat")
        lon = _get_coord(row, "longitude", "Longitude", "lon", "lng")
        if pd.isna(lat) or pd.isna(lon):
            assigned.append("no_coordinates")
        else:
            result = assign_zone(lon, lat, zones)
            assigned.append(result if result else "outside")

    df["assigned_zone"] = assigned

    # Summary
    n_total = len(df)
    n_matched = sum(1 for z in assigned if z not in ("outside", "no_coordinates"))
    n_outside = assigned.count("outside")
    n_no_coord = assigned.count("no_coordinates")

    print(f"\nSummary:")
    print(f"  Total observations :  {n_total}")
    print(f"  Assigned to a zone :  {n_matched}  ({n_matched/n_total*100:.1f}%)")
    print(f"  Outside all zones  :  {n_outside}  ({n_outside/n_total*100:.1f}%)")
    if n_no_coord:
        print(f"  No coordinates     :  {n_no_coord}")

    print(f"\nBy zone:")
    counts = df["assigned_zone"].value_counts()
    for zone, count in counts.items():
        marker = "" if zone in ("outside", "no_coordinates") else "  ← "
        print(f"  {zone:<35} {count:>5}  ({count/n_total*100:.1f}%){marker}")

    # Write output
    df.to_csv(args.out, index=False)
    print(f"\nSaved: {args.out}")


if __name__ == "__main__":
    main()
