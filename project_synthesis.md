# Project Synthesis
## Autonomous Aspect-Aware Side-Scan Sonar Survey on a Small USV

*Master thesis working document. Written for AI agents and collaborators who need full
context to work on any part of the project.*

---

## 0. How to use this document

This is the single source of truth for project scope, claims, architecture, and constraints.
An agent asked to work on any component should read §1–§4 for orientation, then the section
covering its component, then §8 (design rules) before writing code or planning experiments.

**Non-negotiables** are marked ⚠. Violating them breaks the scientific argument, not just
the implementation.

---

## 1. Project identity

**One sentence.** Autonomous aspect-aware replanning for shallow-water side-scan sonar
survey on a small unmanned surface vehicle, evaluated against fixed-pattern coverage in a
calibrated simulation environment and demonstrated in real water at reduced scale.

**Platform.**
- BlueRobotics BlueBoat (small catamaran USV)
- Cerulean Omniscan 450 SS side-scan sonar — 450 kHz, 0.5° azimuth beam, 1/1200 range
  resolution, 50° vertical aperture, 20 Hz max ping rate
- Water Linked USBL (pinger + receiver) — ground-truth instrumentation
- ArduPilot / ArduRover autopilot, ROS 2 middleware
- All computation on the basestation (operator laptop). No on-board compute constraint.
  Constraint is wireless link bandwidth and latency.

**Test environments.**
- Enclosed beach, wall-bounded, shallow (~1–3 m), accessible on demand. Primary real-water
  site.
- Harbour recordings from a prior campaign (July). Used for simulator world reconstruction
  and appearance calibration only.

---

## 2. Scientific spine

Every design decision in this project traces back to the following argument. An agent
should be able to justify any component by pointing at a step in this chain.

1. **A surface vehicle cannot choose its sonar altitude.** Altitude is fixed by water depth.
   An AUV flies low and controls this parameter; a USV cannot.
2. **Fixed high altitude starves shadows.** Shadow length scales as object height × ground
   range ÷ altitude. For realistic small targets in shallow water, shadows are weak or
   absent.
3. **Detection therefore falls back on the specular highlight,** which is strongly
   aspect-dependent. Target strength of structured objects fluctuates by ~20 dB over less
   than 10° of aspect.
4. **Single-pass coverage is therefore structurally incomplete.** Targets physically present
   are missed because they were viewed from an uninformative heading.
5. **Multi-aspect revisit is a detection requirement, not an efficiency optimisation.**
6. **Deciding which contacts to revisit, and from which heading, is a judgment humans make
   poorly in real time.** Standard practice is exhaustive manual reacquisition, costing
   30+ minutes per contact.
7. **Automating that decision is the contribution.**

⚠ The thesis is an *investigation*, not advocacy. The protocol gives a fair chance to the
baseline. A finding that adaptive replanning does not beat two-pass orthogonal coverage is
a publishable result and the framing must survive it.

---

## 3. Operating scope

### 3.1 What the system targets

Objects **≥ 0.5 m in at least one horizontal dimension, with vertical relief**. This is
consistent with IHO S-44 Special Order feature detection (cubic features > 1.0 m) for
harbours, berthing areas, and critical fairways.

Operational framing: **harbour and inland-waterway obstruction and debris survey.**
Applications include illegal discharge outfalls, dumped waste, navigation obstructions,
sunken small craft, lost cargo, mooring hardware.

### 3.2 What is explicitly out of scope

⚠ These must be stated as out of scope in any writing, not quietly omitted.

- **Centimetre-scale marine debris** (bottles, cans, packaging). A 450 kHz SSS cannot
  resolve these. This is a sensor limit, not an engineering gap.
- **UXO detection.** Standard test ordnance (60/81 mm mortars, 105/155 mm projectiles) is
  below the detection floor. Real UXO survey uses magnetometers; SSS provides supporting
  imagery only.
- State-of-the-art detection accuracy. The detector supports the study; it does not compete
  with dedicated MCM systems.
- Novel coverage path planning.
- Novel SLAM or bottom-tracking algorithms.
- Deep-water or open-ocean operation.

### 3.3 Environments and expected targets

| Environment | Depth | Realistic targets | Size |
|---|---|---|---|
| Marina / small-craft harbour | 2–6 m | Mooring blocks, tyres, lost outboards, trolleys, dropped tools | 0.3–3 m |
| Commercial port basin | 7–15 m | Lost cargo, pallets, cables, pipes, construction debris, anchors | 0.5–6 m |
| Enclosed beach (test site) | 0.5–5 m | Controlled targets representing the above classes | 0.3–2 m |
| Urban river / canal | 2–10 m | Discharge pipes, sunken vessels, dumped waste, debris | 0.5–5 m |

⚠ At the beach, targets are **controlled objects representative of harbour debris classes**.
Never write "simulated pollution" — it invites a representativeness question with no strong
answer.

---

## 4. Evidence architecture

⚠ This is the most important table in the document. Each layer supports exactly one claim.
No layer may be used to support a claim above its evidential weight.

| # | Layer | Evidence source | What it supports | What it does NOT support |
|---|---|---|---|---|
| E1 | World geometry and appearance | July harbour recordings: per-range intensity distributions, speckle character, noise floor, seabed texture appearance, reconstructed world geometry, ground-truth depth file | The simulator produces plausible imagery in a real geometry | Anything about detection probability, target strength, or absolute backscatter |
| E2 | Detector | Trained on real beach imagery | A working detector exists; its performance is measured | Generalisation beyond the beach site |
| E3 | Aspect-response check | Beach: 4–5 objects × 8–12 systematic headings at fixed range | The mechanism the thesis rests on behaves as claimed | Quantitative aspect-window widths across a class space |
| E4 | Policy comparison | Gazebo, full pipeline, tens of runs | **The headline result** — adaptive vs two-pass | An unqualified empirical finding; it is model-conditional |
| E5 | Parameter sweeps *(optional)* | Surrogate fitted from E4 Gazebo runs | Boundary conditions, oracle ablation | Anything Gazebo itself did not produce |
| E6 | Real-water demonstration | Beach closed-loop run | The system executes end-to-end outside simulation | Statistical significance |
| E7 | Sim-to-real detector gap | Train on synthetic, test on beach | Side result: quantified transfer gap | The main comparison |

### 4.1 Headline claim phrasing

⚠ Use this form. Do not state the result as an unqualified empirical finding.

> *In a calibrated simulation environment, adaptive aspect-aware replanning recovers X% of
> targets that two-pass orthogonal coverage misses. The result holds across sweeps of
> detector quality, clutter density, and aspect-window width. A real-water demonstration
> confirms the system executes as modelled.*

### 4.2 What July data can and cannot give

**Can:** per-range intensity distributions, speckle distribution shape on homogeneous
patches, noise floor, visual texture of distinguishable seabed types, qualitative multipath
signature near walls, world geometry (with the separate ground-truth depth file), boat
trajectory and speed for 5–6 passes with differing motion.

**Cannot:** absolute backscatter strength, target strength, detection probability, or any
labelled target measurement.

⚠ July validates simulator *appearance and geometry*. It says nothing about detection.

---

## 5. System architecture

### 5.1 Component map

```
BOAT (BlueBoat)
├── Cerulean Omniscan 450 SS ──────► raw pings
├── GPS / IMU / heading ───────────► USV pose
├── Water Linked USBL receiver ────► pinger position
└── ArduPilot ◄──────────────────── waypoint missions (MAVLink)

BASESTATION (laptop)
├── SSS preprocessing ── slant-range correction, FBR altitude, geocoding, normalization
├── Waterfall buffer ─── rolling boat-relative image, fixed-size patch extraction
├── Detector ─────────── classical proposer + CNN classifier
├── Belief layer ─────── multi-channel Bayesian grid          ◄── THE INTERFACE
├── Initial CPP ──────── swath-aware boustrophedon
├── Replanner ────────── aspect-aware revisit decisions
└── Mission manager ──── MAVLink mission swap
```

⚠ The **belief layer is the only object the replanner reads.** Detector changes, sensor
changes, and planner changes interact only through it. Preserve this boundary.

### 5.2 Data structures

**SSS ping (custom ROS 2 message).** No standard type exists for side-scan.
```
std_msgs/Header header
float32 sound_speed
float32 range_max
uint32  num_samples
uint8[] port_intensities
uint8[] starboard_intensities
float32 ping_period
```
A single ping has no spatial position. It is a 1-D time series along a slant-range axis
perpendicular to the boat heading at acquisition.

**Ping → world coordinates, three steps.**
1. Slant-range correction: `r_ground = sqrt(r_slant² − h²)`, h = transducer altitude
   (from FBR).
2. Place in world frame using USV pose at ping time. Port sample at ground range r →
   `(x − r·sin ψ, y + r·cos ψ)`; starboard → `(x + r·sin ψ, y − r·cos ψ)`.
3. Accumulate into a world-frame raster for mosaicking.

TF tree: `map → odom → base_link → sss_link`. Lever-arm offsets matter.

**Detector input — rolling waterfall buffer.**
⚠ The detector consumes a **boat-relative** rolling waterfall (rows = pings, columns =
ground-range bins), not a world-frame mosaic. World-frame patches distort near turns and
introduce intensity-aggregation ambiguity when cells are revisited. Run detection on
overlapping fixed-size patches (e.g. 512×512, 50% overlap) every N pings, targeting ~1–2 Hz.

Mapping a detection back to world coordinates: row → ping index → USV pose; column →
ground range and side.

**Detector output.**
```
(world_x, world_y)     geocoded centre
covariance_xy          localisation uncertainty
class_label
confidence             calibrated, in [0,1]
ping_idx               traceability
detection_id
```

**Belief grid — multi-channel, world frame.**
```
per cell:
  p_target         float   P(target | observations)
  n_observations   int     times this cell was sonified
  aspect_coverage  bitmap  headings this cell has been viewed from
  last_intensity   float
  max_confidence   float
```
Visualise `p_target` as `nav_msgs/OccupancyGrid` for free RViz support. Negative
observations (cell sonified, nothing detected) must also update the posterior — that is what
`n_observations` and `aspect_coverage` are for.

**Replanner inputs.**
- Candidate list: cells with `p_target > τ_high`
- Coverage deficit: cells with `n_observations < n_min` or narrow `aspect_coverage`

### 5.3 Output artifacts

| Artifact | Purpose | Generation |
|---|---|---|
| Acoustic mosaic | Geocoded SSS imagery, no overlay | On demand / post-mission |
| Belief grid | Machine-readable P(target) heatmap | Live |
| Annotated mosaic | Mosaic + detection boxes | Post-mission, for figures |

⚠ Do not generate the world-frame mosaic continuously. It is wasteful and off the critical
path. The waterfall buffer is what the detector needs.

---

## 6. Simulation

Two tiers with distinct jobs. ⚠ Neither substitutes for the other.

### 6.1 Tier 1 — Gazebo + acoustic model (primary)

Existing package `blueboat_sss`. Procedural shallow-water world generation (seabed types,
bathymetry, configurable litter classes with position, orientation, burial, material,
reflectivity), physically motivated Omniscan 450 acoustic model, **byte-identical drop-in
ROS interface** so the perception, planning and logging stacks run unmodified across sim and
real water, YOLO dataset export.

Calibrated against July recordings on appearance: per-range intensity histograms, speckle
statistics, noise floor.

Throughput: tens of runs. Sufficient for the headline policy comparison — ~20 runs × ~10
objects gives ~200 detection opportunities per condition, enough to detect a large effect.

### 6.2 Tier 2 — Policy surrogate (optional, stretch goal)

A fast non-rendering loop: grid map with objects, boat steps cell to cell, visibility
condition triggers a probability draw, tally detections, report.

⚠ **The probability function must be fitted from Tier-1 Gazebo runs, never invented.**
Procedure: run Gazebo across a controlled grid of `class × range × aspect × seabed`, log
outcomes, fit `P(detect | class, range, aspect, seabed)` to those results. The surrogate is
then a *compressed surrogate of the Gazebo pipeline*, not an independent world model.

Validation: hold out configurations, check the surrogate reproduces Gazebo on them. This
gives a concrete pass/fail criterion and makes the component debuggable.

**Build only if the parameter sweeps (§7.4) are wanted.** Dropping it leaves the thesis
simpler and equally defensible, with sweeps as future work.

### 6.3 Simulator validation

Validate on what the thesis claims, not on general image similarity.

| Check | Tests | Priority |
|---|---|---|
| Per-range intensity histograms, speckle statistics | Appearance realism | Necessary, not sufficient |
| World geometry reconstruction vs July recordings along the same trajectory | Geometric fidelity | High |
| Shadow contrast vs object height and altitude | The shadow-starvation model | High |
| Detection-relevant aspect response vs beach measurements (§7.2) | **The load-bearing check** | Critical |
| Tier-1 vs Tier-2 agreement on held-out configurations | Surrogate validity | Only if Tier 2 built |

⚠ If the aspect-response check fails, the simulator cannot support the headline claim
regardless of how good the appearance checks look. Test this early — it is the go/no-go.

### 6.4 External simulators

ACOUSIM, S3Simulator, STARS, HoloOcean/OceanSim: **cite as related work, do not adopt.**
Adapting to another group's interfaces and assumptions is the wrong use of the timeline.

Differentiators to state explicitly: device calibration to a specific low-cost widely
deployed sensor, and closed-loop *policy* evaluation rather than static dataset generation.

Optional nice-to-have if their data is public: train a detector on external synthetic
imagery, test on beach data, report a cross-simulator generalisation figure. Not a plan item.

---

## 7. Experiments

### 7.1 Beach dataset campaign

Purpose: produce E2 (the detector).

Object classes — all above the 0.5 m detection floor, each a proxy for a real target class:

| Class | Proxy | Size | Stands for |
|---|---|---|---|
| A | Stacked cinder blocks / weighted crate | ~0.5 × 0.5 × 0.4 m | Anchor, engine block, concrete debris |
| B | Sand-filled capped PVC pipe | Ø 0.2 m × 1.2 m | Pipe section, cable spool, mooring hardware |
| C | Weighted wire cage or crate | ~0.6 × 0.6 × 0.5 m | Crab pot, trolley, debris cluster |
| D | Car tyre, weighted | Ø 0.65 m | Common real harbour object, distinctive signature |
| E | Flat steel plate | ~0.8 × 0.8 × 0.02 m | **Deliberate low-detectability control** |

⚠ Class E is expected to fail. Its invisibility is a result that locates the detectability
floor empirically, not a gap.

Deploy all classes ≥ 5 m apart. RTK-mark each position at drop. USBL pinger on one object;
rotate across sessions.

### 7.2 Aspect-response experiment ⚠ SCIENTIFIC KEYSTONE

Purpose: produce E3. This is the **only** place where the mechanism the entire thesis rests
on is tested against reality.

Protocol: 4–5 objects, each imaged from **8–12 systematically varied headings at fixed
ground range**, repeated.

Question: does measured visibility vary with heading in the way the model predicts?

⚠ Treat this as more important than dataset volume. Design it deliberately — systematic
headings, controlled range, repeated passes. Run it early enough that a negative outcome is
actionable.

Feeds directly into simulator validation (§6.3) and into the replanner's aspect-selection
rule (§8.3).

### 7.3 Policy comparison

Purpose: produce E4 (headline result).

⚠ **Baseline is two-pass orthogonal, not single-pass.** Single-pass is a strawman; nobody
surveys that way when it matters. Beating single-pass but not two-pass shows nothing.

Condition ladder:
1. Single-pass boustrophedon *(reference only)*
2. **Two-pass orthogonal — the baseline that matters**
3. Adaptive, append-on-completion replanner
4. Adaptive, aspect-aware informative replanner

Run in Gazebo across randomised scenes (object placement, seabed type, clutter density).

### 7.4 Parameter sweeps *(optional, Tier 2)*

Two noted items:

**Oracle-detector ablation.** Run the policy comparison three ways — fitted detection model,
degraded model (~20% worse), perfect oracle. Separates "does the replanner logic work" from
"does the detector work". Nearly free in Tier 2.

**Where adaptivity stops paying.** Sweep clutter density × target density × detector quality
× aspect-window width, and locate the boundary where adaptive replanning stops beating
two-pass orthogonal. ⚠ This boundary is likely the most durable result in the thesis — more
citable than a single "we win by X%" number.

### 7.5 Real-water closed-loop demonstration

Purpose: produce E6. Full stack running at the beach: live detection, live belief update,
live replanning, live mission swap. Feasibility proof, not a statistical result.

### 7.6 Sim-to-real detector gap

Purpose: produce E7. Train a detector purely on synthetic imagery, test on beach data,
report the transfer gap. One experiment, one figure, one section.

⚠ The *primary* detector trains on real beach imagery. Never train the headline detector on
synthetic data — that inherits aspect sensitivity from the model rather than measuring it.

---

## 8. Design rules

### 8.1 Replanner requirements ⚠

An unbounded "revisit hard areas" rule is not an algorithm — an ambiguous patch keeps
looking ambiguous, the replanner keeps returning, the survey never terminates. Three rules
must be explicit and principled:

- **Resolution criterion.** When is a contact done? Confidence above threshold, or N aspects
  acquired, or confidence stopped improving between successive looks.
- **Budget allocation.** What fraction of mission time may go to revisits vs completing
  coverage? This is the exploration/exploitation trade-off and where the interesting
  decision lives.
- **Abandonment rule.** When to give up on a non-converging contact. Without this, one
  pathological patch consumes the mission.

These three rules *are* the replanner's scientific content. Everything else is plumbing.

### 8.2 Confidence calibration ⚠

Neural network confidence outputs are systematically miscalibrated — a detector reporting
0.8 is often right well below 80% of the time. Feeding raw softmax into a Bayesian belief
grid makes the grid quantitatively meaningless.

Budget time for temperature scaling and reliability diagrams. Cheap, and almost no applied
work in this space bothers.

### 8.3 Aspect-selection rule

"Perpendicular to last time" is a heuristic anyone could write. Deriving the rule from the
measured aspect response (§7.2) — pick the heading maximising expected confidence gain given
the empirical model — couples the measurement and the planner so that neither is arbitrary.

This coupling is what separates a distinctive thesis from a competent one.

### 8.4 Metrics

**Headline:** targets recovered by adaptive revisit that two-pass coverage missed.

⚠ Prefer continuous metrics over binary detection rate. Binary rate has poor statistical
power at achievable sample sizes. Continuous alternatives:
- Aspect-unique detection rate (targets found only after a complementary aspect)
- Detection confidence as a function of number of looks acquired
- Localisation error per detection (USBL ground truth)
- Number of distinct aspects acquired per target
- Time to reach N confirmations

**Mission-level metrics** (what end users care about; distinguishes this from pure
detection-accuracy work):

| Metric | Measures |
|---|---|
| Mean time-to-confirmation per contact | First detection → confirmation |
| False positives per hectare | FP rate normalised by area |
| Detection probability by class and range | P(detect \| class, R, aspect) |
| Repositioning precision for revisit | Intended vs achieved revisit geometry |
| Energy cost per validated object | Battery / distance / time per confirmed target |

### 8.5 Reserved settings

| Setting | Value | Note |
|---|---|---|
| Range setting, coverage pass | 30 m per side | Wide swath, range diversity in training data |
| Range setting, revisit pass | 15 m per side | Denser along-track sampling on candidates |
| Boat speed | 1.0 m/s nominal | Denser sampling than reducing range, without halving swath |
| Line spacing | ~0.8 × usable swath | Verify against measured swath, not the setting |
| Target ground range for training data | 5–20 m | Below: nadir gap. Above: along-track resolution limits |

⚠ Range setting does **not** change resolution at a given ground range — resolution is set by
beam geometry (`Δ_along = R · θ`) and pulse length. Reducing range increases ping rate and
along-track sampling density, and halves swath.

### 8.6 Operational rules

- ⚠ AI iteration happens **offline against recorded rosbags**, never in the water. Needing a
  field session to test an AI change means the replay tooling has a gap.
- ⚠ The two-pass baseline must be tuned seriously. Deliberately weakened baselines are
  detected instantly and sink the comparison.
- Paired same-day comparisons wherever possible, to control environmental variability.
- Log tide, weather, water clarity, sea state per run.
- The USBL pinger is first-class instrumentation, integrated from the start.

---

## 9. Deliverables

| # | Deliverable | Status |
|---|---|---|
| D1 | SSS data pipeline — slant-range correction, FBR altitude, geocoding, waterfall buffer | **Built**, field-validated |
| D2 | Beach test-object dataset — labelled, augmented, openly released | Not started ⚠ bottleneck |
| D3 | Detection module — classical proposer + CNN classifier | Blocked on D2 |
| D4 | Belief layer — multi-channel Bayesian grid | Designed, not implemented |
| D5 | Mission interface — path following, clean mid-mission swap | **Built** (base), swap logic pending |
| D6 | Adaptive replanner — two variants | Not started |
| D7 | Evaluation framework — conditions, metrics, campaigns | Not started |
| D8 | Thesis manuscript | Ongoing |
| S1 | `blueboat_sss` simulator package | **Built**, calibration ongoing |
| S2 | Policy surrogate | Optional stretch goal |

**Also built:** Mission Control Station (PySide6 — mission launching, emergency stop, node
monitoring), GCS visualisation app (live mosaic over satellite tiles, USBL and detection
overlays, session recording), BlueBoat base control (MPC / PID / LoS, MAVROS, Gazebo mode).

⚠ D2 is the critical-path bottleneck. It does not parallelise with anything else and gates
D3, which gates every downstream result.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| **Detector quality gates everything.** Poor detector → noisy belief map → replanner chases false positives. | Start D2 first. Classical proposer as fallback. Oracle ablation isolates the effect. |
| Aspect-response check (§7.2) fails | Run early. A negative result reframes but does not kill the thesis — it becomes a regime-characterisation finding. |
| Single-site data caps generalisation | State plainly in limitations. Do not overreach elsewhere. |
| Headline result is simulation-derived | Phrase as model-conditional throughout (§4.1). Lead the limitations chapter with it. |
| Aspect-window widths not measurable at scale | Sensitivity sweep; report the range over which conclusions flip, including if they flip inside the plausible range. |
| Mid-mission MAVLink swap corner cases | Exhaustive SITL testing. Fallback: replan only between missions. |
| Weather / schedule slip on field campaigns | Tier-1 simulation is a defensible fallback for the evaluation, given calibration is in place. |

---

## 11. Positioning

**Not novel:** adaptive SSS surveying (Paull 2010, 2013 — AUVs); state-of-the-art adaptive
replanning (Sethuraman, Baldoni, Skinner, McMahon 2024 — AUV, simulation-only); USV-based
SSS in shallow coastal water (Cocchi et al. 2024, CORAL — 450 kHz catamaran USV, Italian
harbours); information-gain replanning (Hollinger & Sukhatme 2014; Krause/Guestrin);
aspect-dependent target strength (classical sonar physics); Gazebo SSS simulation (ACOUSIM
2026, S3Simulator 2024).

**Novel — the specific intersection:**
1. Characterisation of the shadow-starved, aspect-critical regime a surface platform
   necessarily operates in.
2. Closed-loop replanning driven by target detection **and aspect coverage deficit**, not
   terrain complexity.
3. On a research-accessible USV, 1–2 orders of magnitude cheaper than industrial systems.
4. Closed-loop *policy* evaluation in simulation, not static dataset generation.
5. Device calibration to a specific low-cost widely deployed sensor.
6. Open release of platform stack, simulator, dataset, and methodology.

**Closest precedents.** CORAL is the platform precedent — analogous hardware, same regime,
but a capability demonstrator with no automated detection, no closed loop, no baseline
comparison, no open release. Sethuraman et al. 2024 is the conceptual precedent —
multi-view informed active perception with SSS, next-best-view selection, but AUV-based and
evaluated only in photorealistic simulation. Positioning as the surface-platform,
real-water-demonstrated counterpart is stronger than positioning as a cheaper
re-implementation.

---

## 12. Publication

**UT27, Tokyo** (IEEE OES Japan Chapter). Student Paper Competition — student must be lead
and corresponding author; selected students receive registration waiver and partial travel
reimbursement; full paper still goes to IEEE Xplore. Abstracts not selected for SPC are
still considered for the regular programme, so submitting to SPC is strictly dominant.
A JOE special issue provides an extension path. TPC co-chair is at Kyutech (Kitakyushu) —
domestic travel.

Candidate paper: the regime characterisation plus closed-loop policy evaluation, with the
calibrated simulator as supporting methodology.

---

## 13. Key references

**Adaptive sonar surveying.** Paull, Saeedi, Li & Myers (2010), IEEE CASE. Paull, Saeedi,
Seto & Li (2013), IEEE/ASME TMech 18. Sethuraman, Baldoni, Skinner & McMahon (2024),
*Learning Which Side to Scan*, ICRA / arXiv 2402.01106. Hollinger & Sukhatme (2014), IJRR
33(9).

**Platform / regime precedent.** Cocchi, Muccini, Locritani, Spinelli & Cocco (2024),
*CORAL*, Sensors 24(14), 4544, DOI 10.3390/s24144544.

**USV shallow-water sonar.** Greene et al. (2018), Estuarine, Coastal and Shelf Science 207.
Kaeser & Litts (2010 ff.). Specht, Specht et al., Sensors 23(8).

**Reviews.** Qiao et al. (2026), JMSE 14(2), 145, DOI 10.3390/jmse14020145. Song et al.
(2026), Discover AI.

**Detection.** Williams (CMRE). Petillot (Heriot-Watt). Burguera & Oliver. Sethuraman,
Sheppard, Bhandari et al. (2024), IJRR — Thunder Bay open dataset. Wei et al. (2024), Sci
Rep — domain-adaptive. Zeng et al. (2026), Ocean Engineering.

**Preprocessing.** Al-Rawi et al. (2017) — FBR detection. Lei et al. (2026), arXiv
2604.19901 — attitude-refinement geometric correction, directly relevant to surface motion.
Zhang et al. (2024), Frontiers in Marine Science — mosaicking. Bore & Folkesson — KTH neural
SSS. `auvlib` (KTH).

**USBL ground truth.** Mandić, Mišković, Bibuli et al. (2016), J. Sensors 2016 — closest
methodological precedent, but AUV tracking-filter evaluation with forward-looking sonar.
Kinsey, Eustice & Whitcomb (2006).

**Simulators.** ACOUSIM (2026, arXiv 2605.19712). S3Simulator (ICPR 2024). STARS (arXiv
2310.01667). Bore & Folkesson MC-pix2pix.

**Standards and foundations.** IHO S-44 (Special Order: cubic features > 1.0 m; Order 1a:
> 2.0 m to 40 m depth). NOAA (2024) Standard Ocean Mapping Procedures. Galceran & Carreras
(2013), RAS 61(12). Fossen, *Handbook of Marine Craft Hydrodynamics and Motion Control*.
Krause, Singh & Guestrin (2008), JMLR.

**Project repositories.** BlueBoat ROS stack: https://github.com/Amarsmer/BlueBoat — SSS
integration: https://github.com/Kyyrron/BlueBoat-SideScanSonar

---

## 14. Quick reference for agents

**Working on the detector?** §5.2 (waterfall buffer, boat-relative ⚠), §7.1 (classes),
§8.2 (calibration ⚠), §8.4 (metrics). Train on real beach imagery only.

**Working on the belief layer?** §5.2 (multi-channel grid), §8.1 (what the replanner needs),
negative observations must update the posterior.

**Working on the replanner?** §8.1 (three required rules ⚠), §8.3 (aspect rule), §7.3
(baseline is two-pass orthogonal ⚠).

**Working on the simulator?** §6 (two tiers), §6.3 (validate aspect response — go/no-go ⚠),
§4.2 (what July can and cannot support ⚠).

**Planning experiments?** §7.2 is the keystone ⚠. §7.1 is the bottleneck. §8.6 (operational
rules).

**Writing?** §4.1 (headline phrasing ⚠), §3.2 (state out-of-scope explicitly ⚠), §11
(positioning), §10 (lead limitations with the model-conditional caveat).
