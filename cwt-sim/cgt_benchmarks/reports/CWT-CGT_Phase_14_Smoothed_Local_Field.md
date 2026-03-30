# CWT-CGT Phase 14 — Smoothed Local Mixed-State Field

## Goal

Replace the noisy lane’s discrete patch-family atlas with a smoother **local mixed-state field** over control space.

## Method

- Use the continuous-time Lindblad-style graph-local generator.
- Build minimal trusted plaquettes from the branch atlas.
- Compute CCW/CW response gaps and mixed-holonomy gaps on each plaquette.
- Form local χ = ΔR / ΔΦ_mix only after a holonomy floor.
- Robustly clip the raw local χ values.
- Smooth those values into a field using distance-weighted averaging over nearby plaquettes.
- Report sign consistency, effective support, and zero-crossing structure.

## Why this matters

This is more local and more generator-tied than the Phase 13 patch table. It tells us whether the noisy lane is only a few isolated patch fits or whether it really looks like a field over control space.
