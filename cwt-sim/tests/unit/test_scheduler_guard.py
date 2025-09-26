"""Tests for FS guard early-abort heuristics."""

from cwt.orchestrator.scheduler import _should_abort_fs


def test_should_abort_fs_waits_for_minimum_progress() -> None:
    """Early abort does not trigger before the warmup fraction of steps."""

    total_steps = 100
    # Even with a high exceedance count, the guard should wait until
    # the minimum fraction of steps has elapsed.
    assert not _should_abort_fs(m_bad=9, n_seen=10, total_steps=total_steps, q=0.95)


def test_should_abort_fs_triggers_with_cushion() -> None:
    """Abort once the exceedance ratio overtakes the cushioned threshold."""

    total_steps = 200
    # 13/200 = 0.065, which exceeds the 0.06 cushioned threshold once the
    # warmup period has elapsed.
    assert _should_abort_fs(m_bad=13, n_seen=40, total_steps=total_steps, q=0.95)


def test_should_abort_fs_respects_quantile_parameter() -> None:
    """The quantile adjusts the abort threshold before the cushion is added."""

    total_steps = 1000
    # For q=0.9 the base fraction is 0.1; after adding the cushion we require
    # more than 0.11 of the steps to exceed the guard.
    assert not _should_abort_fs(m_bad=109, n_seen=200, total_steps=total_steps, q=0.9)
    assert _should_abort_fs(m_bad=111, n_seen=200, total_steps=total_steps, q=0.9)
