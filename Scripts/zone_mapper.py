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

    # If your GeoJSON uses a property name not auto-detected, specify it:
    python scripts/zone_mapper.py --zone-property zone

Auto-detected property names (checked in order):
    zone_id, Zone_ID, zone, Zone, name, Name, label, id

Getting the iNaturalist CSV:
    Project page -> Export Observations -> keep default columns -> download.
    The file needs latitude and longitude columns (included by default).

Notes on "outside all zones":
    Historical observations are often logged at the site entrance or general
    address rather than within a specific planting area. Observations with
    obscured coordinates (threatened species / private geoprivacy) may also
    fall outside zones. Both are expected for pre-zoning records.
"""

import json
import argparse
import sys
import os
import pandas as pd


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _ring_area(ring):
    area = 0.0
    n = len(ring)
    j = n - 1
    for i in range(n):
        area += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1])
        j = i
    return abs(area / 2.0)


def _feature_area(feature):
    g = feature.get("geometry") or {}
    t = g.get("type")
    if t == "Polygon":
        return _ring_area(g["coordinates"][0])
    if t == "MultiPolygon":
        return sum(_ring_area(p[0]) for p in g["coordinates"])
    return float("inf")


def _pip(lon, lat, ring):
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

_ZONE_ID_KEYS = [
    "zone_id", "Zone_id", "Zone_ID", "ZONE_ID",
    "zone", "Zone", "ZONE",
    "name", "Name", "NAME",
    "label", "Label",
    "id",
]


def _get_zone_id(properties, override_key=None):
    if not properties:
        return None
    if override_key:
        val = properties.get(override_key)
        return str(val).strip() if val is not None and str(val).strip() else None
    for key in _ZONE_ID_KEYS:
        val = properties.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def load_zones(path, override_key=None):
    """Return (zones list sorted by area, set of all property keys seen)."""
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    features = gj.get("features", [gj])
    zones = []
    all_props = set()
    for feat in features:
        geom = feat.get("geometry") or {}
        props = feat.get("properties") or {}
        all_props.update(props.keys())
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        zone_id = _get_zone_id(props, override_key)
        if not zone_id:
            continue
        zones.append({
            "id": zone_id,
            "geometry": geom,
            "area": _feature_area(feat),
        })
    zones.sort(key=lambda z: z["area"])
    return zones, all_props


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

def assign_zone(lon, lat, zones):
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
    parser.add_argument(
        "--zone-property",
        default=None,
        metavar="PROPERTY",
        help="GeoJSON property name to use as zone ID (auto-detected if omitted)",
    )
    args = parser.parse_args()

    # Load zones
    print(f"Loading zones from: {args.zones}")
    try:
        zones, all_props = load_zones(args.zones, args.zone_property)
    except FileNotFoundError:
        print(f"  ERROR: file not found — {args.zones}")
        sys.exit(1)

    if not zones:
        print("  ERROR: no named polygon features found in the GeoJSON.")
        if all_props:
            print(f"  Properties found in file: {sorted(all_props)}")
            print(f"  Re-run with: --zone-property <name>")
            print(f"  Example:     --zone-property {sorted(all_props)[0]}")
        else:
            print("  The file may contain no polygon features, or features have no properties.")
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

    # Assign zones
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
        marker = "" if zone in ("outside", "no_coordinates") else "  <--"
        print(f"  {zone:<35} {count:>5}  ({count/n_total*100:.1f}%){marker}")

    df.to_csv(args.out, index=False)
    print(f"\nSaved: {args.out}")


if __name__ == "__main__":
    main()
