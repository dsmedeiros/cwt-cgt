# Gate C: topology robustness under noise

Phase noise sweep: 0.000, 0.050, 0.100, 0.200, 0.350
Amplitude noise σ_amp: 0.020
Delay jitter σ_tau: 0.020
Trials per noise level: 6
Loop steps: 120
Thresholds — overlap: 0.90, coherence: 0.50

## Graph: ring3

Loop flux magnitude: 2.015e-02

- σ_phase = 0.000 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -2.718e-03 with CI [-2.727e-03, -2.709e-03] (width 1.825e-05)
  - ⟨s̄⟩: 1.000 with CI [9.997e-01, 9.997e-01]
  - ⟨overlap⟩: 1.000 with CI [9.999e-01, 9.999e-01]
  - Quantization claim: yes
- σ_phase = 0.050 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -2.556e-03 with CI [-2.622e-03, -2.489e-03] (width 1.327e-04)
  - ⟨s̄⟩: 0.944 with CI [9.175e-01, 9.706e-01]
  - ⟨overlap⟩: 0.998 with CI [9.982e-01, 9.986e-01]
  - Quantization claim: yes
- σ_phase = 0.100 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -2.122e-03 with CI [-2.375e-03, -1.869e-03] (width 5.060e-04)
  - ⟨s̄⟩: 0.787 with CI [6.928e-01, 8.820e-01]
  - ⟨overlap⟩: 0.994 with CI [9.935e-01, 9.951e-01]
  - Quantization claim: yes
- σ_phase = 0.200 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -1.514e-03 with CI [-1.852e-03, -1.176e-03] (width 6.763e-04)
  - ⟨s̄⟩: 0.568 with CI [4.395e-01, 6.956e-01]
  - ⟨overlap⟩: 0.982 with CI [9.812e-01, 9.833e-01]
  - Quantization claim: yes
- σ_phase = 0.350 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -1.619e-03 with CI [-1.909e-03, -1.329e-03] (width 5.801e-04)
  - ⟨s̄⟩: 0.621 with CI [5.081e-01, 7.329e-01]
  - ⟨overlap⟩: 0.959 with CI [9.569e-01, 9.611e-01]
  - Quantization claim: yes

## Graph: rr8

Loop flux magnitude: 7.554e-02

- σ_phase = 0.000 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -4.511e-03 with CI [-4.519e-03, -4.504e-03] (width 1.434e-05)
  - ⟨s̄⟩: 1.000 with CI [9.997e-01, 9.997e-01]
  - ⟨overlap⟩: 1.000 with CI [9.998e-01, 9.998e-01]
  - Quantization claim: yes
- σ_phase = 0.050 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -4.231e-03 with CI [-4.348e-03, -4.114e-03] (width 2.335e-04)
  - ⟨s̄⟩: 0.937 with CI [9.098e-01, 9.649e-01]
  - ⟨overlap⟩: 0.998 with CI [9.973e-01, 9.982e-01]
  - Quantization claim: yes
- σ_phase = 0.100 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -3.602e-03 with CI [-3.900e-03, -3.303e-03] (width 5.968e-04)
  - ⟨s̄⟩: 0.802 with CI [7.331e-01, 8.700e-01]
  - ⟨overlap⟩: 0.993 with CI [9.916e-01, 9.937e-01]
  - Quantization claim: yes
- σ_phase = 0.200 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -2.743e-03 with CI [-3.215e-03, -2.271e-03] (width 9.439e-04)
  - ⟨s̄⟩: 0.619 with CI [5.082e-01, 7.289e-01]
  - ⟨overlap⟩: 0.977 with CI [9.756e-01, 9.780e-01]
  - Quantization claim: yes
- σ_phase = 0.350 (σ_amp=0.020, σ_tau=0.020)
  - R_γ mean: -2.063e-03 with CI [-2.360e-03, -1.765e-03] (width 5.947e-04)
  - ⟨s̄⟩: 0.484 with CI [4.127e-01, 5.553e-01]
  - ⟨overlap⟩: 0.940 with CI [9.381e-01, 9.421e-01]
  - Quantization claim: no (tracking robustness only)

When either threshold is violated we switch to the mixed-state fallback and report robustness trends only.
