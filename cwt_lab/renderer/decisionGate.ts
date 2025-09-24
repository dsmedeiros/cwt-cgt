export type PhaseIdentifier = 'phase1' | 'phase3' | 'phase4';

export type Phase1Metrics = {
  phase: 'phase1';
  omegaMaxAbs?: number | null;
};

export type Phase3Metrics = {
  phase: 'phase3';
  fsP95?: number | null;
  fsGuard?: number | null;
  phi?: number | null;
  calmHotspot?: boolean;
};

export type Phase4Metrics = {
  phase: 'phase4';
  advantage3d?: number | null;
  overlap?: number | null;
};

export type DecisionMetrics = Phase1Metrics | Phase3Metrics | Phase4Metrics;

const TIP_PHASE1_LOW_OMEGA =
  'Map shows barely any |Ω| structure. Increase asymmetry (try sw/sf, widen ranges) and re-map before iterating.';
const TIP_PHASE3_GUARD =
  'Flux spikes keep breaching the guard. Switch to Guided Mode or tweak the loop center / axes before retrying.';
const TIP_PHASE3_EXTEND =
  'Loops look calm with Φ ≈ 0. Push the extents outward on the mellow tiles to explore more energetic regions.';
const TIP_PHASE4_DIMENSION =
  '3D sweep is matching your 2D baseline. Shift effort to 2D optimisation until a clear 3D edge appears.';

class DecisionGateEngine {
  private phase3GuardBreaches = 0;

  evaluate(metrics: DecisionMetrics): string | null {
    switch (metrics.phase) {
      case 'phase1':
        return this.evaluatePhase1(metrics);
      case 'phase3':
        return this.evaluatePhase3(metrics);
      case 'phase4':
        return this.evaluatePhase4(metrics);
      default:
        return null;
    }
  }

  private evaluatePhase1(metrics: Phase1Metrics): string | null {
    if (metrics.omegaMaxAbs != null && Math.abs(metrics.omegaMaxAbs) < 1e-5) {
      return TIP_PHASE1_LOW_OMEGA;
    }
    return null;
  }

  private evaluatePhase3(metrics: Phase3Metrics): string | null {
    const { fsP95, fsGuard, phi, calmHotspot } = metrics;
    if (fsP95 != null && fsGuard != null) {
      if (fsP95 > fsGuard) {
        this.phase3GuardBreaches += 1;
        if (this.phase3GuardBreaches >= 2) {
          return TIP_PHASE3_GUARD;
        }
      } else {
        this.phase3GuardBreaches = 0;
      }
    }

    if (fsP95 != null && fsGuard != null && fsP95 <= fsGuard && phi != null) {
      if (Math.abs(phi) < 0.02) {
        return calmHotspot ? TIP_PHASE3_EXTEND : null;
      }
    }

    return null;
  }

  private evaluatePhase4(metrics: Phase4Metrics): string | null {
    if (metrics.advantage3d != null && Math.abs(metrics.advantage3d) < 5) {
      return TIP_PHASE4_DIMENSION;
    }
    if (metrics.overlap != null && metrics.overlap < 0.35) {
      return TIP_PHASE4_DIMENSION;
    }
    return null;
  }
}

export const createDecisionGateEngine = () => new DecisionGateEngine();
