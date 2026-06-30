---
name: openfoam-cht-convergence
description: Make a stiff OpenFOAM steady-state CHT (conjugate heat transfer) run with k-omega SST converge on a high-non-orthogonality snappyHexMesh, using non-orthogonal-correction schemes, strong under-relaxation, first-order warm-start, and flow-rate ramping (continuation). Use when an OpenFOAM multi-region run diverges (omega/continuity blow-up, p_rgh NaN), when dealing with non-orthogonal/skewed cells, or when setting up a robust steady CHT solve with foamMultiRun.
---

# Converge a stiff OpenFOAM CHT run (k-omega SST, snappy mesh)

The hard case: steady-state CHT, k-omega SST, narrow high-velocity inlet jets
(e.g. 0.1 mm slots at ~4.6 m/s), 70-75 deg non-orthogonal cells near walls/fins.
A cold start at full flow diverges (omega explodes first, then U, then
continuity, around iter ~30). The fix is a **continuation / warm-start**
strategy: never ask the solver to reach the hard solution from a blank field.

## Failure signature

- `omega` initial residual climbs monotonically, `nut` oscillates, then U and
  continuity blow up → stiff turbulent jets + 2nd-order overshoot.
- `p_rgh` GAMG NaN after a few iters → degenerate cells (determinant < 0.001)
  and/or too-aggressive pressure relaxation.

## The recipe (apply together)

### 1. Non-orthogonal correction (the #1 lever for skewed meshes)
In `system/<fluid>/fvSchemes` — cap the non-orthogonal correction so it cannot
overshoot on the 75 deg faces:
```
laplacianSchemes { default  Gauss linear limited 0.333; }
snGradSchemes    { default  limited 0.333; }
```
`corrected` (full correction) overshoots on those faces and blows up p_rgh.
`limited 0.333` keeps partial correction while staying stable. Negligible bias
on global results; refine toward `limited 0.5` / `corrected` later if wanted.

In `PIMPLE` (fvSolution): use more non-orthogonal correctors during the violent
transient, fewer once steady:
```
nNonOrthogonalCorrectors  3;   // transient on 75 deg cells; drop to 1 when steady
```

### 2. First-order convection during convergence
In `fvSchemes` — all convection `bounded Gauss upwind` (unconditionally bounded):
```
div(phi,U) bounded Gauss upwind;   div(phi,h) bounded Gauss upwind;
div(phi,k) bounded Gauss upwind;   div(phi,omega) bounded Gauss upwind;
```
2nd-order `linearUpwind` overshoots in the jet shear layers. Get a converged
1st-order field first, then **restart** with `linearUpwind` for accuracy.
Also limit gradients: `grad(U|h|k|omega) cellLimited Gauss linear 1`.

### 3. Strong under-relaxation (relax everything, incl. Final correctors)
In `fvSolution` `relaxationFactors` — conservative for the violent start:
```
fields    { "p_rgh.*"  0.3; }
equations { "U.*" 0.3;  "(k|omega).*" 0.3;  "(h|e).*" 0.7; }
```
Raise later once stable: U→0.5, p_rgh→0.5-0.7, h/e→0.9 (energy on a frozen
velocity field is a stable advection-diffusion solve; 0.9 speeds thermal
charge-up).

### 4. Divergence-free initialisation
Kill the huge initial continuity error with potentialFoam:
```
potentialFlow { nNonOrthogonalCorrectors 10; }
```

### 5. Flow-rate ramping (continuation) — the key idea
Because we impose flow rate (`flowRateInletVelocity`), the equivalent of the
classic "ramp the pressure" is to **ramp the flow rate**. Increase it in stages,
each stage **warm-started from the previous converged field**:
```
10% → 25% → 50% → 75% → 100%   of target flow rate
```
At each stage edit the inlet volumetric flow rate in `0/<fluid>/U`
(`flowRateInletVelocity`), restart from the latest time, let it converge, then
step up. Low flow = low Reynolds = gentle jets that converge easily; each step
builds on the last.

### 6. Laminar → k-omega warm-start (if turbulence still resists)
First converge with `simulationType laminar` (in `constant/<fluid>/momentumTransport`)
to get a clean, stable U/p/T field. Then switch back to `RAS` (k-omega SST),
**restarting from the laminar field**, and initialise k/omega consistently with
the converged velocity (the default low internal k/omega is a poor start).

## residualControl (stop criteria)
```
residualControl { U 1e-6;  h 1e-6;  "(k|omega)" 1e-4; }
```
Loose thresholds (1e-4 on U/h) can stop the run early at ~90% energy balance —
tighten U/h to 1e-6 for a truly converged thermal field.

## Safety
- `runTimeModifiable true` in controlDict → apply scheme/relaxation changes hot;
  if it NaNs on a hot change, revert immediately (keep a `fvSolution.*_bak`).
- After convergence, verify with the `openfoam-monitor-convergence` skill
  (residuals + energy balance Q_out/Q_in ≈ 100% + Tjmax drift).

## Recovering accuracy after the robust solve (optional)
From the converged 1st-order field, restart with: `div(phi,U) linearUpwindV`,
`nNonOrthogonalCorrectors 1`, relaxed factors raised. Near the solution this
usually stays stable and recovers 2nd-order accuracy. Measure the difference to
prove the robust settings did not bias the result.
