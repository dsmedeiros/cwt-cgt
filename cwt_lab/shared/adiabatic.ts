export type AdiabaticSurfaceSample = {
  extent: number;
  steps: number;
  flux: number | null;
  area: number | null;
  kappa1: number | null;
  readout: number | null;
  fsMean: number | null;
  fsP95: number | null;
};

export type AdiabaticHistogram = {
  extent: number;
  steps: number;
  bins: number[];
};

export type AdiabaticBoundaryPoint = {
  extent: number;
  boundarySteps: number | null;
  referenceKappa: number | null;
  boundaryKappa: number | null;
  boundaryFsP95: number | null;
};

export type AdiabaticBoundaryRecommendation = {
  extent: number;
  steps: number;
  fsP95: number | null;
};

export type AdiabaticFsGuardSummary = {
  recommended: number | null;
  maxObserved: number | null;
};

export type AdiabaticBoundaryResult = {
  runId: string;
  outputDir: string;
  surface: AdiabaticSurfaceSample[];
  histograms: AdiabaticHistogram[];
  boundary: AdiabaticBoundaryPoint[];
  recommendation: AdiabaticBoundaryRecommendation | null;
  fsGuard: AdiabaticFsGuardSummary;
  referenceKappa: number | null;
};
