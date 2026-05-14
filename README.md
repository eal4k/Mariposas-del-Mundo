# Mariposas del Mundo — Field Documentation

Documentation, spatial data, and tools for the Mariposas del Mundo pollinator garden in Fair Haven Heights, New Haven, CT. Maintained by [your name] in collaboration with Kat Calhoun, Urban Resources Initiative (URI), Yale School of the Environment.

---

## About the site

Mariposas del Mundo is a community-led butterfly garden and monarch waystation at the corner of Hemingway and Eastern Streets, New Haven CT 06513, established in 2020 by Kat Calhoun through URI's Community Greenspace program. The site occupies a formerly vacant lot adjacent to Hemingway Creek, a small tributary of the Quinnipiac River system, in the Fair Haven Heights / Quinnipiac Meadows neighborhood.

The site is now in its sixth season, with a documented planting history spanning 2020–2024 including native trees, shrubs, and perennials across distinct planting-year zones. This continuous management record, combined with its position within URI's 47-site New Haven Greenspace network, makes Mariposas del Mundo a useful candidate for longitudinal urban soil ecological research.

**Location:** 41.302°N, 72.862°W · USDA Zone 7a · [Google My Maps](INSERT_LINK)  
**iNaturalist project:** [Mariposas del Mundo Biodiversity Survey](INSERT_LINK)

---

## About this repository

This repository serves three purposes:

1. **Documentation** — a versioned record of planting history, zone boundaries, and management decisions that survives intern and volunteer turnover.
2. **Data infrastructure** — spatial zone files, observation exports, and TBI decomposition records that connect field work to analysis.
3. **Tools** — scripts for linking iNaturalist observations to site zones.

The work here is the foundation for a planned soil microbiome characterization study in collaboration with URI. The methodology is designed to be portable to other URI Greenspace sites.

---

## Repository structure

```
mariposas-del-mundo/
├── spatial/
│   ├── mariposas_zones.geojson     # zone polygon master file
│   └── mariposas_zones.kml         # KML version for Google My Maps / iNaturalist
├── log/
│   └── planting_log.csv            # all planting and management events by zone
├── data/
│   └── tbi/                        # Tea Bag Index mass-loss records
├── protocols/
│   ├── tbi_protocol.md             # Tea Bag Index field and lab instructions
│   ├── photo_protocol.md           # fixed-point photography convention
│   └── observation_protocol.md     # iNaturalist tagging instructions
├── scripts/
│   └── zone_mapper.py              # assigns iNaturalist observations to zones
├── .gitignore
└── README.md
```

Photos are archived in Google Photos, not this repository. The planting log and TBI records are the curated data files maintained here.

---

## Planting history

| Year | Plantings (summary) |
|------|---------------------|
| 2020 | 8 shrubs (Ilex, Ninebark), 30 perennials (phlox, agastache, coreopsis). Site founded by Kat. |
| 2021 | 3 trees (2 serviceberry, 1 redbud), 3 spicebush. Trees planted creekside. |
| 2022 | 7 shrubs (clethra ×5, pussy willow ×2, inkberry), 15 perennials. |
| 2023 | 15 shrubs (dogwood, elderberry, witchhazel, blueberry, buttonbush, snowberry), 22 perennials (turtlehead, coreopsis, blue vervain, joe pye weed, coneflower, aster). |
| 2024 | 2 pussy willow, 28 perennials (wild bergamot, wild geranium, highbush blueberry, wild indigo, cardinal flower, red columbine). |

Full species-level detail is in `log/planting_log.csv`. Ongoing management includes knotweed cutting along the creek edge; mugwort, garlic mustard, and dame's rocket are also present as background management context.

---

## Zone system

The site is divided into zones corresponding roughly to planting years and microhabitat areas. Zone boundaries are mapped in `spatial/mariposas_zones.geojson`.

### Naming convention

Zones use alphanumeric IDs in the format `A1`, `B2`, etc. — content-neutral names that remain stable across site changes and intern turnover. Zone names do not encode planting year or species; that information lives in the planting log, joined by `zone_id`.

The zone GeoJSON properties include:
- `zone_id` — the stable identifier (e.g. `A1`)
- `planting_year` — year the area was first planted
- `description` — short notes on dominant species or microhabitat

### Site zones

| zone_id | planting_year | notes |
|---------|--------------|-------|
| [fill in from your GeoJSON] | | |

---

## Making observations in the field

Observations are recorded using the iNaturalist mobile app and automatically aggregated into the [Mariposas del Mundo Biodiversity Survey](INSERT_LINK) project.

### Step-by-step

1. Open the iNaturalist app and start a new observation.
2. Photograph the organism. Multiple angles help with identification.
3. Before submitting, add a **tag** in the field observations tab using the format `zone-A1` (replacing `A1` with the zone you are standing in).
4. If the plant was deliberately planted (as most here are), toggle **captive / cultivated** to on. Wild volunteers, weeds, insects, fungi, and birds should be marked wild.
5. Submit. The observation will appear in the project automatically.

### Zone tagging reference

Use the exact format `zone-A1`, `zone-B2`, etc. — lowercase `zone-`, hyphen, then the zone ID. Consistent formatting is important for the automated zone-assignment script.

If you are uncertain which zone you are in, submit without a tag and note the approximate location in the observation description. Coordinates can be used to assign the zone later.

---

## Tools

### zone_mapper.py

Assigns iNaturalist observation coordinates to zone polygons using point-in-polygon geometry. Appends an `assigned_zone` column to the CSV.

**Requirements:** Python 3 and pandas.

```bash
pip install pandas
```

**Basic usage** (run from repo root, expects files at default paths):

```bash
python scripts/zone_mapper.py
```

**Explicit paths:**

```bash
python scripts/zone_mapper.py \
  --zones spatial/mariposas_zones.geojson \
  --obs observations_2026-05-14.csv \
  --out data/observations_2026-05-14_zoned.csv
```

**Getting the iNaturalist CSV:**  
Go to the project page → Export Observations → keep default columns → download. Name the file with the date before running the script.

---

## Tea Bag Index (TBI)

The TBI is a standardized decomposition measurement using Lipton green and rooibos tea bags buried at 8 cm depth for approximately 90 days. It produces two parameters:

- **k** — decomposition rate (how fast labile material breaks down)
- **S** — stabilization factor (how much labile material persists rather than decomposing)

TBI is the minimum protocol for inclusion in the [Global Urban Soil Ecology and Education Network (GLUSEEN)](https://doi.org/10.1093/jue/jux002) and connects Mariposas observations to a global citizen science dataset at [teatime4science.org](http://www.teatime4science.org).

**First deployment planned:** Summer 2026, one set of bag pairs per zone.

Field and lab instructions are in `protocols/tbi_protocol.md`. Mass-loss records go in `data/tbi/`.

---

## Data files

| File | Description | Updated |
|------|-------------|---------|
| `spatial/mariposas_zones.geojson` | Zone polygon master | After each field revision |
| `log/planting_log.csv` | All planting and management events | After each site visit |
| `data/tbi/` | TBI mass-loss records by zone and season | After each retrieval |

Dated iNaturalist export snapshots (`observations_YYYY-MM-DD.csv`) are committed to `data/` when a significant threshold of new observations has accumulated. Raw downloads are not committed to the repo.

---

## Acknowledgments

**Site founder and group leader:** Kat Calhoun, Urban Resources Initiative  
**URI Greenspace program:** Yale School of the Environment, New Haven CT  
**Methodology context:** [GLUSEEN](https://doi.org/10.1093/jue/jux002) urban soil ecology network; [Tea Bag Index](http://www.teatime4science.org)

---

## License

Documentation and data (`.md`, `.csv`, `.geojson`) are released under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).  
Code (`scripts/`) is released under the [MIT License](https://opensource.org/licenses/MIT).

---

*Contributions welcome. Open an issue or contact [your email] with questions.*
