"""Unit tests for cwt.cgt.analysis._utils helper functions."""

from __future__ import annotations

import math

import pytest

from cwt.cgt.analysis._utils import nan_to_none, safe_float, safe_pow


# ---------------------------------------------------------------------------
# safe_pow
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_safe_pow_normal() -> None:
    """Normal integer-like exponent returns the expected value."""
    result = safe_pow(2.0, 3.0)
    assert abs(result - 8.0) < 1e-10


@pytest.mark.unit
def test_safe_pow_zero_base() -> None:
    """Zero base always returns 0.0 regardless of exponent."""
    assert safe_pow(0.0, 5.0) == 0.0


@pytest.mark.unit
def test_safe_pow_zero_exponent() -> None:
    """Any positive base raised to the zeroth power is 1.0."""
    assert safe_pow(100.0, 0.0) == 1.0


@pytest.mark.unit
def test_safe_pow_extreme_exponent_is_finite() -> None:
    """Extreme exponent that would ordinarily overflow returns a finite float."""
    result = safe_pow(1e300, 1e10)
    assert math.isfinite(result), f"Expected finite result, got {result}"


@pytest.mark.unit
def test_safe_pow_negative_base() -> None:
    """Negative base is treated as non-positive, so 0.0 is returned — no crash."""
    result = safe_pow(-5.0, 3.0)
    assert result == 0.0


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_safe_float_normal() -> None:
    """Normal float is returned unchanged."""
    assert safe_float(3.14) == pytest.approx(3.14)


@pytest.mark.unit
def test_safe_float_none() -> None:
    """None is converted to NaN."""
    result = safe_float(None)
    assert math.isnan(result)


@pytest.mark.unit
def test_safe_float_integer() -> None:
    """Integer input is coerced to the equivalent float."""
    assert safe_float(5) == 5.0


@pytest.mark.unit
def test_safe_float_string_number() -> None:
    """Numeric string is coerced via float()."""
    assert safe_float("2.5") == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# nan_to_none
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_nan_to_none_nan() -> None:
    """float('nan') is replaced with None."""
    assert nan_to_none(float('nan')) is None


@pytest.mark.unit
def test_nan_to_none_inf() -> None:
    """Positive infinity is replaced with None."""
    assert nan_to_none(float('inf')) is None


@pytest.mark.unit
def test_nan_to_none_neg_inf() -> None:
    """Negative infinity is replaced with None."""
    assert nan_to_none(float('-inf')) is None


@pytest.mark.unit
def test_nan_to_none_finite_float() -> None:
    """Finite float is returned unchanged."""
    assert nan_to_none(42.0) == 42.0


@pytest.mark.unit
def test_nan_to_none_none_passthrough() -> None:
    """None (not a float) passes through unchanged."""
    assert nan_to_none(None) is None


@pytest.mark.unit
def test_nan_to_none_nested_dict_and_list() -> None:
    """Recursively replaces non-finite floats inside dicts and lists."""
    obj = {'a': float('nan'), 'b': [float('inf'), 1.0]}
    result = nan_to_none(obj)
    assert result == {'a': None, 'b': [None, 1.0]}


@pytest.mark.unit
def test_nan_to_none_non_float_types_preserved() -> None:
    """Non-float types (str, int) inside a dict are preserved unchanged."""
    obj = {'x': 'hello', 'y': 42}
    result = nan_to_none(obj)
    assert result == {'x': 'hello', 'y': 42}


@pytest.mark.unit
def test_nan_to_none_numpy_scalar() -> None:
    """numpy scalars with NaN or inf are replaced with None; finite scalars pass through."""
    import numpy as np
    assert nan_to_none(np.float64('nan')) is None
    assert nan_to_none(np.float64('inf')) is None
    assert nan_to_none(np.float64(3.14)) == np.float64(3.14)


# ---------------------------------------------------------------------------
# _prediction_summary edge cases (imported from phase41_analysis)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prediction_summary_empty_rows() -> None:
    """Empty row list returns the zero/None sentinel dict."""
    from cwt.cgt.analysis.phase41_analysis import _prediction_summary

    result = _prediction_summary([], 'some_key')
    assert result == {'r2': None, 'corr': None, 'count': 0, 'sign_agreement': None}


@pytest.mark.unit
def test_prediction_summary_single_trusted_row() -> None:
    """Single trusted row returns count=1; r2 may be None due to zero SS."""
    from cwt.cgt.analysis.phase41_analysis import _prediction_summary

    rows = [
        {
            'trusted_pair': True,
            'orientation_gap': 0.5,
            'predictor': 0.4,
        }
    ]
    result = _prediction_summary(rows, 'predictor')
    assert result['count'] == 1
    # With a single point, mean(y) == y[0] so SS == 0, hence r2 must be None.
    assert result['r2'] is None


@pytest.mark.unit
def test_prediction_summary_all_identical_y() -> None:
    """Constant y values produce SS <= 1e-15, so r2 is None."""
    from cwt.cgt.analysis.phase41_analysis import _prediction_summary

    rows = [
        {'trusted_pair': True, 'orientation_gap': 1.0, 'pred': 0.9},
        {'trusted_pair': True, 'orientation_gap': 1.0, 'pred': 1.1},
        {'trusted_pair': True, 'orientation_gap': 1.0, 'pred': 1.0},
    ]
    result = _prediction_summary(rows, 'pred')
    assert result['count'] == 3
    assert result['r2'] is None


# ---------------------------------------------------------------------------
# _derive_pooled_rule underdetermined guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_derive_pooled_rule_underdetermined() -> None:
    """_derive_pooled_rule raises ValueError when trusted rows < 6 (one per feature)."""
    from cwt.cgt.analysis.phase41_analysis import _derive_pooled_rule

    # 3 rows < 6 features — must raise before calling lstsq
    rows = [
        {
            'trusted_pair': True,
            'variance_alignment': 1.0,
            'local_area_share': 0.5,
            'share_geometry': 0.3,
            'local_tensor_share': 0.2,
            'local_covariance_share': 0.1,
            'local_area_channel': 0.4,
            'm2_gap': 0.01,
            'm2_gap_boundary': 0.02,
            'area_magnitude': 0.1,
            'local_baseline_scale': 1.0,
            'm2_gap_var': 0.001,
            'm2_gap_boundary_var': 0.002,
            'orientation_gap': 0.05,
        }
    ] * 3
    with pytest.raises(ValueError, match='at least 6'):
        _derive_pooled_rule(rows)
