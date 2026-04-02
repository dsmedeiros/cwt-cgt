# CWT-CGT Next Steps After Step 2

Step 2 is complete: the project now has branch continuation, persistent branch IDs, and R4-aware loop exclusion.

## New baseline

The code can now:
- run mesh scans,
- run clockwise/counter-clockwise loop families,
- build branch-ID maps on the mesh,
- label ambiguous or disagreement regions as R4,
- continue branches along loop paths,
- exclude untrusted loops from signed-loop fits.

## Highest-priority next step

### Step 3 — Plotting and report generation

Add utilities that can automatically produce:
- persistent branch-ID maps,
- ambiguity / disagreement maps,
- regime maps,
- metric and curvature heatmaps,
- signed-loop response-vs-flux plots,
- benchmark summary markdown.

Deliverables:
- plotting module,
- report writer,
- saved PNG artifacts for A/B/C/D,
- one auto-filled benchmark report per benchmark.

## After that

1. Run the full acceptance pass for A/B/C/D.
2. Freeze the benchmark report set.
3. Move into the modal upgrade lane.
