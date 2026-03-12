"""
scoring.py — Risk score computation and optional V (Price Volatility) dimension.

Key functions:
  compute_risk_score()      → composite risk score for a single region row
  fetch_price_volatility()  → live V scores via gridstatus (requires: pip install gridstatus)
"""

import pandas as pd


def compute_risk_score(
    row: pd.Series,
    toggle_P: bool = True,
    toggle_Q: bool = True,
    toggle_L: bool = True,
    toggle_S: bool = True,
    toggle_V: bool = False,
    weight_P: float = 1.0,
    weight_Q: float = 1.0,
    weight_L: float = 1.0,
    weight_S: float = 1.0,
    weight_V: float = 1.0,
) -> float:
    """
    Compute composite risk score for a single region row.

    Formula: RiskScore = Σ (toggle_i * weight_i * score_i)
    Scores range 1–3; toggles are 0 or 1; weights default to 1.0.
    V_volatility must be present in row if toggle_V is True.
    """
    score = 0.0
    if toggle_P:
        score += weight_P * row["P_permitting"]
    if toggle_Q:
        score += weight_Q * row["Q_queue"]
    if toggle_L:
        score += weight_L * row["L_load"]
    if toggle_S:
        score += weight_S * row["S_policy"]
    if toggle_V and "V_volatility" in row.index:
        v = row["V_volatility"]
        if pd.notna(v):
            score += weight_V * v
    return score


def apply_scores(
    df: pd.DataFrame,
    toggle_P: bool = True,
    toggle_Q: bool = True,
    toggle_L: bool = True,
    toggle_S: bool = True,
    toggle_V: bool = False,
    weight_P: float = 1.0,
    weight_Q: float = 1.0,
    weight_L: float = 1.0,
    weight_S: float = 1.0,
    weight_V: float = 1.0,
) -> pd.DataFrame:
    """
    Apply compute_risk_score to every row and add weighted component columns.
    Returns a copy of df with added columns:
      P_w, Q_w, L_w, S_w, [V_w,] RiskScore
    """
    out = df.copy()
    out["P_w"] = out["P_permitting"] * weight_P * toggle_P
    out["Q_w"] = out["Q_queue"] * weight_Q * toggle_Q
    out["L_w"] = out["L_load"] * weight_L * toggle_L
    out["S_w"] = out["S_policy"] * weight_S * toggle_S

    if toggle_V and "V_volatility" in out.columns:
        out["V_w"] = out["V_volatility"].fillna(0) * weight_V
    else:
        out["V_w"] = 0.0

    out["RiskScore"] = out.apply(
        compute_risk_score,
        axis=1,
        toggle_P=toggle_P,
        toggle_Q=toggle_Q,
        toggle_L=toggle_L,
        toggle_S=toggle_S,
        toggle_V=toggle_V,
        weight_P=weight_P,
        weight_Q=weight_Q,
        weight_L=weight_L,
        weight_S=weight_S,
        weight_V=weight_V,
    )
    return out.sort_values("RiskScore", ascending=False).reset_index(drop=True)


def fetch_price_volatility(lookback_days: int = 90) -> pd.DataFrame:
    """
    Fetch live price data via gridstatus and compute V (Price Volatility) scores.

    Requires: pip install gridstatus>=0.25

    Returns DataFrame with columns:
      region_id, price_std_dev, scarcity_hrs, V_volatility (1–3 normalised)

    Degrades gracefully: returns empty DataFrame on API failure.
    """
    try:
        from gridstatus import NYISO, Ercot
    except ImportError:
        raise ImportError(
            "gridstatus is not installed. Run: pip install gridstatus>=0.25"
        )

    import warnings

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=lookback_days)

    records = []

    # --- NYISO DAM LBMP by zone ---
    try:
        nyiso = NYISO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            nyiso_raw = nyiso.get_lmp(
                start=start,
                end=end,
                market="DAY_AHEAD_HOURLY",
                location_type="zone",
            )

        # Map NYISO zone names to our region_ids
        nyiso_zone_map = {
            "CAPITL": "NYISO_ABCDEF",
            "CENTRL": "NYISO_ABCDEF",
            "DUNWOD": "NYISO_GHI",
            "GENESE": "NYISO_ABCDEF",
            "H Q": "NYISO_ABCDEF",
            "HUD VL": "NYISO_GHI",
            "LONGIL": "NYISO_K",
            "MHK VL": "NYISO_ABCDEF",
            "MILLWD": "NYISO_GHI",
            "N.Y.C.": "NYISO_J",
            "NORTH": "NYISO_ABCDEF",
            "WEST": "NYISO_ABCDEF",
        }

        price_col = next(
            (c for c in nyiso_raw.columns if "lmp" in c.lower() or "price" in c.lower()),
            None,
        )
        loc_col = next(
            (c for c in nyiso_raw.columns if "location" in c.lower() or "zone" in c.lower()),
            None,
        )

        if price_col and loc_col:
            nyiso_raw["region_id"] = nyiso_raw[loc_col].map(nyiso_zone_map)
            nyiso_raw = nyiso_raw.dropna(subset=["region_id"])
            nyiso_raw[price_col] = pd.to_numeric(nyiso_raw[price_col], errors="coerce")

            for region_id, grp in nyiso_raw.groupby("region_id"):
                prices = grp[price_col].dropna()
                records.append(
                    {
                        "region_id": region_id,
                        "price_std_dev": prices.std(),
                        "scarcity_hrs": (prices > 100).sum(),
                    }
                )
    except Exception:
        # NYISO fetch failed; leave NYISO regions out
        pass

    # --- ERCOT Real-Time Settlement Point Prices ---
    try:
        ercot = Ercot()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ercot_raw = ercot.get_spp(
                start=start,
                end=end,
                market="DAY_AHEAD_HOURLY",
            )

        ercot_zone_map = {
            "HB_HOUSTON": "ERCOT_HOU",
            "HB_NORTH": "ERCOT_NORTH",
            "HB_WEST": "ERCOT_WEST",
            "HB_SOUTH": "ERCOT_SOUTH",
        }

        price_col = next(
            (c for c in ercot_raw.columns if "lmp" in c.lower() or "spp" in c.lower() or "price" in c.lower()),
            None,
        )
        loc_col = next(
            (
                c
                for c in ercot_raw.columns
                if "location" in c.lower() or "settlement" in c.lower()
            ),
            None,
        )

        if price_col and loc_col:
            ercot_raw = ercot_raw[ercot_raw[loc_col].isin(ercot_zone_map)]
            ercot_raw["region_id"] = ercot_raw[loc_col].map(ercot_zone_map)
            ercot_raw[price_col] = pd.to_numeric(ercot_raw[price_col], errors="coerce")

            for region_id, grp in ercot_raw.groupby("region_id"):
                prices = grp[price_col].dropna()
                records.append(
                    {
                        "region_id": region_id,
                        "price_std_dev": prices.std(),
                        "scarcity_hrs": (prices > 100).sum(),
                    }
                )
    except Exception:
        # ERCOT fetch failed; leave ERCOT regions out
        pass

    if not records:
        return pd.DataFrame(columns=["region_id", "price_std_dev", "scarcity_hrs", "V_volatility"])

    v_df = pd.DataFrame(records).groupby("region_id", as_index=False).mean()

    # Normalise price_std_dev to 1–3 scale
    std_min = v_df["price_std_dev"].min()
    std_max = v_df["price_std_dev"].max()
    if std_max > std_min:
        v_df["V_volatility"] = 1 + 2 * (v_df["price_std_dev"] - std_min) / (std_max - std_min)
    else:
        v_df["V_volatility"] = 2.0  # all regions identical → mid-point

    v_df["V_volatility"] = v_df["V_volatility"].round(2)
    return v_df[["region_id", "price_std_dev", "scarcity_hrs", "V_volatility"]]
