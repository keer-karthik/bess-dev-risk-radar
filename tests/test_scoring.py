"""
Unit tests for scoring.py — compute_risk_score() and apply_scores().
Run with: python -m pytest tests/test_scoring.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scoring import apply_scores, compute_risk_score


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_row():
    return pd.Series(
        {
            "region_id": "NYISO_GHI",
            "P_permitting": 3,
            "Q_queue": 3,
            "L_load": 3,
            "S_policy": 3,
        }
    )


@pytest.fixture
def k_row():
    return pd.Series(
        {
            "region_id": "NYISO_K",
            "P_permitting": 3,
            "Q_queue": 3,
            "L_load": 2,
            "S_policy": 3,
        }
    )


@pytest.fixture
def south_row():
    return pd.Series(
        {
            "region_id": "ERCOT_SOUTH",
            "P_permitting": 1,
            "Q_queue": 3,
            "L_load": 2,
            "S_policy": 2,
        }
    )


@pytest.fixture
def full_df():
    return pd.DataFrame(
        [
            {"region_id": "NYISO_GHI", "P_permitting": 3, "Q_queue": 3, "L_load": 3, "S_policy": 3},
            {"region_id": "NYISO_J",   "P_permitting": 3, "Q_queue": 3, "L_load": 3, "S_policy": 3},
            {"region_id": "NYISO_K",   "P_permitting": 3, "Q_queue": 3, "L_load": 2, "S_policy": 3},
            {"region_id": "ERCOT_HOU", "P_permitting": 2, "Q_queue": 3, "L_load": 3, "S_policy": 3},
            {"region_id": "ERCOT_NORTH","P_permitting": 1,"Q_queue": 3, "L_load": 3, "S_policy": 3},
            {"region_id": "NYISO_ABCDEF","P_permitting":2,"Q_queue": 3, "L_load": 2, "S_policy": 3},
            {"region_id": "ERCOT_WEST","P_permitting": 2, "Q_queue": 3, "L_load": 2, "S_policy": 2},
            {"region_id": "ERCOT_SOUTH","P_permitting":1, "Q_queue": 3, "L_load": 2, "S_policy": 2},
        ]
    )


# ---------------------------------------------------------------------------
# compute_risk_score tests
# ---------------------------------------------------------------------------

def test_all_off_returns_zero(sample_row):
    score = compute_risk_score(
        sample_row,
        toggle_P=False, toggle_Q=False, toggle_L=False, toggle_S=False
    )
    assert score == 0.0


def test_only_P_on(sample_row):
    score = compute_risk_score(
        sample_row,
        toggle_P=True, toggle_Q=False, toggle_L=False, toggle_S=False
    )
    assert score == 3.0


def test_only_Q_on(sample_row):
    score = compute_risk_score(
        sample_row,
        toggle_P=False, toggle_Q=True, toggle_L=False, toggle_S=False
    )
    assert score == 3.0


def test_only_L_on(sample_row):
    score = compute_risk_score(
        sample_row,
        toggle_P=False, toggle_Q=False, toggle_L=True, toggle_S=False
    )
    assert score == 3.0


def test_only_S_on(sample_row):
    score = compute_risk_score(
        sample_row,
        toggle_P=False, toggle_Q=False, toggle_L=False, toggle_S=True
    )
    assert score == 3.0


def test_all_on_nyiso_ghi_equals_12(sample_row):
    score = compute_risk_score(sample_row)
    assert score == 12.0


def test_all_on_ercot_south_equals_8(south_row):
    score = compute_risk_score(south_row)
    assert score == 8.0


def test_double_weight_P_nyiso_k(k_row):
    # P=3 (w=2) + Q=3 (w=1) + L=2 (w=1) + S=3 (w=1) = 6+3+2+3 = 14
    score = compute_risk_score(k_row, weight_P=2.0)
    assert score == 14.0


def test_v_not_applied_when_toggle_off(sample_row):
    row_with_v = sample_row.copy()
    row_with_v["V_volatility"] = 2.5
    score = compute_risk_score(row_with_v, toggle_V=False)
    assert score == 12.0


def test_v_applied_when_toggle_on(sample_row):
    row_with_v = sample_row.copy()
    row_with_v["V_volatility"] = 2.0
    score = compute_risk_score(row_with_v, toggle_V=True)
    assert score == 14.0


def test_v_nan_excluded(sample_row):
    """V=NaN should not count even when toggle is on."""
    import math
    row_with_v = sample_row.copy()
    row_with_v["V_volatility"] = float("nan")
    score = compute_risk_score(row_with_v, toggle_V=True)
    assert score == 12.0


# ---------------------------------------------------------------------------
# apply_scores tests
# ---------------------------------------------------------------------------

def test_apply_scores_all_on_sorted(full_df):
    result = apply_scores(full_df)
    assert result.iloc[0]["region_id"] in ("NYISO_GHI", "NYISO_J")  # tied at 12
    assert result.iloc[-1]["region_id"] == "ERCOT_SOUTH"


def test_apply_scores_all_off_zero(full_df):
    result = apply_scores(
        full_df,
        toggle_P=False, toggle_Q=False, toggle_L=False, toggle_S=False
    )
    assert (result["RiskScore"] == 0).all()


def test_apply_scores_s_weight_2_raises_nyiso(full_df):
    """All NYISO regions have S=3; doubling S weight adds 3 to each NYISO score."""
    base = apply_scores(full_df)
    weighted = apply_scores(full_df, weight_S=2.0)

    nyiso = ["NYISO_GHI", "NYISO_J", "NYISO_K", "NYISO_ABCDEF"]
    for rid in nyiso:
        base_score = base.loc[base["region_id"] == rid, "RiskScore"].values[0]
        new_score = weighted.loc[weighted["region_id"] == rid, "RiskScore"].values[0]
        assert new_score == base_score + 3.0, f"Failed for {rid}"


def test_apply_scores_columns_present(full_df):
    result = apply_scores(full_df)
    for col in ["P_w", "Q_w", "L_w", "S_w", "V_w", "RiskScore"]:
        assert col in result.columns


def test_ercot_south_lowest_all_on(full_df):
    result = apply_scores(full_df)
    assert result.iloc[-1]["region_id"] == "ERCOT_SOUTH"
