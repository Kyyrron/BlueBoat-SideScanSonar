# CLAUDE.md — BlueBoat Aspect-Aware SSS Survey (superproject)

Root guidance for the superproject carrying eight git submodules: **how the modules relate**, the
cross-module rules, and workspace and git architecture. Not a backlog: open work lives in each submodule's
`TODO.md`, and the cross-repository list is `docs/OPEN_ITEMS.md`.

**Authority order.** `project_synthesis.md` is the single source of truth for scope, system architecture
(§5), data structures (§5.2) and every ⚠-marked rule. Where a module's `CLAUDE.md` contradicts it,
`.claude/synthesis-discrepancies.md` records the disagreement instead of resolving it silently. Below that,
each submodule's `CLAUDE.md` is authoritative for its own internals; this file only for cross-module
relationships. **Full text of every section below: `docs/DESIGN.md`** (moved verbatim on 2026-11-18,
same section numbers). Dated history: `docs/HISTORY.md`. Where the project stands: `docs/PROJECT_STATE.md`.

Markers: **VERIFIED** (stated in `project_synthesis.md`, or in a module section that module marks VERIFIED),
**HISTORICAL** (from design sessions, not a scan of the current tree), **UNCERTAIN** (contested or never
established). Markers are carried forward, never upgraded.

## 0. Simulator frozen (2026-11-18)

`BlueBoat-SSS-Sim` is **frozen** at tag `sim-freeze-v1.0-2026-11-18` (the owner creates the tag; it did not
exist yet on 2026-11-18), code digest `cc29e08780aac4cd`
(`python3 -m blueboat_sss_sim.core.provenance --check`). The acceptance protocol's literal verdict is
**NOT READY**. The owner froze it anyway as a **model-conditional tool** (decision:
`~/ros2_ws/sim_runs/sim_acceptance/freeze_decision.md`). The acceptance work (sessions 01–10) is over.

- **No simulator code change** (any `*.py` of the package or `config/*.yaml`). A change means a new
  simulator version, by owner decision only. **v1.1 (2026-11-21, session 14, owner order; pending signature):**
  world generation only (World Builder Screen 5's Mission-like mode, `builder/` only), code digest `bbd4112928645e13`,
  engine digest unchanged; the evidence-based population model is a second package of the simulator's repository,
  `BlueBoat-SSS-Sim/blueboat_harbour_population/` (outside the code digest; `docs/population/` of that repository).
- Every simulated result is produced and stated under the conditions file, imported here:

@../SIM_VALIDITY_CONDITIONS.md

## 1. System overview

A BlueRobotics BlueBoat USV runs autonomous aspect-aware side-scan sonar survey in shallow enclosed water.
Sonar and navigation stream over the BlueBoat Base Station WiFi link to the operator laptop, which runs
**all** project software and returns the waypoint missions. **VERIFIED** (`project_synthesis.md` §1, §5.1).

```
sonar module (seabed images + metadata) → Perception → Belief → Replanner → Control
```

| Module | Role (detail: `docs/DESIGN.md` §1, state: `docs/PROJECT_STATE.md`) |
|---|---|
| BlueBoat-Control | Motion, pose, thrust, trajectories, run bags and replay, live path update `/blueboat/update_path`; owns `blueboat_interfaces`. Frozen at `v1.0`, additions only |
| BlueBoat-MCS | Mission launch and supervision, Pattern Designer, safe shutdown. Frozen at `v1.0`, additions only |
| BlueBoat-SSS | `blueboat_sss` (sonar driver, processor, `.svlog`) and `blueboat_gcs` (mosaic, overlays, recording, seabed images) |
| BlueBoat-SSS-Sim | Gazebo worlds, the drop-in simulated sonar (ray-cast `raycast_harbour_fast` = production sensor; the geometric renderer is legacy), sea state. **Frozen 2026-11-18** |
| BlueBoat-Perception | The station's one detection source (`/sss_ai/detections`, `/sss_ai/image_records`); dummy detector by default, YOLO over tiles not yet trained; dataset mode |
| BlueBoat-Belief | Belief map: pings + detections → `BeliefGrid` (`belief_grid/0`); built, never with a real detector |
| BlueBoat-Replanner | Aspect-aware replanner, every survey condition C1–C4 through `/blueboat/update_path`; built; once in Gazebo beside Control's node (a C2 development run in a built world, 2026-11-18); never on the boat |
| SSS-Dataset-Aug-Studio | Optional offline augmentation of YOLO datasets; nothing depends on it |
| `link_guardian/` (not a submodule) | Connection-loss guardian: ArduPilot Lua script + laptop `guardian.py` (`link_guardian/README.md`) |
| Evaluation | Planned, not built |

- The GCS shows **only Perception's detections**; it runs no detector.
- **Belief** reads `/sss_processor/processed`, `/sss_ai/detections`, odometry, GPS, a survey-area file, and
  optionally `/sss_ai/image_records` (which pings the detector searched). It sends `BeliefGrid` to the
  Replanner, and displays and `/diagnostics` to the operator; nothing else.
- The **Replanner** reads Belief as its only target evidence, acts on its own, and generates every survey
  type through Control's live path update.

### 1.1 Deployment — VERIFIED by the owner, 2026-09-28

**All** code runs on **this computer** (`~/ros2_ws`). The boat carries only hardware and its own firmware:
ArduPilot/BlueOS (MAVROS at `192.168.2.2`), two Omniscan 450 SS (`192.168.2.92` / `.93`, TCP 51200, driven
by `sss_node.py` from here), GPS/compass, Water Linked USBL (`192.168.2.94`). **Nothing of ours runs on the
boat. `/blueboat_ws` never existed in this project**; never expect, suggest or document it. A stale
deployment is a stale `~/ros2_ws/install` (rebuild with `colcon build`). In documents "robot-side" / "on the
boat" never locate software: name the node, or say "in a real-robot run". The one exception (owner,
2026-10-14) is the link guardian's Lua script, copied onto the autopilot as autopilot configuration; its
behaviour (`LGRD_ON`, neutral after 3 s, return along the trail after 15 s, automatic hand-back) is in
`link_guardian/README.md` and `docs/DESIGN.md` §1.1.

## 2. Workspace and build order

`~/ros2_ws` is the project's only ROS workspace; the superproject is checked out at
`~/ros2_ws/src/BlueBoat-SideScanSonar/` and is not itself the colcon workspace (`colcon build` runs from
`~/ros2_ws`). Two ROS packages sit one level below their git roots: `BlueBoat-SSS-Sim/blueboat_sss_sim/` and
`BlueBoat-Perception/blueboat_perception/`. Build `blueboat_interfaces` first;
`blueboat_belief_interfaces` before `blueboat_belief` (from a shell that has not sourced the venv);
`blueboat_harbour_population` (beside `blueboat_sss_sim` in the simulator's repository) depends on nothing at build time;
`blueboat_replanner` needs both interface packages. `blueboat_gcs` and `BlueBoat-MCS` are not colcon
packages. **No file is owned twice.** Detail: `docs/DESIGN.md` §2.

## 2.1 Git operations — session boundary

**Sessions never run `git commit` or `git push`, in the superproject or in any submodule.**
Make the requested file changes and stop there; the user handles staging, committing and
pushing themselves, everywhere in this tree. Sessions never create tags either.

## 3. Git architecture

The eight module directories are git **submodules**; root `git status` shows a submodule as modified
without naming files, so inspect inside it. **Frozen modules:** `BlueBoat-Control` and `BlueBoat-MCS` (tag
`v1.0`, 2026-09-14) are not edited without an explicit user order and are then changed **by additions only**
(owner, 2026-10-20): nothing proven is renamed, retyped or changed in behaviour unless it is shown identical
(`BlueBoat-Control/test/mc_harness.py --compare HEAD`, MCS's smoke test, the interface baseline). The dated
orders are in skill `git-history`. **`BlueBoat-SSS-Sim` is frozen in code since 2026-11-18** (§0).

## 4. Cross-module interface contract

**`.claude/interface-contract.md`** (sections §4.1–§4.7). **Read it before adding, changing, consuming or
debugging any topic, service, QoS profile, parameter, frame convention or file-level handoff** between
modules. `.claude/rules/interface-contract.md` reminds you of this whenever a launch file, a
`.msg`/`.srv`, a `ros/` file or a Control or SSS node is read or edited.

## 5. Project-wide non-negotiables (full text and evidence: `docs/DESIGN.md` §5)

- **CM-1 Signatures are a cross-repo contract.** No module renames or retypes a topic, service or parameter.
  `blueboat_interfaces` is the only home of vehicle and sonar message types; new modules may own their own
  interfaces package; extra simulation data goes on new additive JSON topics.
- **CM-2 Simulation and real water expose the identical ROS interface** (names, types, QoS, parameters,
  node names, acquisition defaults), and "identical" must be demonstrated (`fault_injection_sonar.yaml`).
  Exception: the run-session plumbing exists only in a real-robot launch. A bag replay is neither graph.
- **CM-3 No module modifies a neighbour's package.**
- **CM-4 QoS is changed at both ends or not at all.**
- **CM-5 Side identity comes from the packet** (`channel_number`, byte 34; fallback: sign of
  `transducer_heading_deg`), never from the topic or `src`.
- **CM-6 Never drop a ping.** Rows assemble by normalised `ping_number`; one-sided rows are emitted.
- **CM-7 Field data and generated ground truth are write-once** (`.svlog`, position CSVs, `.npy` logs,
  mission bundles, worlds); the Aug Studio never modifies an input dataset.
- **CM-8 Monitoring output is world-frame at the source**; no consumer re-applies a frame correction.
- **CM-9 Belief is the only target evidence the Replanner reads** (never detections, sonar data, ground
  truth or `/sim/*`).
- **CM-10 AI inputs are waterfall-domain and boat-relative**, never world-frame mosaic crops.
- **CM-11 The headline detector is a YOLO model in Perception, trained on simulated datasets, calibrated on
  held-out simulated worlds**; split and calibrate by world, never by image. Detector-dependent results stay
  model-conditional.
- **CM-12 The policy baseline is two-pass orthogonal, tuned seriously.**
- **CM-13 Headline results are model-conditional:** "In a calibrated simulation environment, …", the
  caveat leading the limitations chapter; never a layer above its evidential weight.
- **CM-14 Perception, control and AI iteration happen offline against recordings** (run bags for control;
  GCS sessions with `blueboat-perception-offline` for perception), never in the water.
- **CM-15 Safe shutdown precedes terminating a launch** (`default` on `/blueboat/input_str`, matched
  subscriber, `/blueboat/param_mode` echo, then terminate). E-STOP, servo release and ending the mission are
  three separate operator actions.
- **CM-16 `enable_motors` gates all thruster output, and a closed gate streams neutral** (1500/1500 while in
  override).

## 6. Discrepancies against `project_synthesis.md`

`.claude/synthesis-discrepancies.md` (D1–D11). Read it before relying on a `project_synthesis.md` §5
statement about what is built.

## 7. Where the detail lives

| Topic | Read |
|---|---|
| Scope, evidence architecture, claim phrasing, design rules | `project_synthesis.md` §§1–4, §8 |
| Experiment design, target classes, metrics, campaign | `project_synthesis.md` §7–§8.4, `target_families_and_surrogates.md` |
| Simulator conditions, freeze, evidence | `SIM_VALIDITY_CONDITIONS.md`; `~/ros2_ws/sim_runs/sim_acceptance/10_evidence/SIM_FREEZE_CARD.md` |
| Project state, open items, doc map | `docs/PROJECT_STATE.md`, `docs/OPEN_ITEMS.md`, `docs/DOC_MAP.md` |
| Controllers, thrust path, trajectories, MAVROS bridge | `BlueBoat-Control/.claude/CLAUDE.md`; `blueboat_control/src/TRAJECTORY_SYSTEM.md`, `FIELD_TUNING.md` |
| Live path update (the Replanner's entry point) | `BlueBoat-Control/docs/PATH_UPDATE_INTERFACE.md`, `PATH_UPDATE_DESIGN.md`, `docs/REQUESTS.md` |
| Sonar driver, processor, `.svlog`, GCS | `BlueBoat-SSS/.claude/CLAUDE.md`, open items `BlueBoat-SSS/.claude/TODO.md` |
| Acoustic model, worlds, renderers, smoke test | `BlueBoat-SSS-Sim/.claude/CLAUDE.md`; ray-cast status `blueboat_sss_sim/docs/engineering/raycast_assessment.md` |
| Station threading, map, Pattern Designer | `BlueBoat-MCS/.claude/CLAUDE.md` |
| Augmentation (optional module) | `SSS-Dataset-Aug-Studio/.claude/CLAUDE.md` |
| Belief map | `BlueBoat-Belief/.claude/CLAUDE.md`; `blueboat_belief/docs/MATH.md`, `topics.md`, `OFFLINE_CORE_API.md`, `VALIDATION_REPORT.md` |
| Replanner | `BlueBoat-Replanner/.claude/CLAUDE.md`, `docs/REPORT.md` |
| Detector pipeline, dataset mode, offline = live | `BlueBoat-Perception/.claude/CLAUDE.md`; `docs/PREPROCESSING_STUDY.md`, `docs/LIVE_CHECKS.md` |
| Connection-loss guardian | `link_guardian/README.md` |
| Per-module gates and exact commands | skill `module-gates` |
| Running and recording a simulated survey from the command line | `tools/sim_record/README.md`, skill `sim-run-recording` |
| Dated owner orders that opened Control / MCS | skill `git-history` |
| MAVROS boundary table, other served interfaces | skill `interface-inventory` |
| Cross-module file formats | skill `file-interfaces` |

**Detail that loads by itself.** The superproject and every module with `.claude/` topic files (all but Belief)
have `.claude/rules/*.md`: path-scoped rules (globs relative to that repository) that import the topic files when
Claude reads or edits a matching file, whether the session started here or inside the module.

**CLAUDE.md map: read the relevant one before touching a directory.** A nested `CLAUDE.md` loads by itself
only when Claude reads, writes or edits a file in its directory (a Bash `cat`/`head` of one file counts; Grep
and Glob do not). So before
changing anything under these paths (or scripting a change there), Read its `CLAUDE.md` first: every
`<module>/.claude/CLAUDE.md`; `BlueBoat-Control/` `blueboat_control/src/`, `blueboat_description/`,
`log_reviewer/`; `BlueBoat-SSS/blueboat_sss/blueboat_gcs/`; `BlueBoat-SSS-Sim/blueboat_sss_sim/` `launch/`,
`blueboat_sss_sim/builder/`, `blueboat_sss_sim/calibration/`, `blueboat_sss_sim/sea/`;
`BlueBoat-MCS/mcs/designer/`. Where a module document marks a section HISTORICAL or UNCERTAIN, the repository
outranks the document: prefer reading a file to trusting a description of it.

**The two reviews.** `project_review.md` and `sim_review.md` (superproject root, tracked) are dated review
documents that ~20 source files cite by section: load-bearing, not archive. Their measurement chain
`~/ros2_ws/sim_review_work/` is outside every repository and frozen at the pre-2026-09-18 constants:
provenance, never a gate (re-running it shows deltas that are the fix, not a regression).
