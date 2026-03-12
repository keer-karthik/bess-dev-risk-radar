"""
data_loader.py — Load and process all source data for the BESS Dev Risk Radar.

Key functions:
  parse_nyiso_queue()       → queued BESS MW by NYISO zone group
  parse_ercot_gis()         → queued BESS MW by ERCOT CDR zone (GIS large-gen sheet)
  parse_ercot_collocated()  → queued co-located battery MW by ERCOT CDR zone
  load_region_risk()        → final region_risk DataFrame (8 rows)
  load_permitting()         → ny_permitting + tx_permitting combined DataFrame
"""

from pathlib import Path
import pandas as pd
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

NYISO_QUEUE_PATH = RAW_DIR / "NYISO-Interconnection-Queue-1-31-2026.xlsx"
ERCOT_GIS_PATH = RAW_DIR / "GIS_Report_February2026.xlsx"
ERCOT_COLOC_PATH = RAW_DIR / "Co-located_Battery_Report_February2026.xlsx"
REGION_RISK_PATH = DATA_DIR / "region_risk.csv"
NY_PERM_PATH = DATA_DIR / "ny_permitting.csv"
TX_PERM_PATH = DATA_DIR / "tx_permitting.csv"

# ---------------------------------------------------------------------------
# NYISO zone groupings
# ---------------------------------------------------------------------------
NYISO_ZONE_MAP = {
    "J": "NYISO_J",
    "K": "NYISO_K",
    "G": "NYISO_GHI",
    "H": "NYISO_GHI",
    "I": "NYISO_GHI",
    "A": "NYISO_ABCDEF",
    "B": "NYISO_ABCDEF",
    "C": "NYISO_ABCDEF",
    "D": "NYISO_ABCDEF",
    "E": "NYISO_ABCDEF",
    "F": "NYISO_ABCDEF",
}

# ERCOT CDR zone → our 4 ERCOT regions
ERCOT_ZONE_MAP = {
    "NORTH":     "ERCOT_NORTH",
    "PANHANDLE": "ERCOT_NORTH",
    "WEST":      "ERCOT_WEST",
    "SOUTH":     "ERCOT_SOUTH",
    "HOUSTON":   "ERCOT_HOU",
    "COASTAL":   "ERCOT_HOU",
}

# Approximate peak load (MW) per region — used for bess_to_peak_ratio
PEAK_LOAD_MW = {
    "NYISO_K":       5_250,
    "NYISO_GHI":     6_500,
    "NYISO_J":      11_500,
    "NYISO_ABCDEF": 13_000,
    "ERCOT_HOU":    30_000,
    "ERCOT_NORTH":  25_000,
    "ERCOT_WEST":    8_000,
    "ERCOT_SOUTH":  15_000,
}

# ---------------------------------------------------------------------------
# Parse functions
# ---------------------------------------------------------------------------

def parse_nyiso_queue() -> pd.DataFrame:
    """
    Parse NYISO interconnection queue XLSX.
    Returns DataFrame with columns: region_id, queued_bess_mw, bess_projects
    Source: January 2026 snapshot; Type/Fuel 'ES' = Energy Storage.
    Combines 'Interconnection Queue' (pre-cluster) and 'Cluster Projects' (in active study)
    sheets — both represent live active development pipelines.
    """
    active_sheets = ["Interconnection Queue", " Cluster Projects"]
    frames = []
    for sheet in active_sheets:
        df = pd.read_excel(NYISO_QUEUE_PATH, sheet_name=sheet)
        bess = df[df["Type/ Fuel"] == "ES"].copy()
        bess["SP (MW)"] = pd.to_numeric(bess["SP (MW)"], errors="coerce")
        bess["region_id"] = bess["Z"].map(NYISO_ZONE_MAP)
        frames.append(bess[bess["region_id"].notna()])

    combined = pd.concat(frames, ignore_index=True)
    result = (
        combined.groupby("region_id")["SP (MW)"]
        .agg(queued_bess_mw="sum", bess_projects="count")
        .reset_index()
    )
    return result


def parse_ercot_gis() -> pd.DataFrame:
    """
    Parse ERCOT GIS Report (February 2026) — Large Gen sheet.
    Returns DataFrame with columns: region_id, ercot_queued_bess_mw
    Source: Projects in active GIM study phases (no IA-cancelled/withdrawn filter needed
    as all rows are active per report design).
    """
    df = pd.read_excel(
        ERCOT_GIS_PATH,
        sheet_name="Project Details - Large Gen",
        header=30,
        skiprows=[31, 32, 33, 34],
    )
    df["Capacity (MW)"] = pd.to_numeric(df["Capacity (MW)"], errors="coerce")

    # Filter to storage/battery projects
    bess_mask = (
        df["Project Name"].str.contains(
            "Storage|Battery|BESS|SLF|ESS", case=False, na=False
        )
        | df["Fuel"].str.contains("Battery|ESS|OTH", case=False, na=False)
    )
    bess = df[bess_mask].copy()
    bess["region_id"] = bess["CDR Reporting Zone"].map(ERCOT_ZONE_MAP)
    bess = bess[bess["region_id"].notna()]

    result = (
        bess.groupby("region_id")["Capacity (MW)"]
        .agg(ercot_queued_bess_mw="sum", ercot_bess_projects="count")
        .reset_index()
    )
    return result


def parse_ercot_collocated() -> pd.DataFrame:
    """
    Parse ERCOT Co-located Battery Report (February 2026).
    All entries are 'Planned' (queued) — returns MW by region.
    """
    sheets = [
        "Co-located with Solar",
        "Co-located with Wind",
        "Co-located with Thermal",
        "Stand-Alone",
    ]
    dfs = []
    for sh in sheets:
        try:
            df = pd.read_excel(
                ERCOT_COLOC_PATH,
                sheet_name=sh,
                header=14,
                skiprows=[15, 16, 17],
            )
            df = df[df["INR"].notna()]
            df["source"] = sh
            dfs.append(df)
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame(columns=["region_id", "coloc_queued_mw"])

    all_bess = pd.concat(dfs, ignore_index=True)
    all_bess["Capacity (MW)"] = pd.to_numeric(all_bess["Capacity (MW)"], errors="coerce")
    all_bess["region_id"] = all_bess["CDR Reporting Zone"].map(ERCOT_ZONE_MAP)
    all_bess = all_bess[all_bess["region_id"].notna()]

    result = (
        all_bess.groupby("region_id")["Capacity (MW)"]
        .sum()
        .reset_index()
        .rename(columns={"Capacity (MW)": "coloc_queued_mw"})
    )
    return result


# ---------------------------------------------------------------------------
# Load pre-built CSVs
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# GIS zone boundary loader
# ---------------------------------------------------------------------------

# ArcGIS REST endpoints — open, no auth required
_ERCOT_GEOJSON_URL = (
    "https://services3.arcgis.com/fwwoCWVtaahwlvxO/ArcGIS/rest/services/"
    "ERCOT_Load_Zones/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson"
)
_NYISO_GEOJSON_URL = (
    "https://services.nyserda.ny.gov/arcgis/rest/services/Electric/"
    "Utility_and_Load_Zones/MapServer/0/query?where=1%3D1&outFields=*&f=geojson"
)

# ERCOT hub names as they appear in the ArcGIS feature service
_ERCOT_GEO_MAP = {
    # HubName variants
    "HB_HOUSTON": "ERCOT_HOU",
    "HB_NORTH":   "ERCOT_NORTH",
    "HB_WEST":    "ERCOT_WEST",
    "HB_SOUTH":   "ERCOT_SOUTH",
    # plain variants (fallback)
    "HOUSTON":    "ERCOT_HOU",
    "NORTH":      "ERCOT_NORTH",
    "WEST":       "ERCOT_WEST",
    "SOUTH":      "ERCOT_SOUTH",
    # COAST sometimes appears for Houston area
    "COAST":      "ERCOT_HOU",
}


def load_zone_geodata(iso: str):
    """
    Fetch zone boundary GeoJSON from open ArcGIS REST services and return a
    GeoDataFrame indexed by region_id with a single 'geometry' column.

    Parameters
    ----------
    iso : "NYISO" or "ERCOT"

    Returns
    -------
    geopandas.GeoDataFrame  or  None on any failure
    """
    try:
        import geopandas as gpd
        import requests
    except ImportError:
        print("geopandas or requests not installed — zone map unavailable", file=sys.stderr)
        return None

    try:
        url = _NYISO_GEOJSON_URL if iso == "NYISO" else _ERCOT_GEOJSON_URL
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        geojson = resp.json()

        if not geojson.get("features"):
            return None

        gdf = gpd.GeoDataFrame.from_features(geojson["features"])
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)

        # --- detect the zone-name field ---
        cols_lower = {c.lower(): c for c in gdf.columns}

        if iso == "NYISO":
            # Try common field names; NYSERDA service typically uses 'ZoneName' or 'Zone'
            for candidate in ("zone", "zonename", "zone_name", "name", "label"):
                if candidate in cols_lower:
                    zone_field = cols_lower[candidate]
                    break
            else:
                print(f"NYISO GeoJSON columns: {list(gdf.columns)}", file=sys.stderr)
                return None

            gdf["region_id"] = gdf[zone_field].str.strip().str.upper().map(NYISO_ZONE_MAP)
            gdf = gdf.dropna(subset=["region_id"])
            # dissolve individual zones (A–F) into our 4 grouped regions
            gdf = gdf.dissolve(by="region_id").reset_index()[["region_id", "geometry"]]

        else:  # ERCOT
            for candidate in ("zone_name", "zonename", "name", "hubname", "hub_name", "label"):
                if candidate in cols_lower:
                    zone_field = cols_lower[candidate]
                    break
            else:
                print(f"ERCOT GeoJSON columns: {list(gdf.columns)}", file=sys.stderr)
                return None

            gdf["region_id"] = gdf[zone_field].str.strip().str.upper().map(_ERCOT_GEO_MAP)
            gdf = gdf.dropna(subset=["region_id"])
            gdf = gdf[["region_id", "geometry"]]

        if gdf.empty:
            return None

        return gdf.set_index("region_id")

    except Exception as exc:
        print(f"load_zone_geodata({iso}) failed: {exc}", file=sys.stderr)
        return None


def load_region_risk() -> pd.DataFrame:
    """Load the master region_risk.csv table."""
    return pd.read_csv(REGION_RISK_PATH)


def load_permitting() -> pd.DataFrame:
    """Load and combine NY + TX permitting CSV tables."""
    ny = pd.read_csv(NY_PERM_PATH)
    tx = pd.read_csv(TX_PERM_PATH)
    return pd.concat([ny, tx], ignore_index=True)
