# CLAUDE.md — BlueBoat Aspect-Aware SSS Survey (superproject)

Root guidance for the superproject carrying six git submodules: **how the modules relate** —
merged interface contract, cross-module rules, workspace and git architecture. Not a backlog:
open work lives only in each submodule's own `TODO.md`, never restated here.

**Authority order.** `project_synthesis.md` (project files) is the single source of truth for
scope, system architecture (§5), data structures (§5.2) and every ⚠-marked rule; where a
module's `CLAUDE.md` contradicts it, §6 records the disagreement rather than resolving it
silently. Below that, each submodule's `CLAUDE.md` is authoritative for its own internals;
this file only for cross-module relationships.

## Verification markers

| Marker | Meaning |
|---|---|
| **VERIFIED** | Stated in `project_synthesis.md`, or in a module `CLAUDE.md` section that module itself marks VERIFIED. |
| **HISTORICAL** | Carried from module documents written from design sessions rather than a scan of the current tree. |
| **UNCERTAIN** | Ambiguous, contested between modules, or never established. |

Markers are carried forward, never upgraded: HISTORICAL in `sssCLAUDE.md` is HISTORICAL here.

---

## 1. System overview

A BlueRobotics BlueBoat USV runs autonomous aspect-aware side-scan sonar survey in shallow
enclosed water. Sonar and navigation stream over the BlueBoat Base Station WiFi link to the
operator laptop, which runs **all** project software and returns the waypoint missions; the
operational constraint is link bandwidth and latency, not on-board compute. **VERIFIED**
(`project_synthesis.md` §1, §5.1; deployment §1.1.)

```
BOAT — hardware + its own firmware only    THIS COMPUTER (operator laptop, ~/ros2_ws) — ALL our code
├─ Cerulean Omniscan 450 SS ×2 (.92/.93)   ├─ MAVROS · blueboat_control (robot_interface, master_control, …)
├─ ArduPilot / BlueOS autopilot (.2)       ├─ blueboat_sss: sss_node.py (sonar driver) · sss_processor_node
├─ GPS / compass                           ├─ Mission Control Station  (supervise, command, E-STOP)
└─ Water Linked USBL (.94)                 ├─ BlueBoat GCS             (mosaic, overlays, recording)
        ▲                                  ├─ SSS-Dataset-Aug-Studio   (offline, no ROS)
        │                                  ├─ BlueBoat-Perception      (detector — dummy default; YOLO over tiles, untrained — + image records)
        └── BlueBoat Base Station (WiFi) ──┤  [Belief · Replanner · Evaluation]  planned, not built
            192.168.2.0/24                 └─ SIMULATION: blueboat_sss_sim serves the identical sonar
                                              interface, Gazebo owns hull dynamics
```

**The module chain (owner's decision, 2026-10-20; `project_synthesis.md` §5.1).**

```
sonar module (seabed images + metadata) → Perception → Belief → Replanner → Control
```

- The GCS shows **only Perception's detections** (`/sss_ai/detections`); it runs no detector.
- **Belief** reads **only** Perception's per-image records (`/sss_ai/image_records`) plus the
  mission's survey area and anchor, and sends **only** to the Replanner.
- The **Replanner** reads **only** Belief, acts on its own (simulation and boat alike) and
  generates **every survey type** through Control's live path update (`/blueboat/update_path`,
  §4.1).
- **Belief, Replanner and Evaluation are planned, not built.** No package, node or topic of
  theirs exists. Perception and the link guardian exist; the Aug Studio is optional.
- The Mission Control Station does not use the path update yet; a survey-mission launch mode
  is the planned way (Control `docs/REQUESTS.md` R-1). A built-world simulation cannot yet run
  a replanner-owned run (R-3).
- New modules may own their own interfaces package (CM-1); an existing topic is never renamed
  or retyped.

### 1.1 Deployment — **VERIFIED by the owner, 2026-09-28**

**All** code runs on **this computer** (`~/ros2_ws`): every ROS node (MAVROS,
`robot_interface`, `master_control`, `path_generation`, `uwgps_log`, `sss_node.py`,
`sss_processor_node`, `perception_node`, the simulator), the Mission Control Station and the GCS. It reaches the
boat through the **BlueBoat Base Station** — Blue Robotics' WiFi radio link, never a name for
the laptop. The boat carries only hardware and its own firmware: ArduPilot/BlueOS autopilot
(MAVROS at `192.168.2.2`), two Omniscan 450 SS (`192.168.2.92` / `.93`, TCP 51200, driven by
`sss_node.py` from here), GPS/compass, Water Linked USBL (`192.168.2.94`, polled by
`uwgps_log` from here). **Nothing of ours runs on the boat. `/blueboat_ws` never existed in
this project** — a months-old artifact never to be expected, suggested or documented again. A
stale deployment is a stale `~/ros2_ws/install` (rebuild with `colcon build`), never a "boat
build". In documents "robot-side" / "on the boat" never locate software: name the node, or say
"in a real-robot run".
**One owner-ordered exception (2026-10-14):** the connection-loss guardian
`link_guardian/autopilot/link_guardian.lua` (superproject, not a submodule) is an ArduPilot
Lua script copied onto the autopilot — autopilot configuration, not a ROS node. While its
session flag `LGRD_ON` is set (by the laptop for every real-robot session; reset at every
autopilot boot) and MAVROS's heartbeat (ROS 2 MAVROS: **sys 1 / comp 191**) has been silent
for `LGRD_NEUTRAL` s (3) it holds the passthrough thrusters at neutral (RC override 1500 —
with no RC receiver ArduPilot otherwise keeps the last laptop command), and after
`LGRD_TIMEOUT` s (**15**, was 5 until 2026-10-28) it switches `SERVO1/3_FUNCTION` from
passthrough to 74/73, **arms the autopilot itself** if needed (ArduPilot refuses to arm on
passthrough; first attempt 3.5 s after the switch, so Rover's disarmed 1 Hz loop has set the
±1000 thruster range), and **retraces the boat's own trail** in reverse in GUIDED (recorded
in the script's memory every 2 m while the guardian is ON, armed or not, whatever the station
drives; RTL only as fallback). On the laptop's **first heartbeat** it hands control back
itself — HOLD → the saved passthrough mapping → MANUAL — so the run goes on with no operator
action (owner, 2026-10-28; MCS "Take back control" is a fallback). Its
laptop companion `link_guardian/laptop/guardian.py` (plain script, not a colcon package) is
started by MCS with every real-robot launch: sets the flag, moves HOME to each run start,
serves MCS's GUARDIAN box over `/link_guardian/status` / `/link_guardian/command`. Design,
setup and test ladder: `link_guardian/README.md`.

| Module | Produces |
|---|---|
| **BlueBoat-Control** | Vehicle motion, pose, thrust, trajectories; per-run ros2bag + kinematic Gazebo replay of a run (v1.1); owns `blueboat_interfaces` — **frozen at tag `v1.0`** (§3), with user-ordered additive changes since (`UpdatePath.srv`, 2026-10-15) |
| **BlueBoat-SSS** — `blueboat_sss` | Sonar acquisition, slant-range correction, bottom tracking, `.svlog` |
| **BlueBoat-SSS** — `blueboat_gcs` | Live mosaic, overlays, recording sessions, seabed images |
| **BlueBoat-MCS** | Mission launch/supervision (incl. "From a ros2bag" replay launches and the link guardian's GUARDIAN box, v1.1), pattern designer, safe shutdown — **frozen at tag `v1.0`** (§3) |
| **BlueBoat-SSS-Sim** | GPS-anchored Gazebo worlds (World Builder GUI over MCS anchored paths) + a drop-in replacement for the real sonar interface (two renderers: the calibrated geometric default and a GPU ray-cast run in a slowed simulation, §4.3) + the **sea state** (current/waves into Gazebo, `sea_state_node`) |
| **SSS-Dataset-Aug-Studio** — *optional* | Physics-informed augmentation of YOLO datasets (offline, file-level only); nothing in the chain depends on it |
| **Link guardian** (`link_guardian/`, not a submodule) | Connection-loss guardian: ArduPilot Lua script + laptop companion `guardian.py` (§1.1). Not yet tested on the boat |
| **Belief · Replanner · Evaluation** | **Planned, not built** — the chain above; open requirements `project_synthesis.md` §5.2, §8.1, §8.4 |
| **BlueBoat-Perception** — `blueboat_perception` | **The station's one detection source** (since 2026-10-16): the GCS's seabed images → detector input (`fixed_gray`, a fixed mapping of the raw dB) → detector (the station's former dummy, still the default; or since 2026-10-23 a YOLO model — Ultralytics YOLO11s / YOLO26s, imported lazily — run on 256 × 256 across-track tiles at native resolution and merged across tiles, `nms` / `greedy_nmm`; no trained weights yet) → calibration (identity) → `/sss_ai/detections` for the GCS map + one record per image (`/sss_ai/image_records`) for the future belief layer. ROS-free deterministic core, thin node, offline CLI (offline = live, byte-equal records); dataset mode: a YOLO dataset per world run, labelled from the simulator's ground truth (highlight + shadow boxes, the 29 World Builder classes), plus the archival ground-truth bag; offline tools (not installed): tile datasets split by world, YOLO training, evaluation on held-out worlds |

---

## 2. Workspace layout and build order

**VERIFIED.** Each submodule's `.gitmodules` `path` equals its repository name, directly under
the root; the surprise is that two ROS packages sit one level below their git roots: the
simulator's at `BlueBoat-SSS-Sim/blueboat_sss_sim/` and Perception's at
`BlueBoat-Perception/blueboat_perception/`. A `.../BlueBoat-SideScanSonar/blueboat_mcs/`
path in an older document is history.

`~/ros2_ws` is the project's **only** ROS workspace (§1.1). The superproject is checked out at
`~/ros2_ws/src/BlueBoat-SideScanSonar/` and is not itself the colcon workspace; `colcon build`
runs from `~/ros2_ws`. Build `blueboat_interfaces` first — every ROS module's types resolve
there (`OmniscanProfile`, `ProcessedSSSPing`, `RequestPath.srv`, `UpdatePath.srv`); `blueboat_sss_sim` modifies
no other package (`simCLAUDE.md` NC #8). `blueboat_perception` (`ament_python`) uses standard
types only (`std_msgs`, `sensor_msgs`, `vision_msgs`), so it has no build-order constraint;
the GCS imports its ROS-free core lazily for the replay window's Run AI (installed package,
else the superproject checkout), and Perception imports nothing from the GCS. Two submodules are not colcon packages:
`blueboat_gcs` and `BlueBoat-MCS` import `rclpy` from a sourced workspace at runtime and
degrade to GUI-only without it; `SSS-Dataset-Aug-Studio` has no ROS dependency in any mode
(its dev-only `tools/make_demo_dataset.py` puts `../BlueBoat-SSS-Sim/blueboat_sss_sim` on
`sys.path` for the simulator's ROS-free offline path; not installed).

**No file is owned twice.** `BlueBoat-MCS/integration/` **no longer exists**; its four nodes
are committed in and installed by `blueboat_control` — nothing needs copying beyond a normal
`colcon build`.

---

## 2.1 Git operations — session boundary

**Sessions never run `git commit` or `git push`, in the superproject or in any submodule.**
Make the requested file changes and stop there; the user handles staging, committing and
pushing themselves, everywhere in this tree.

## 3. Git architecture

The six module directories are git **submodules**, each an independent repository; root
`git status` shows a submodule as modified without naming files — inspect inside it.
`.gitmodules` paths are authoritative for the layout.

**Frozen modules (recorded 2026-09-18).** `BlueBoat-Control` and `BlueBoat-MCS` are frozen at
tag `v1.0` (Control `65b15bb`, MCS `790934f`, both on `origin/main`, 2026-09-14). **Sessions do
not edit these two submodules** unless the user explicitly orders it; a needed change becomes a
post-v1.0 item in the requesting module's `TODO.md` or a review's update plan. **Add-only rule
(owner, 2026-10-20):** Control and MCS are updated **by additions only** — a new topic, service,
parameter, launch argument or UI element; nothing proven is renamed, retyped or changed in
behaviour unless the behaviour stays identical *and is shown to be*
(`BlueBoat-Control/test/mc_harness.py --compare HEAD`, MCS's smoke test, the interface
baseline). Every dated owner order is an instance of this rule. The "frozen" statement is the
**2026-09-18 baseline**: the gitlinks have since moved on (2026-10-20: Control `b94dd7b`, MCS
`490f195`), so the trees are no longer identical to the tags. The dated orders (2026-09-28 to
2026-10-16: documentation splits, sea-state UI, run sessions, v1.1 run bags and bag replay,
link guardian, live path update, the Perception companion in MCS) are recorded in skill
`git-history`. BlueBoat-Perception itself (added 2026-10-16) is not frozen.

---

## 4. Cross-module interface contract

**Moved to `.claude/interface-contract.md`** (superproject root; section numbers kept, so every
"§4.1"–"§4.7" reference points there). **Read it before adding, changing, consuming or
debugging any topic, service, QoS profile, parameter, frame convention or file-level handoff**
between modules: per-topic producers/consumers, QoS, frames, sonar acquisition defaults, ray-cast
slow-down, MAVROS rates. The rules it implements are §5 below, which stay here.

---

## 5. Project-wide non-negotiables

Only genuinely cross-module constraints (a shared boundary, or reached independently by two or
more modules); module-local rules stay in the module.

**CM-1 — Topic, service and parameter signatures are a cross-repo contract.** No module
changes a name or message type unilaterally; refactors change file internals only
(`ctrlCLAUDE.md` N1, `simCLAUDE.md` NC #1; all of §4 depends on it). `blueboat_interfaces` is
the only place a *vehicle or sonar* message type is defined; the sim reuses it and puts
additional simulation data on new additive JSON topics (`ground_truth/contacts` is the
pattern). **New modules (Belief, Replanner, Evaluation) may own their own interfaces package**
(owner, 2026-10-20), and BlueBoat-Perception already publishes JSON and standard types only;
what is never allowed is renaming or retyping an existing topic, service or parameter.

**CM-2 — Simulation and real water expose the identical ROS interface:** names, types, QoS
(BEST_EFFORT / KEEP_LAST / 10 on the sonar topics), parameter names, node names, ping-enable
semantics and, since 2026-09-28, the acquisition defaults (§4.3). One deliberate,
user-ordered exception (2026-10-09): the run-session plumbing (`/blueboat/run_command`,
`/blueboat/run_state`, `/blueboat/run_log`) exists only in a real-robot launch with
`session_mode:=true` — operator/station plumbing, no sensor or perception interface, and
every downstream stack runs unchanged against both graphs. A **bag replay** (v1.1,
`Replay_launch.py`) is neither graph: it plays a recorded real run back (telemetry on its live
names, commands under `/replay/`), so it is evidence about that run, never a simulation result
and never one side of the sim-to-real comparison. A run slowed below real time for the
ray-cast sonar (§4.3) **is** the simulation graph, on one slower clock: same interface, same
records. Downstream stacks run
unmodified in both; divergence invalidates the sim-to-real comparison the thesis rests on
(`ctrlCLAUDE.md` N2, `simCLAUDE.md` NC #1). **Corollary (2026-09-18): "identical" has to be
*demonstrated*, and a clean simulation cannot** — a stream whose gain never walks, whose
counter never restarts, which never reports `channel_number: 255` or drops a ping leaves four
downstream paths untaken (the processor's gain compensation stuck at `g = 0`, its counter
re-base and the CM-5 side fallback never entered, CM-6's one-sided rows never occurring). So
the sim ships `config/fault_injection_sonar.yaml` (all knobs off by default), putting all five
on the wire, each reproducing something the corpus shows; running the real stack against it
once turns CM-2 from a claim into a test.

**CM-3 — No module modifies a neighbour's package.** Integration happens by serving identical
interfaces (`simCLAUDE.md` NC #8, `mcsCLAUDE.md` N9, `ctrlCLAUDE.md` N1). **No exception
remains:** no source file is owned by two submodules (§2).

**CM-4 — QoS is changed at both ends or not at all.** A `RELIABLE` subscriber against a
`BEST_EFFORT` publisher receives *nothing* (`sssCLAUDE.md` NC #4); a non-latched subscriber
against `TRANSIENT_LOCAL` never sees a sample published before it matched, so a latched
one-shot `/blueboat/controller_ready` was missed — the latched-readiness row of §4.1 is the
second instance of the same failure mode, closed by re-publishing, not by changing QoS.

**CM-5 — Side identity comes from the packet, never from the topic or the `src` tag:**
`channel_number` at byte 34, falling back to the sign of `transducer_heading_deg`. VERIFIED
against 5250 packets, zero mismatches. Applies to any module consuming raw frames or profiles.

**CM-6 — Never drop a ping.** Rows assemble by `ping_number` **normalised by the per-device
counter offset** (§4.3); one-sided rows are emitted, not discarded; no ping is withheld
because the bottom tracker has not locked (`sssCLAUDE.md` NC #2). Obeyed by
`sss_processor_node` and the GCS replay path; a missing pose is the only sanctioned drop, and
it is BlueBoat-Control's to fix.

**CM-7 — Field data and generated ground truth are write-once.** Recorded `.svlog` files,
position CSVs and controller `.npy` logs are primary field record, never overwritten or
regenerated; mission bundles are immutable snapshots, regenerated rather than edited; the Aug
Studio never modifies an input dataset (`sssCLAUDE.md` NC #6, `ctrlCLAUDE.md` §6,
`simCLAUDE.md` NC #10, `augCLAUDE.md` #1).

**CM-8 — Monitoring output is world-frame in every controller branch, and no consumer
re-applies a frame correction.** The conversion belongs at the source (`ctrlCLAUDE.md` N9,
`mcsCLAUDE.md` N3 — two halves of one rule).

**CM-9 — The belief layer is the only object the replanner reads.** Detector, sensor and
planner changes interact only through it (`project_synthesis.md` §5.1 ⚠, `sssCLAUDE.md` #15).
Belief reads only Perception's per-image records plus the mission's survey area and anchor,
and sends only to the Replanner; the Replanner reads only Belief. Nothing in the current tree
implements either — §6 D7.

**CM-10 — AI inputs are waterfall-domain and boat-relative, never world-frame mosaic crops:**
world-frame patches distort near turns and make intensity aggregation ambiguous where cells
are revisited (`project_synthesis.md` §5.2 ⚠, `sssCLAUDE.md` #12).

**CM-11 — The headline detector is a YOLO model in BlueBoat-Perception, trained on simulated
datasets (Perception's dataset mode), with its confidence calibrated on held-out simulated
worlds** (owner, 2026-10-20; replaces "trains on real imagery only"). Real water validates the
simulator (motion and sensor), runs the heading-response experiment, checks simulator-to-real
conclusions later and serves the final demonstration; a labelled real dataset blocks nothing.
**Consequence to keep stated:** a simulation-trained detector inherits its aspect sensitivity
from the simulator's model, so detector-dependent results stay model-conditional (CM-13) and
the real heading-response experiment is what bounds the simulator. Split and calibrate by
world, never by image (consecutive seabed images overlap 50 %). `project_synthesis.md` §4 E2 /
E7, §7.6, §8.2. The old wording survives in `sssCLAUDE.md` #11, `simCLAUDE.md` NC #11, and
Perception / Aug Studio documents — stale lines listed in the 2026-10-20 report.

**CM-12 — The policy baseline is two-pass orthogonal, and tuned seriously.** Single-pass is a
strawman; a deliberately weakened baseline is detected instantly and sinks the comparison
(`project_synthesis.md` §7.3 ⚠, §8.6 ⚠, `sssCLAUDE.md` #13, `mcsCLAUDE.md` N10).

**CM-13 — Headline results are stated as model-conditional:** "In a calibrated simulation
environment…", never an unqualified empirical finding, the caveat leading the limitations
chapter rather than buried in it (`project_synthesis.md` §4.1 ⚠, `sssCLAUDE.md` #16,
`mcsCLAUDE.md` N10). The evidence architecture of `project_synthesis.md` §4 governs which
layer may support which claim; no layer is used above its evidential weight.

**CM-14 — Perception, control and AI iteration happen offline against recorded rosbags, never
in the water.** Field time is weather-gated and the scarcest resource; needing a field session
to test a change means the replay tooling has a gap (`project_synthesis.md` §8.6 ⚠,
`ctrlCLAUDE.md` N7, `sssCLAUDE.md` #14).

What "recorded" means in the tree differs by stream. A real run's **run bag** (v1.1) holds
navigation, commands and session plumbing, and **excludes** `/side_scan_sonar/*`,
`/sss_processor/*` and `/sss_ai/*` (`run_bag.py:52`). The sonar's record is the `.svlog`
and the GCS recording session. So:
- control iterates against run bags (`Replay_launch.py`, the log reviewer);
- perception and AI iterate against **GCS sessions**, with `blueboat-perception-offline`,
  which reproduces live records byte for byte;
- `.svlog` files are replayed through the GCS window, whose Run AI uses Perception's core.

`svlog_to_rosbag.py` converts a `.svlog` to a bag, but no tool joins a run bag and a sonar
recording into one replay. A run bag can drive the **simulated** sonar (2026-10-27): the
replay publishes the boat pose. Neither MCS nor the replay starts that sonar (MCS owner
decision, 2026-10-27); since 2026-11-02 the **GCS** does, at START with *Sonar: Simulation*,
when the process table shows a bag replay on a world folder and no `/side_scan_sonar`
(`ros2 launch blueboat_sss_sim sss_sim_launch.py world_dir:=<world> with_mavros_shim:=false
auto_ping:=false`, `blueboat_gcs/ros/sonar_source.py`). Before that, a session recorded
during a replay held only the replayed MAVLink. The recorded
position and full attitude then render the world's seabed. That is real motion with a simulated sensor, evidence about the simulator
under that motion, never a field sonar result.

**CM-15 — Safe shutdown precedes terminating a launch:** publish `default` on
`/blueboat/input_str`, confirm a matched subscriber, wait for the `/blueboat/param_mode` echo,
flush, then terminate (MCS Stop Mission, labelled **Turn Off Connection** in a real-robot
run session, where a run still active is stopped first on `/blueboat/run_command`); killing
the launch first can leave the motors in override (`mcsCLAUDE.md` N1). The echo wait outlasts
`param_set`'s own sequence bound (25 s, 2026-10-23), and an unconfirmed `default` is the
operator's call to terminate, never a timer's: torn down mid-sequence, the autopilot keeps
SERVO1/3 on passthrough and its GCS sysid on mavros, and no other ground station can drive it. `ctrlCLAUDE.md` N5 is the control-stack half: the default servo mapping
is restored before shutdown and a SERVO function is never set to `0`. Since 2026-09-04
`robot_interface` and `param_set` also attempt that restore themselves in independent bounded
`try/finally` blocks — best effort (a launch teardown SIGINTs the whole process group, mavros
included), never a replacement for the station's sequence. **Corollary (2026-09-04): stopping
the motors, releasing the servo mapping and ending the mission are three separate operator
actions, never re-nested.** The E-STOP publishes `stop` — `robot_interface` zeroes thrust,
closes the `enable_motors` gate, disarms and **latches** until an explicit `enable` — and
touches neither the parameter mode nor the launch. Leaving override *transfers* authority (the
RC channels go back to whatever else transmits), so it can never be part of a panic button
(`mcsCLAUDE.md` N1b table; `ctrlCLAUDE.md` N4b latch).

**CM-16 — `enable_motors` gates all thruster output, and a closed gate holds neutral.** No
**thrust-bearing** PWM reaches the motors unless `enable_motors:=True`; every
`/mavros/rc/override` write outside the gate carries neutral 1500/1500 or channel release
(`ctrlCLAUDE.md` N4). **Reworded 2026-09-04** from "no code path writes to
`/mavros/rc/override` around that gate", because writing *nothing* was unsafe:
`robot_interface` requests `override` unconditionally at init, so `SERVO1/3_FUNCTION` sit on
RCIN passthrough and the ESCs follow RC channels 1 and 3 from any transmitter, with nothing
feeding ArduPilot's `RC_OVERRIDE_TIME` to keep those channels ours — a silent gate left the
motors drivable by a hand transmitter, a QGC joystick or an RC failsafe. The gate now streams
true neutral (0 N is an exact knot of the calibration table) while in override, pinning the
channels and feeding the watchdog.

---

## 6. Discrepancies against `project_synthesis.md`

**Moved to `.claude/synthesis-discrepancies.md`** (D1–D10: where the modules and
`project_synthesis.md` disagree, and which source to trust). Read it before relying on a
`project_synthesis.md` §5 statement about what is built.

---

## 7. Where the detail lives

The root describes relationships; each submodule stays authoritative for its internals and its
backlog — do not duplicate either here.

| Topic | Read |
|---|---|
| Scope, evidence architecture, headline claim phrasing, design rules | `project_synthesis.md` §§1–4, §8 (project files) |
| Experiment design, target classes, metrics, campaign planning | `project_synthesis.md` §7–§8.4 and `target_families_and_surrogates.md` — **out of scope for this file** |
| Controllers, guidance law, thrust path, trajectory library, MAVROS bridge | `BlueBoat-Control/.claude/CLAUDE.md` · no `TODO.md` since the v1.0 freeze (post-v1.0 items go to the requesting module's `TODO.md`). Deeper, in the package: `blueboat_control/src/TRAJECTORY_SYSTEM.md`, `FIELD_TUNING.md` |
| Sonar driver, processor, `.svlog` format, GCS internals, measured acquisition settings | `BlueBoat-SSS/.claude/CLAUDE.md` · open items `BlueBoat-SSS/.claude/TODO.md` |
| Acoustic model, world generation, mission bundles, renderer seams, smoke test | `BlueBoat-SSS-Sim/.claude/CLAUDE.md` · open items `BlueBoat-SSS-Sim/.claude/TODO.md`. The ray-cast sensor: `README.md` (use, range advice), `blueboat_sss_sim/docs/engineering/raycast_assessment.md` (status) |
| Station threading model, map and georeferencing, Pattern Designer | `BlueBoat-MCS/.claude/CLAUDE.md` · no `TODO.md` since the v1.0 freeze |
| Augmentation families, intensity-domain policy, reproducibility contract, extension contract, release gates (the module is **optional**) | `SSS-Dataset-Aug-Studio/.claude/CLAUDE.md` · open items `SSS-Dataset-Aug-Studio/.claude/TODO.md` |
| Live path update (the Replanner's entry point): contract, refusal codes, tests, first water test | `BlueBoat-Control/docs/PATH_UPDATE_INTERFACE.md`, `PATH_UPDATE_DESIGN.md`, `PATH_UPDATE_REPORT.md`, `PATH_UPDATE_REAL_WATER_TEST.md`; requests `docs/REQUESTS.md` |
| Connection-loss guardian: design, setup, test ladder | `link_guardian/README.md` (superproject) |
| Planned chain (Belief, Replanner, Evaluation) | `project_synthesis.md` §5.1–§5.2, §7.3, §8.1–§8.4 — no module exists |
| Detector pipeline, detector input (fixed mapping, near-range mask, turn flags), YOLO over tiles, tile datasets / training / evaluation tools, image records, dataset mode, offline = live | `BlueBoat-Perception/.claude/CLAUDE.md` · open items `BlueBoat-Perception/.claude/TODO.md`; evidence `docs/PREPROCESSING_STUDY.md`, `docs/LIVE_CHECKS.md` |
| Per-module test / lint / smoke gates, exact commands, what survives a fresh clone | skill `module-gates` (`.claude/skills/module-gates/SKILL.md`) |
| Dated owner orders that opened the frozen Control / MCS (2026-09-28 to 2026-10-16) | skill `git-history` |
| MAVROS boundary table, FCU endpoint, other served interfaces (§4.4, §4.7 detail) | skill `interface-inventory` |

**CLAUDE.md map — read the relevant ones before touching a directory.** A nested `CLAUDE.md`
loads by itself only when the Read tool opens a file in its directory; Bash, Grep and Glob
access never trigger it. So before changing anything under one of these paths (or scripting a
change there), Read its `CLAUDE.md` first:
- module roots: `<module>/.claude/CLAUDE.md`, all six submodules;
- `BlueBoat-Control/`: `blueboat_control/src/` (controller and thrust-path evidence),
  `blueboat_description/`, `log_reviewer/`;
- `BlueBoat-SSS/`: `blueboat_sss/blueboat_gcs/` (GCS);
- `BlueBoat-SSS-Sim/`: `blueboat_sss_sim/blueboat_sss_sim/builder/` (World Builder) and
  `…/sea/` (sea state);
- `BlueBoat-MCS/`: `mcs/designer/` (Pattern Designer).

Each nested file holds that directory's rules and evidence; its module root file states what
moved where.

Where a module's `CLAUDE.md` marks its repo layout UNCERTAIN or its GCS/controller sections
HISTORICAL, the repository outranks the document. Prefer reading a file to trusting a
description of it.

**The two reviews.** `project_review.md` and `sim_review.md` (superproject root, untracked) are
the dated review documents; ~20 source files and several `CLAUDE.md`/`TODO.md` sections cite
them by section — load-bearing, not archive. `sim_review.md` **Part 7** records that its Part 6
update plan was implemented on 2026-09-18, what gates each item, and the two of its own
numbers that did not survive being measured properly. Its measurement chain,
`~/ros2_ws/sim_review_work/`, is **outside every repository** — this machine only, in no
clone. ⚠ **Provenance, not a gate:** its scripts and sonar profiles are frozen at the
pre-2026-09-18 constants, so re-running them against today's model shows large deltas that are
*the fix, not a regression*; the gates are the per-module suites (skill `module-gates`).
