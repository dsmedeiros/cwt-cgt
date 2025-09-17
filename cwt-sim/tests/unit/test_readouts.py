"""Unit tests for readout and memory helpers."""

from __future__ import annotations

import numpy as np
import pytest

from cwt.graph import factories
from cwt.layers import readouts


class _StubRNG:
    def __init__(self, values: np.ndarray) -> None:
        self._values = np.asarray(values, dtype=int)
        self.last_lam: np.ndarray | None = None

    def poisson(self, lam: np.ndarray) -> np.ndarray:
        self.last_lam = np.asarray(lam, dtype=float)
        return self._values.copy()


class _BadRNG:
    pass


def test_memory_uniform_charge_scales_weights() -> None:
    Phi = 1.5
    chi = np.array([0.2, 0.3, 0.5])
    memory = readouts.memory_uniform_charge(Phi, chi)
    np.testing.assert_allclose(memory, Phi * chi)


def test_memory_uniform_charge_psi_amp_uses_amplitude_distribution() -> None:
    Phi = 2.0
    psi = np.array([1.0 + 0.0j, 0.0 + 0.0j, 2.0 + 0.0j])
    memory = readouts.memory_uniform_charge(Phi, mode="psi_amp", pQ=psi)
    amplitudes = np.abs(psi) ** 2
    expected = Phi * amplitudes / amplitudes.sum()
    np.testing.assert_allclose(memory, expected)


def test_memory_uniform_charge_centrality_mode_normalises() -> None:
    Phi = 3.0
    centrality = np.array([1.0, 3.0, 2.0])
    memory = readouts.memory_uniform_charge(Phi, mode="centrality", centrality=centrality)
    expected = Phi * centrality / centrality.sum()
    np.testing.assert_allclose(memory, expected)


def test_memory_uniform_charge_one_hot_targets_index() -> None:
    Phi = 0.75
    probs = np.array([0.1, 0.2, 0.7])
    memory = readouts.memory_uniform_charge(Phi, mode="one_hot", target=2, pQ=probs)
    expected = np.zeros_like(probs)
    expected[2] = Phi
    np.testing.assert_allclose(memory, expected)


def test_memory_direction_locked_scalar_gradient() -> None:
    Phi = 0.5
    s = np.array([0.2, 0.4, 0.6])
    grad_theta = np.array([1.0, -2.0, 0.5])
    t_loop = 0.25

    memory = readouts.memory_direction_locked(Phi, s, t_loop, grad_theta)
    expected = Phi * s * grad_theta * t_loop
    np.testing.assert_allclose(memory, expected)


def test_memory_direction_locked_vector_projection() -> None:
    Phi = 2.0
    s = np.array([0.2, 0.3, 0.4])
    grad_theta = np.array([[1.0, 0.0], [0.0, 2.0], [1.0, -1.0]])
    t_loop = np.array([0.5, -1.5])

    memory = readouts.memory_direction_locked(Phi, s, t_loop, grad_theta)
    projected = grad_theta @ t_loop
    expected = Phi * s * projected
    np.testing.assert_allclose(memory, expected)


def test_memory_direction_locked_invalid_shape_raises() -> None:
    Phi = 1.0
    s = np.array([0.1, 0.2])
    grad_theta = np.array([0.5, 0.5])
    with pytest.raises(ValueError):
        readouts.memory_direction_locked(Phi, s, np.array([1.0, 2.0]), grad_theta)


def test_memory_current_coupled_normalises_by_max() -> None:
    Phi = 2.0
    currents = np.array([1.0, -3.0, 0.0])
    memory = readouts.memory_current_coupled(Phi, currents)
    expected = Phi * currents / 3.0
    np.testing.assert_allclose(memory, expected)

    zero_memory = readouts.memory_current_coupled(Phi, np.zeros_like(currents))
    np.testing.assert_allclose(zero_memory, np.zeros_like(currents))


def test_readout_stochastic_temperature_limits() -> None:
    probs = np.array([0.1, 0.7, 0.2])
    memory = np.zeros_like(probs)

    choice, weights = readouts.readout_stochastic(probs, memory, T=0.0, eta=1.0)
    assert choice == int(np.argmax(probs))
    np.testing.assert_allclose(weights, np.eye(3)[choice])

    np.random.seed(0)
    _, weights_high_T = readouts.readout_stochastic(probs, memory, T=1e6, eta=0.0)
    np.testing.assert_allclose(
        weights_high_T, np.full_like(probs, 1.0 / probs.size), atol=1e-6
    )


def test_readout_stochastic_incorporates_memory_bias() -> None:
    probs = np.array([0.3, 0.7])
    memory = np.array([2.0, 0.0])
    T = 0.5
    eta = 0.8

    _, weights = readouts.readout_stochastic(probs, memory, T=T, eta=eta)

    field = np.log(probs) + eta * memory
    scaled = field / T
    finite = np.isfinite(scaled)
    logits = np.full_like(probs, -np.inf)
    logits[finite] = scaled[finite] - np.max(scaled[finite])
    expected = np.exp(np.where(np.isfinite(logits), logits, -np.inf))
    expected = expected / expected.sum()
    np.testing.assert_allclose(weights, expected)


def test_readout_percolation_without_graph_counts_active() -> None:
    probs = np.array([0.9, 0.1, 0.8])
    result = readouts.readout_percolation(probs, p_crit=0.5, theta_perc=0.4)
    assert result == {"fired": True, "size": 2}


def test_readout_percolation_with_graph_components() -> None:
    substrate = factories.line3(weight=1.0, delay=1.0, bidir=True)
    probs = np.array([0.9, 0.9, 0.1])
    result = readouts.readout_percolation(probs, p_crit=0.5, theta_perc=0.5, G=substrate)
    assert result == {"fired": True, "size": 2}

    with pytest.raises(ValueError):
        readouts.readout_percolation(np.ones(2), p_crit=0.5, theta_perc=0.5, G=substrate)


def test_readout_spiking_uses_supplied_rng() -> None:
    probs = np.array([0.3, 0.6])
    signal = np.array([0.1, 0.4])
    memory = np.array([0.2, -0.1])
    stub = _StubRNG(values=np.array([3, 10]))

    result = readouts.readout_spiking(
        probs,
        signal,
        memory,
        r0=5.0,
        c1=1.0,
        c2=1.5,
        c3=0.5,
        window=2.0,
        thresh=12,
        rng=stub,
    )

    expected_drive = np.array([0.3, 0.6]) + 1.5 * signal + 0.5 * memory
    expected_rates = 5.0 * np.clip(expected_drive, 0.0, None)
    expected_lambda = expected_rates * 2.0

    np.testing.assert_allclose(stub.last_lam, expected_lambda)
    assert result == {"fired": True, "spikes_total": 13}

    with pytest.raises(TypeError):
        readouts.readout_spiking(
            probs,
            signal,
            memory,
            r0=1.0,
            c1=1.0,
            c2=1.0,
            c3=1.0,
            window=1.0,
            thresh=1,
            rng=_BadRNG(),
        )


def test_edge_currents_balances_flux() -> None:
    substrate = factories.dimer(weight=1.0, delay=1.0, bidir=True)
    pQ = np.array([0.4, 0.6])
    theta = np.array([0.0, np.pi / 2.0])

    currents = readouts.edge_currents(substrate, pQ, theta)

    expected_magnitude = np.sqrt(pQ[0] * pQ[1])
    expected = np.array([-2.0 * expected_magnitude, 2.0 * expected_magnitude])

    np.testing.assert_allclose(currents, expected)
    assert np.isclose(currents.sum(), 0.0)

    with pytest.raises(TypeError):
        readouts.edge_currents(object(), pQ, theta)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        readouts.edge_currents(substrate, np.ones(1), theta)
