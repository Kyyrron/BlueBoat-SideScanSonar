# Sonar model

How the synthetic Omniscan 450 imagery is produced, what is modeled, what
is deliberately not, and which parameter controls what. Implementation:
`blueboat_sss/sonar/`.

## 1. Geometry

For each ping and each side, the transducer pose is derived from
`/blueboat/odom`: mount offset (`mount_x_m`, ±`mount_y_abs_m`) rotated by
yaw, transducer at `sensor_depth_m` below the surface. The renderer casts a
single athwartship ground line perpendicular to the heading (side sign:
port = +y in body frame), sampling the scene heightfield every
`sample_step_m` out to the configured slant range.

Per sample: slant range `R = √(y² + Δz²)`, depression angle
`δ = atan2(Δz, y)`, and local incidence angle from the along-line terrain
slope. Altitude is the water depth under the transducer; the water column
(`R <` altitude) stays empty except for additive noise, producing the nadir
gap.

## 2. Shadows — horizon culling

A sample is insonified iff its elevation angle (as seen from the
transducer) exceeds the running maximum over all nearer samples
(`np.maximum.accumulate`). This single mechanism produces geometrically
correct acoustic shadows behind proud objects, dune crests, and rocks — the
length of a shadow automatically obeys `L ≈ h·R / altitude`. The same
visibility array feeds the ground-truth contact annotations
(`visible` flag, `shadow_bins`).

## 3. Intensity model

Per insonified sample, echo power is the product of:

| Term | Formula | Config |
|---|---|---|
| Backscatter | `ρ · cos(θᵢ)^p` (Lambert-like) | material `reflectivity`, `lambert_exp` (material) or `lambert_exponent` (global) |
| Vertical beam pattern | Gaussian in depression angle, centered on `beam_tilt_deg` + roll toward that side, FWHM = `vertical_aperture_deg` | mounting section |
| Residual range response | `(10^(−α·2R/10) / R^(2k))^(1−c)` — two-way absorption `α` and spreading `k`, partially undone by TVG fraction `c` | `absorption_db_per_m`, `spreading_exponent`, `tvg_compensation` |

Samples are accumulated into the `num_results` slant-range bins with
`np.bincount` and normalized by per-bin hit counts, i.e. an unbiased mean
per bin — the discrete analogue of the intra-bin ensonified average.

`tvg_compensation = 1.0` reproduces a perfectly flattened image;
the default `0.90` leaves the gentle range falloff visible in the real
captures.

## 4. Surface-vehicle attitude coupling

Roll rotates the vertical beam pattern; a rolling USV therefore brightens
one side and dims the other ping-by-ping, producing the along-track
banding characteristic of surface platforms (a core concern of the thesis
regime). Pitch and heave enter through the odometry pose. There is no
intra-ping motion (§7, A5).

## 5. Noise model (`sonar/noise.py`)

Applied in order, all configurable:

1. **Speckle** — multiplicative `Exp(1)` on ensonified bins: fully
   developed speckle, the correct first-order statistic for incoherent
   sonar imagery (`speckle: true`).
2. **Water-column noise** — small additive floor inside the nadir gap
   (`watercolumn_noise`).
3. **Receiver noise floor** — additive everywhere (`noise_floor`).
4. **Gain drift** — slow multiplicative sinusoid + random walk
   (`gain_drift_amp`, `gain_drift_period_s`), emulating AGC/thermal drift
   → realistic long-period banding.
5. **Dropped pings** — Bernoulli per ping (`dropped_ping_prob`); the ping
   counter still advances, as with the real device, so downstream gap
   handling is exercised.

## 6. Quantization and encoding (`sonar/encoder.py`)

Float power → u16 `pwr_results` via
`base_scale · 10^((gain_index − 4)·gain_index_step_db/10)`, clipped to
65535, so the ROS `gain_index` parameter behaves like the real gain
ladder (`analog_gain` reported from the measured table, 74.55 at index 4).
`max/min_pwr_db = 10·log10(pwr) + calibration_db_offset` reproduces the
observed ~16 dB offset. Frames are byte-exact Ping Protocol
(`BR | len | 2198 | src | dst | 52-byte fixed payload | u16[n] | checksum`);
`parse_frame()` round-trips them and the smoke test verifies length parity
with the field capture (1262 B at n = 600).

Timing: free-run period = two-way travel time + 2 ms device processing
(observed 22 ms at 15 m); `msec_per_ping > 0` clamps to the commanded
period exactly like the hardware.

## 7. Assumptions (explicit)

* **A1 — straight rays.** No refraction; sound speed constant
  (`sos_dmps` 1500 m/s). Reasonable over ≤ 30 m in shallow well-mixed water.
* **A2 — single bounce, no multipath.** Surface/wall multipath — a known
  systematic of the enclosed-basin regime — is *not* modeled (roadmap §2).
* **A3 — no volume scattering / water absorption inhomogeneity.**
* **A4 — static scene.** No mid-run object motion, no vegetation sway.
* **A5 — stop-and-hop pings.** No intra-ping motion blur; inter-ping
  motion (attitude, advance) is fully modeled.
* **A6 — 2.5-D scene.** Heightfield world: no overhangs, objects
  represented as height + reflectivity stamps. Adequate for litter-scale
  targets; wrecks with cavities would need the mesh path (roadmap §3).
* **A7 — uncorrelated speckle.** No inter-ping speckle correlation.

## 8. Fidelity positioning

The model is a KTH-style (Bore & Folkesson) heightfield-draping renderer:
the accepted standard for generating *training-grade* SSS imagery when the
goal is detector development rather than acoustic research. Everything a
detector keys on — highlight/shadow geometry, nadir gap, speckle
statistics, texture by material, range falloff, attitude banding — is
present; everything it should not key on (renderer artifacts) is avoided
by the per-bin averaging and noise stack. The `SonarRenderer` ABC is the
seam for any higher-fidelity replacement.
