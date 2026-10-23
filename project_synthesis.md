# Project Synthesis
## Autonomous Aspect-Aware Side-Scan Sonar Survey on a Small USV

*Master thesis working document. Written for AI agents and collaborators who need full
context to work on any part of the project.*

> **Revision note — 2026-10-20.** Brought in line with the owner's decisions of this date and
> with the code as found on this machine. What changed:
> 1. **Schedule.** The publication plan (old §12) is removed; §12 is now the thesis schedule
>    (submission early January 2027). No venue is planned in this document.
> 2. **Scientific goal unchanged.** Research questions and the headline claim (§4.1) stand: a
>    model-conditional simulated comparison of adaptive heading-aware replanning against a
>    seriously tuned two-pass orthogonal survey.
> 3. **Detector (§4 E2/E7, §5.2, §7.1, §7.6, §8.2, §9 D2/D3, §10, §14).** A YOLO model in
>    BlueBoat-Perception, trained on simulated datasets made by Perception's dataset mode,
>    with its confidence calibrated on held-out simulated worlds. Real water validates the
>    simulator, runs the heading-response experiment, checks simulator-to-real conclusions
>    later, and serves the final demonstration; a labelled real dataset is not on the critical
>    path and blocks nothing. The "trained on real beach imagery only" rule, the beach dataset
>    deliverable and the "classical proposer + CNN on 512 × 512 patches" description are
>    replaced; §5.2 now describes the detector input as the code implements it.
> 4. **Module chain (§5.1).** sonar module → Perception → Belief → Replanner → Control. Belief,
>    Replanner and Evaluation are planned, not built; Perception and the link guardian are
>    existing modules; the Aug Studio is optional.
> 5. **"MAVLink mission swap" (§5.1, §7.5, §9 D5, §10)** replaced by Control's live path update
>    (`/blueboat/update_path` and the progress / event topics): built, tested in Gazebo only,
>    not on water, no client yet.
> 6. **Sonar range (§8.5):** 20 m per side for every survey condition; the 30 m / 15 m passes
>    are gone.
> 7. **Add-only rule (§0):** Control and the Mission Control Station change by additions only.
> 8. **Deliverables (§9)** re-stated with their real status.
>
> Superseded by this revision: the dated reviews (`project_review.md`, `sim_review.md`) and
> `literature_conclusions.md` where they plan a real-imagery detector, 30 m / 15 m passes or a
> publication; each carries a header line saying so.

---

## 0. How to use this document

This is the single source of truth for project scope, claims, architecture, and constraints.
An agent asked to work on any component should read §1–§4 for orientation, then the section
covering its component, then §8 (design rules) before writing code or planning experiments.

**Non-negotiables** are marked ⚠. Violating them breaks the scientific argument, not just
the implementation.

**Add-only rule.** BlueBoat-Control and BlueBoat-MCS are updated by additions only: a new
topic, service, parameter, launch argument or UI element is fine; nothing proven is renamed,
retyped or changed in behaviour unless the behaviour stays identical (and is shown to). New
modules (Belief, Replanner, Evaluation) may own their own interfaces package; no existing topic
is ever renamed or retyped.

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
- All computation on the operator laptop, linked to the boat through the BlueBoat Base
  Station WiFi; the boat carries only its hardware and firmware. No on-board compute
  constraint. Constraint is wireless link bandwidth and latency.

**Test environments.**
- Enclosed beach, wall-bounded, shallow (~1–3 m), accessible on demand. Primary real-water
  site. Real water has four jobs: validate the simulator (boat motion and sensor), run the
  heading-response experiment (§7.2), check simulator-to-real conclusions later (§7.6), and
  host the final demonstration (§7.5). It does not produce the detector's training data.
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
| E2 | Detector | YOLO model in BlueBoat-Perception, trained on simulated datasets from Perception's dataset mode; confidence calibrated on held-out simulated worlds | A working detector exists; its performance and calibration are measured **in simulation** | Detection performance in real water; generalisation beyond the simulated worlds |
| E3 | Aspect-response check | Beach: 4–5 objects × 8–12 systematic headings at fixed range. Also validates the simulator's boat motion and sensor | The mechanism the thesis rests on behaves as claimed; the simulator is a fair stand-in | Quantitative aspect-window widths across a class space |
| E4 | Policy comparison | Gazebo, full pipeline, tens of runs | **The headline result** — adaptive heading-aware replanning vs a seriously tuned two-pass orthogonal survey | An unqualified empirical finding; it is model-conditional |
| E5 | Parameter sweeps *(optional)* | Surrogate fitted from E4 Gazebo runs | Boundary conditions, oracle ablation | Anything Gazebo itself did not produce |
| E6 | Real-water demonstration | Beach closed-loop run (live path update) | The system executes end-to-end outside simulation | Statistical significance |
| E7 | Simulator-to-real check *(optional, later)* | The simulation-trained detector and the policy conclusions run against real beach data, if and when a field day allows | Side result: how far the simulated conclusions carry over | The main comparison; nothing else waits on it |

### 4.1 Headline claim phrasing

⚠ Use this form. Do not state the result as an unqualified empirical finding.

> *In a calibrated simulation environment, adaptive aspect-aware replanning recovers X% of
> targets that two-pass orthogonal coverage misses. The result holds across sweeps of
> detector quality, clutter density, and aspect-window width. A real-water demonstration
> confirms the system executes as modelled.*

⚠ Because the detector is trained on simulated imagery (E2), its aspect sensitivity comes
from the simulator's model. Every detector-dependent statement therefore stays
model-conditional, and E3 is what bounds how far the simulator can be trusted on it.

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
BOAT (BlueBoat) — hardware and its own firmware only
├── Cerulean Omniscan 450 SS ×2 ───► raw pings
├── GPS / IMU / heading ───────────► USV pose
├── Water Linked USBL receiver ────► pinger position
└── ArduPilot ◄──────────────────── RC override from the laptop (+ link guardian script)

OPERATOR LAPTOP (via the BlueBoat Base Station WiFi) — the module chain
 sonar module ─► Perception ─► Belief ─► Replanner ─► Control ─► boat
 (seabed images  (detector,     (planned)  (planned)   (live path
  + metadata)     per-image                            update)
                  records)
```

| Module | Status | Role |
|---|---|---|
| Sonar module (`blueboat_sss`, `blueboat_gcs`) | existing | Acquisition, slant-range correction, bottom tracking, `.svlog`; the GCS turns the stream into **seabed images + metadata** |
| BlueBoat-Perception | existing (dummy detector by default; YOLO adapter built, not yet trained) | Seabed images → detector input → detector → calibration → detections for the GCS + **one record per image** for Belief; also builds simulated training datasets (dataset mode) |
| Ground Control Station | existing | Operator display. Shows **only Perception's detections**; runs no detector |
| Belief | **planned, not built** | Reads **only** Perception's per-image records, plus the mission's survey area and anchor. Sends **only** to the Replanner |
| Replanner | **planned, not built** | Reads **only** Belief. Acts on its own, in simulation and on the boat. Generates **every survey type** (including the two-pass baseline and the plain boustrophedon) and sends it through Control's live path update |
| Control (`blueboat_control`) | existing | Follows the path; owns the **live path update** service (`/blueboat/update_path`) and its progress / event topics. Built and tested in Gazebo; **not tested on water; no client yet** |
| Mission Control Station | existing | Operator station: launch, supervise, E-STOP. It does not use the path update yet; a survey-mission launch mode is planned |
| Link guardian | existing (not yet tested on the boat) | ArduPilot Lua script + laptop companion that brings the boat home if the link drops |
| Evaluation framework | **planned, not built** | Conditions, metrics, campaigns (§7.3, §8.4) |
| SSS-Dataset-Aug-Studio | optional | Offline augmentation of YOLO datasets; nothing depends on it |

⚠ The **belief layer is the only object the replanner reads.** Detector changes, sensor
changes, and planner changes interact only through it. Preserve this boundary. Belief carries
the mission's survey area and anchor with it, so the Replanner needs no other input.

### 5.2 Data structures

**SSS ping (custom ROS 2 message).** No standard type exists for side-scan. *Original
sketch; the implemented type is `blueboat_interfaces/OmniscanProfile` — one-sided, one topic
per side, mirroring the decoded Cerulean header — see `.claude/CLAUDE.md` §4.3 and §6 D2.*
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

TF tree: `map → odom → base_link → sss_link`, specified here; no module publishes or reads it
today (geometry is handled per module — `.claude/CLAUDE.md` §4.6, §6 D6). Lever-arm offsets
matter (transducer lateral offset 0.285 m).

**Detector input — boat-relative seabed images (as implemented in BlueBoat-Perception).**
⚠ The detector consumes **boat-relative** waterfall images (rows = pings, columns = the
device's native slant-range bins), never a world-frame mosaic. World-frame patches distort near
turns and introduce intensity-aggregation ambiguity when cells are revisited.

What the code does today:
- The ground control station cuts the waterfall into **seabed images** of 256 rows by 1200 to
  2402 native slant bins, one new image every 128 rows (50 % overlap). The cadence is therefore
  set by the ping rate, roughly 0.1–0.36 images/s, not a fixed 1–2 Hz.
- Perception receives each image as the **raw float dB** plus its metadata and maps it to the
  detector's 8-bit input with a fixed mapping (`fixed_gray_v1`): the per-row receive gain and a
  fixed range-reference curve are removed, then a fixed dB window (−31.15 … +17.16 dB) is
  scaled to 0…255. There is no per-image stretch. The operator's display PNG remains the
  `identity` baseline only.
- An optional near-range (nadir) mask and per-row turn flags exist; turn flags mark rows and
  detections, they drop nothing.
- The detector runs **once per image**. The default is still a placeholder (one detection at
  the image centre). Since 2026-10-23 a YOLO adapter (Ultralytics YOLO11s / YOLO26s) is built:
  it **tiles each image across-track** into 256 × 256 tiles at native resolution (stride 128,
  the nadir kept, never squashed), runs every tile, shifts the boxes back and merges the
  overlapping tiles' boxes (`nms`, or `greedy_nmm` = intersection-over-smaller union), giving
  one detection list and one record per image. No trained weights exist yet; the merge rule is
  chosen by the planned comparison on held-out simulated worlds.

Mapping a detection back to world coordinates: row → ping → USV pose; column → slant range →
ground range and side (the image's metadata carries the per-row track).

**Detector output → per-image record.** Perception publishes, for every image, a detections
array for the GCS and a JSON **image record** (`blueboat_perception/image_record/1`) for the
belief layer. A record holds: the per-row track (time, position, heading, speed, altitude,
bottom depth, attitude, look angles), the seabed polygon searched on each side and the image
footprint, and the detections.
```
per detection:
  pixel, class_name / class_id
  world_xy                geocoded centre (local ENU metres)
  covariance_xy           localisation uncertainty (geometric model, assumed sigmas)
  confidence_raw, confidence, calibrated   (identity calibration today: calibrated = false)
  look_azimuth_rad, grazing_angle_rad, boat_heading_rad, turn_backscan
per image:
  detections: []   searched, nothing found  (negative evidence)
  detections: null no pixels, unknown
```
⚠ Confidence only becomes a probability once calibrated (§8.2). The record carries no survey
area, no anchor and no latitude / longitude (local ENU metres only); Belief takes those from
the mission.

**Belief grid — multi-channel, world frame.** *Planned, not built. Reads only Perception's
image records plus the mission's survey area and anchor.*
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

**Replanner inputs** *(planned)*. Only the belief layer:
- Candidate list: cells with `p_target > τ_high`
- Coverage deficit: cells with `n_observations < n_min` or narrow `aspect_coverage`
- The mission's survey area and anchor, carried by Belief.

**Replanner output.** Timed path samples `[t, x, y, yaw]` sent to Control's live path update
service `/blueboat/update_path` (first path, or a replacement from a `change_point` on). Control
has no survey generator of its own; every survey type — the baseline included — is generated by
the Replanner. Control checks the update (continuity at the change point, speed, heading
coherence, sample count) and answers `ok` or a refusal code; a refusal changes nothing.
Progress is on `/blueboat/path_progress`, every answer and activation on
`/blueboat/path_update_event`. Built and tested in Gazebo for the PID, LoS and MPC controllers;
not tested on water; no client exists yet. Simulations of built worlds cannot yet run
replanner-owned runs (open item in Control's backlog).

### 5.3 Output artifacts

| Artifact | Purpose | Generation |
|---|---|---|
| Acoustic mosaic | Geocoded SSS imagery, no overlay | On demand / post-mission; the GCS also draws a live one as an operator display |
| Belief grid | Machine-readable P(target) heatmap | Live *(planned)* |
| Annotated mosaic | Mosaic + detection boxes | Post-mission, for figures |

⚠ The world-frame mosaic is an operator display and a figure source. It feeds no detector.
The detector's input is the boat-relative seabed image (§5.2).

---

## 6. Simulation

Two tiers with distinct jobs. ⚠ Neither substitutes for the other.

### 6.1 Tier 1 — Gazebo + acoustic model (primary)

Existing package `blueboat_sss_sim`. Procedural shallow-water world generation (seabed types,
bathymetry, configurable litter classes with position, orientation, burial, material,
reflectivity), physically motivated Omniscan 450 acoustic model, a sea state (current and waves
into Gazebo), and a **drop-in replacement for the real sonar interface** (same topics, types,
QoS, parameters) so the perception, planning and logging stacks run unmodified across sim and
real water. YOLO training data come from **BlueBoat-Perception's dataset mode**, which labels
the seabed images from the simulator's ground truth (highlight and acoustic shadow boxes, the
29 World Builder classes); the simulator itself exports no dataset.

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

### 7.1 Beach controlled-object campaign

Purpose: provide the controlled objects for the heading-response experiment (§7.2, E3), for
validating the simulator's motion and sensor, and for the final demonstration (§7.5, E6). It
is **not** a detector-dataset campaign: the detector is trained on simulated data (E2), and a
labelled real dataset is not on the critical path and blocks nothing. Real imagery collected
along the way is kept as primary field record and may later serve the optional E7 check.

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

Run in Gazebo across randomised scenes (object placement, seabed type, clutter density), at
20 m range per side in every condition (§8.5). All four conditions are generated by the
Replanner and sent through Control's live path update, so the baseline and the adaptive
variants share one execution path.

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
live replanning, live path update (Control's `/blueboat/update_path`). Feasibility proof, not
a statistical result. Prerequisites that do not exist yet: the Belief and Replanner modules, a
client in the Mission Control Station (a survey-mission launch mode), and a first water test
of the path update itself (Control's protocol `PATH_UPDATE_REAL_WATER_TEST.md`).

### 7.6 Simulator-to-real check *(optional, later)*

Purpose: produce E7. If a field day comes in time, run the simulation-trained detector on real
beach imagery and report how far the simulated conclusions carry over. One experiment, one
figure, one section. Nothing else waits on it.

⚠ The headline detector is trained on simulated data (E2). It therefore inherits its aspect
sensitivity from the simulator's model instead of measuring it. This is accepted and stated:
detector-dependent results stay model-conditional (§4.1), and the real heading-response
experiment (§7.2) is what bounds the simulator's aspect model.

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
work in this space bothers. Calibrate on **held-out simulated worlds** (worlds the detector
never trained on, never single images of a training world: consecutive seabed images overlap
50 %). Perception's calibration stage is the identity today (`calibrated: false`), so no
confidence it emits is a probability yet.

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
| Range setting, **every survey condition** | **20 m per side** | One setting for the baseline and the adaptive variants (no separate coverage and revisit passes). The default of the real driver and the simulator; the device's best range resolution is kept to ~27 m |
| Boat speed | 1.0 m/s nominal | Denser sampling than reducing range, without halving swath |
| Line spacing | ~0.8 × usable swath | Verify against the measured swath at 20 m, not the setting |
| Target ground range for detector training data | 5–20 m | Below: nadir gap. Above: along-track resolution limits |

⚠ Range setting does **not** change resolution at a given ground range — resolution is set by
beam geometry (`Δ_along = R · θ`) and pulse length. A shorter range raises the ping rate and
along-track sampling density and narrows the swath; this project does not use that lever: the
range is 20 m for every condition so that conditions differ only in where the boat goes and
from which heading.

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
| D1 | SSS data pipeline — slant-range correction, bottom tracking, geocoding, seabed images (the "waterfall buffer") | **Built**; verified live in simulation; field validation partial — no recording by the current stack exists (`.claude/CLAUDE.md` §6 D10) |
| D2 | Simulated detector datasets — made by Perception's dataset mode from the simulator's ground truth | Dataset mode **built** (29 classes, write-once, labelled); tile-dataset tool with the split by world **built** (2026-10-23); no simulated worlds built for it, no training run yet |
| D3 | Detection module — YOLO model in BlueBoat-Perception | Perception pipeline **built**; default detector is a **placeholder**; YOLO adapter over tiles, training and evaluation tools **built** (2026-10-23); no trained model, comparison not run; calibration is the identity |
| D4 | Belief layer — multi-channel Bayesian grid | **Planned, not built** (input contract exists: Perception's image records) |
| D5 | Mission interface — path following and live path update | **Built**: path following, and the live path update service with its progress and event topics (Gazebo-tested, not on water, no client yet) |
| D6 | Adaptive replanner — generates every survey type through the path update | **Planned, not built** |
| D7 | Evaluation framework — conditions, metrics, campaigns | **Planned, not built** |
| D8 | Thesis manuscript — submission early January 2027 | Ongoing |
| S1 | `blueboat_sss_sim` simulator package | **Built**, calibration ongoing |
| S2 | Policy surrogate | Optional stretch goal |
| S3 | SSS-Dataset-Aug-Studio — augmentation of YOLO datasets | **Built**, optional; nothing depends on it |

**Also built:** Mission Control Station (PySide6 — mission launching, run sessions, emergency
stop, node monitoring, bag replay, pattern designer), GCS visualisation app (live mosaic over
satellite tiles, USBL and Perception-detection overlays, session recording, seabed images),
BlueBoat base control (MPC / PID / LoS, MAVROS, Gazebo mode, per-run ros2bag and kinematic
replay), BlueBoat-Perception (above), the sea state of the simulator, and the **link
guardian** (ArduPilot script + laptop companion that brings the boat home when the link
drops; not yet tested on the boat).

⚠ The detector (D3) gates every downstream *quality* result, but it no longer waits on any
field campaign: its training data come from the simulator. The Replanner and Belief (D4, D6)
can be developed against Perception's records, with the dummy detector or the simulator's
ground truth standing in.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| **Detector quality gates everything.** Poor detector → noisy belief map → replanner chases false positives. | Build D3 early from the simulated datasets of D2. Calibrate on held-out simulated worlds (§8.2). Oracle ablation (the simulator's ground truth in place of the detector) isolates the effect. |
| **A simulation-trained detector inherits the simulator's aspect sensitivity** rather than measuring it. | Accepted and stated: detector-dependent results are model-conditional (§4.1). The real heading-response experiment (§7.2, E3) bounds the simulator's aspect model; the optional E7 check measures the carry-over. |
| Aspect-response check (§7.2) fails | Run early. A negative result reframes but does not kill the thesis — it becomes a regime-characterisation finding. |
| Single-site data caps generalisation | State plainly in limitations. Do not overreach elsewhere. |
| Headline result is simulation-derived | Phrase as model-conditional throughout (§4.1). Lead the limitations chapter with it. |
| Aspect-window widths not measurable at scale | Sensitivity sweep; report the range over which conclusions flip, including if they flip inside the plausible range. |
| Live path update corner cases (first use on water; built-world simulation cannot yet run replanner-owned runs) | Control's refusal codes leave the boat on its current path; Gazebo tests exist; follow the real-water test protocol before relying on it. Fallback: replan only between runs. |
| Weather / schedule slip on field campaigns | Simulation is the defensible basis for the evaluation, given calibration is in place; nothing in the headline result waits on a field day. |

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
6. Open release of platform stack, simulator, dataset generator, and methodology.

**Closest precedents.** CORAL is the platform precedent — analogous hardware, same regime,
but a capability demonstrator with no automated detection, no closed loop, no baseline
comparison, no open release. Sethuraman et al. 2024 is the conceptual precedent —
multi-view informed active perception with SSS, next-best-view selection, but AUV-based and
evaluated only in photorealistic simulation. Positioning as the surface-platform,
real-water-demonstrated counterpart is stronger than positioning as a cheaper
re-implementation.

---

## 12. Schedule

**Thesis submission: early January 2027.** The scientific goal and the headline claim (§4.1)
are unchanged. The simulated policy comparison (E4) is the core of the work and is never
gated on a field day; real-water work (E3, E6, and the optional E7) goes in as field days
allow. No venue or publication plan is kept in this document.

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

**Working on the detector?** §5.2 (boat-relative seabed images ⚠, the record), §7.1 (object
classes), §8.2 (calibration ⚠, on held-out simulated worlds), §8.4 (metrics). The model is YOLO
in BlueBoat-Perception, trained on simulated datasets from its dataset mode; real water is not
on its critical path.

**Working on the belief layer?** §5.1 (it reads only Perception's image records plus the survey
area and anchor, and sends only to the Replanner), §5.2 (multi-channel grid), §8.1 (what the
replanner needs), negative observations must update the posterior.

**Working on the replanner?** §5.1–§5.2 (reads only Belief; output through the live path
update), §8.1 (three required rules ⚠), §8.3 (aspect rule), §7.3 (baseline is two-pass
orthogonal ⚠), §8.5 (20 m for every condition).

**Working on the simulator?** §6 (two tiers), §6.3 (validate aspect response — go/no-go ⚠),
§4.2 (what July can and cannot support ⚠).

**Planning experiments?** §7.2 is the keystone ⚠. §7.1 lists the controlled objects, not a dataset. §8.6 (operational
rules).

**Writing?** §4.1 (headline phrasing ⚠), §3.2 (state out-of-scope explicitly ⚠), §11
(positioning), §10 (lead limitations with the model-conditional caveat).
