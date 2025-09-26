"""Noise models including dephasing, amplitude, and delay jitter."""

from __future__ import annotations


def placeholder_noise_model(
    *,
    coherence_time: float = 250.0,
    drive_snr_db: float = 38.0,
    jitter_ps: float = 6.0,
) -> dict[str, float]:
    """Return a physically motivated noise model.

    Parameters
    ----------
    coherence_time:
        Characteristic phase-coherence time in microseconds.  The value is
        inverted to obtain the dephasing rate expressed in inverse
        microseconds.
    drive_snr_db:
        Signal-to-noise ratio of the drive envelope in decibels.  Higher
        values translate to smaller amplitude fluctuations.  The returned
        amplitude term represents the relative standard deviation of the
        drive.
    jitter_ps:
        Absolute timing jitter of the control electronics expressed in
        picoseconds.  The value is converted to nanoseconds to match the
        orchestrator’s conventions.

    Returns
    -------
    dict[str, float]
        Dictionary with the keys ``dephasing``, ``amplitude``, and ``jitter``
        populated with non-negative floating point values.
    """

    if coherence_time <= 0.0:
        raise ValueError("coherence_time must be positive.")
    if jitter_ps < 0.0:
        raise ValueError("jitter_ps must be non-negative.")

    coherence_time = float(coherence_time)
    drive_snr_db = float(drive_snr_db)
    jitter_ps = float(jitter_ps)

    # Convert microseconds to inverse microseconds to express dephasing
    # strength as a rate.  The small epsilon guards against unrealistic
    # coherence times that would otherwise produce unbounded values.
    eps = 1e-9
    dephasing_rate = 1.0 / max(coherence_time, eps)

    # Translate the envelope SNR into a relative amplitude noise level.  The
    # quantity is bounded to keep the standard deviation within sensible
    # limits and avoid catastrophic growth when the ratio is negative.
    amplitude_std = 10.0 ** (-drive_snr_db / 20.0)
    amplitude_std = min(max(amplitude_std, 0.0), 1.0)

    # Express jitter in nanoseconds to align with the simulator’s base units.
    jitter_ns = jitter_ps * 1e-3

    return {
        "dephasing": dephasing_rate,
        "amplitude": amplitude_std,
        "jitter": jitter_ns,
    }
