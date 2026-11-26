# Open items across the project

*Collected 2026-11-18 (session 11) from every repository, handoff and report. Nothing was closed by this
collection: an item marked **done** is done in the code or the tree, with the evidence named. "Source" is where
the item is written; `SA` = `~/ros2_ws/sim_runs/sim_acceptance/`. Module backlogs stay in each module's
`.claude/TODO.md` (one row per module below, with its blocking items). Update a row in place when it changes.*

## 1. Blocking the next phase (owner decisions first)

| Id | Module | Item | Status | Source |
|---|---|---|---|---|
| FRZ-1 | all | Create the tag `sim-freeze-v1.0-2026-11-18` in every module and the superproject, and push it; sign `freeze_decision.md` | **open** (no tag exists on 2026-11-18; the signature line is blank) | `SA/freeze_decision.md` §6.4 |
| FRZ-2 | Sim, Control | Rebuild once so the build stamp names the head (`colcon build --packages-select blueboat_sss_sim blueboat_control blueboat_description`), then `provenance --check` must give `cc29e08780aac4cd` | open for the owner after committing (session 11 saw the install equal to the source, digest `cc29e08780aac4cd`, built 2026-11-18T04:54Z) | `freeze_decision.md` §6.2–6.3 |
| FRZ-3 | superproject | Add session 10's register entries to `split_register.yaml` | **done** by session 11 (15 entries, 5 roles HELD-OUT → SEEN, 2 notes; the before-copy is `SA/11_cleanup/split_register.before_session_11.yaml`) | `freeze_decision.md` §6.1 |
| R-3 | Sim ← Control, Replanner | The simulator's `full_mission_launch.py` passes `path_source`, so a built world can host a replanner-owned run | **done 2026-11-18** (session 13, owner order, before the freeze tag): launch argument `path_source` (`mission` default \| `replanner`) in the launch's own `master_control` parameters, as `Sim_launch.py`; launch files are outside the code digest (`cc29e08780aac4cd` unchanged, source and install); Sim smoke 559 / 0 / 0; Control gates green (`mc_harness --compare HEAD` 23/23 bit-identical, `--replanner` all passed); recorded in `SIM_VALIDITY_CONDITIONS.md` §7 and `freeze_decision.md` §6 | Control `docs/REQUESTS.md` R-3; `~/ros2_ws/sim_runs/replanner/handoff_13_R-3.md` |
| PER-LBL-1 | Perception | Dataset labels took the shadow end as the larger of the flat-floor tip and the contact's `shadow_bins` (5–35 bins too long). `SIM_VALIDITY_CONDITIONS.md` §5.5 says labels come from the rendered picture and the world metadata, never from a contact | **done 2026-11-18** (uncommitted): `core/sim_labels.py` `ping_object_bins` ends the shadow at the flat-floor tip and takes the height without terrain from the sensor's `altitude_m`; `shadow_bins` only reported. Tests 230 pass / 28 skip (`tests/test_sim_labels_shadow.py`). On the C2 mission against 05's picture shadow ends: +9.1 / +35.2 bins → +9.1 / +14.4 (concrete / mooring block); 15 % of 2951 contacts shorten by > 2 bins, none lengthen. Remaining: the flat tip still ends 9–14 bins past the picture's half-level crossing; contacts still select objects and the `visible` flag. Was open (found by session 11: `core/sim_labels.py:421-423` shadow end, `:557` visibility; documented at `:41-47`, `:63`) | this file; freeze card §4 |
| 02-CR2 | Perception | Class map `core/data/yolo_classes_v1.json` still lists the 29 old World Builder classes; object set version 2 has 11 | open | `SA/02_world_builder/handoff_02.md` change request 2 |
| 02-CR3 | Replanner | `CLASS_MAP` in `emulator_node.py:51` names deleted classes (`pipe_pvc`, `mesh_crate`) | open | `handoff_02.md` change request 3 |
| CR-PER-2 | Perception | Place convention-3 detections from the transducers' point | **done and confirmed live** in Perception `0d55d76` (2026-11-15: `core/geometry.py:76-100`, `core/image.py:96-101`); re-checked by session 12 (`~/ros2_ws/sim_runs/perception/handoff_12_cr_per_2.md`: grids equal the GCS's bit for bit on 34/34 pictures, A1 gap 0.763 → 0.073 m, 222 pass / 28 skip). Re-run before the pipeline test as ordered (2026-11-18: 230 pass / 28 skip on the working tree) and **checked in Gazebo** (session 13): Perception's grids and Belief's core place the same ping sample within median 0.015 m, max 0.057 m (55 samples, six objects, straight legs; both apply −0.345 m), `pipeline_dev/pipe13_c2_nominal_s2/cr_per_2_placement.json`. The 05 report §10.6, `freeze_decision.md` §6.5 and `EVIDENCE_REPORT.md` still call it open (records, kept verbatim) | `SA/06_sss/handoff_06.md:216` |
| CR-PER-1 | Perception | Labels use the rendered transducer pose | **done** (Perception TODO; `handoff_perception.md:159`, confirmed by a run) | `handoff_06.md:227` |
| CR-REP-1 | Replanner | Re-run the 690 + 150 dev-loop missions on Belief's core with the fore/aft arm | open | `SA/06_sss_followup_belief/handoff_belief.md:197`; Replanner TODO:60 |
| PIPE-1 | all | The whole chain in Gazebo (sonar → Perception → Belief → Replanner → Control) | **first run done 2026-11-18** (session 13, a development check, never a result): campaign world `e4_example-nominal-s2`, production ray-cast, MPC, `harbour_chop`, `path_source:=replanner`, the Replanner on `time_source: ros`; master_control held until the first path, 1 request accepted, path flown to `end_reached`, Replanner `done`, no stale input through the render holds, clean CM-15 end. Open: C4 (a decision record with `source: stamp`), the stop test (L-G2…L-G4) | Replanner `LOCAL_CHECKLIST.md` L-G1; `~/ros2_ws/sim_runs/pipeline_dev/pipe13_c2_nominal_s2/RUN_NOTES.md` |
| ICAROB-E2 | owner | Re-run ICAROB Experiment 2 on the frozen simulator | open | `freeze_decision.md` §6.5 |
| V11-1 | Sim (owner) | Sign `SA/sim_v1.1_worldgen_decision.md` and `SA/sim_v1.2_worldgen_decision.md` (both parts of v1.1), commit the v1.1 tree and `blueboat_harbour_population`, create the tag `sim-v1.1-worldgen-2026-11-21`; then rebuild (`colcon build --packages-select blueboat_sss_sim blueboat_harbour_population`) so that `provenance --check` gives `ed13b523d1be4f07` | **open** | `~/ros2_ws/sim_runs/worldgen_v11/HANDOFF_14.md` |
| V11-2 | owner | Decide the harbour split (`blueboat_harbour_population/data/splits.yaml`: Port Gardner and Marseille unassigned) and confirm the seed ranges before dataset recording | open | same |
| V11-3 | Perception | Dataset labels from mission-like worlds: use `role`, `nominal_target`, `effectively_buried` and `params.on_mud` / `altitude_m` / `in_envelope` / `group_id` / `stand_in_for` (today `classes_for` makes a class of every object type, structures and debris included) | open (change request; no neighbour edited) | same |
| E4/E5 | owner | Campaign design against the C2 throughput (about 44 missions of 20 simulated minutes a day) | open | 05 report §10.6 |
| PNG-1 | owner, Control | Pinger field calibration: latency, y sign, mount yaw, lever arm and noise are provisional (no still-pinger data in the Makurazaki runs); check the Water Linked locator type and depth source (locator z read a constant 0.19 m) | **open**, mandatory before trusting the filtered pinger | Control `docs/PINGER_FIELD_CALIBRATION.md`, `docs/PINGER_FILTER_FINDINGS.md` |
| PNG-2 | GCS (BlueBoat-SSS) | Show the filtered and the legacy pinger like the station (subscribe `/blueboat/pinger/estimate` for the filtered world position and `/blueboat/pinger/legacy_body`); today `pinger_listener` draws `/blueboat/pinger_coordinates`, which is now the filtered vector | open (change request; no neighbour edited, CM-3) | Control `.claude/interface.md` §2.7 |
| PNG-4 | owner | Rebuild the shared install (`cd ~/ros2_ws && colcon build --packages-select blueboat_control`) before any real launch: the pinger work was built and tested in a private overlay only; the shared install still has v1.1's `robot_interface` / `uwgps_log` and no `pinger_estimator` (the station's launch fails to start it otherwise) | open | 2026-11-24 session |
| PNG-3 | Control | A START whose new session file fails to parse re-serves the previous run's path (`path_generation` keeps the old trajectory) | open (found 2026-11-24, not fixed: out of the order's scope) | `docs/PINGER_FILTER_FINDINGS.md` §8 |
| SWB-1 | link guardian, MCS | Safety way back (2026-11-25, owner order): upload the new `link_guardian.lua` to the autopilot, then the bench and water test `link_guardian/README.md` §7 step 5. Tested offline only (`link_guardian/test/`: the real script on a mocked autopilot, `guardian.py` on a fake MAVROS; MCS smoke `safety way back ok`); the mission upload through the real MAVROS and ArduPilot's GUIDED following of it have not run | open | `link_guardian/README.md` §2, §7 |
| GH-1 | link guardian, MCS | Guardian Home and Set Home (2026-11-26, owner order): upload the new `link_guardian.lua` (adds `LGRD_HOME`; param table size 18 → 20), then `link_guardian/README.md` §7 step 6 on the boat. Offline only so far (`lua_harness.py` 12 scenarios, `test_guardian_safety.py`, MCS smoke). To confirm on the real autopilot: `ahrs:set_home` / `get_home` from Lua on this firmware, and that Rover's GUIDED arrival (`WP_RADIUS`) brings the boat within `WP_RADIUS` + 0.5 m of the Home before LOITER | open | `link_guardian/README.md` §2, §7 |

## 2. Change requests of the acceptance round (CR-…)

| Id | To | Item | Status (evidence) | Source |
|---|---|---|---|---|
| CR-SSS-1 | SSS processor | `TRANSDUCER_X_OFFSET_M` = −0.345 | **done** (installed processor line 163) | `SA/01_sonar_physics/handoff_01.md:1075` |
| CR-SSS-2 | SSS GCS | Apply the fore/aft arm in georeferencing | **done** (SSS TODO:19) | `handoff_01.md:1076` |
| CR-BEL-1 | Belief | Place pings from the transducers' point | **done** (Belief `4827623`, D-12, smoke [23]; installed package equals the source, checked 2026-11-18) | `handoff_01.md:1077` |
| CR-ROOT-1/2 | superproject | Interface-contract §4.3/§4.6 and D6 text on the arm | **done** (committed 2026-11-17; the "Perception does not yet" lines corrected 2026-11-18) | `handoff_06.md:228`, `handoff_belief.md:169` |
| CR-SIM-1 | Sim docs | Out-of-date lines | done (`handoff_06.md:229`) | — |
| CR-OWN-1 | owner | Measure the lever arm (reciprocal passes over a point target) and weigh the boat; fill `owner_measurements.yaml` | **open** (the arm −0.345 m is adopted from the simulator, not measured) | `handoff_01.md:1082`; SSS TODO:26; Perception TODO:30; `SA/owner_measurements.yaml:50` |
| CR-OWN-2 | owner | Rebuild `~/ros2_ws/install`; check L-9 on the boat | rebuild **done** (installed Belief, Perception and processor equal their sources); the L-9 real-boat check **open** | `handoff_belief.md:198` |
| CR-02-1 | Sim catalogue | Flooded shells for hollow classes | done (session 02 design note) | `handoff_01.md:1079` |
| CR-03-1 | Sim | Surface roughness from the sea state | done, opt-in | `SA/03_sea_state/handoff_03.md:62` |
| CR-03-2 | Control | Closed-loop spread between controllers | answered: a stated limitation (`SA/04c_closed_loop/`) | `handoff_03.md:139` |
| CR-03-3 | MCS | Choose a sea situation file and `thrust_gain` | **done** (MCS `244c0bc`) | `SA/09b_mcs/handoff_09b.md` |
| CR-03-4 | superproject tools | Record `sim_config`, `thrust_gain`, schedule SHA in every run record | **done** (`tools/sim_record/record_run.py:17,112-115`, commit `44c938b`; `handoff_09b.md:86` "untouched" is older text) | `SA/09a_record_run/handoff_09a.md` |
| CR-03-5 | Sim | Stale poses under the render hold | **done** (fixed in 02b, committed in Sim `1c37bed`); Sim TODO:1418 still says "cause not isolated" (frozen backlog) | `SA/02b_raycast_fix/handoff_02b.md:166` |
| CR-05-1 | session 05 | B4 exclusion and B6 profile | used in 05 | `handoff_01.md:1081` |
| CR-05-2 | session 05 | Report I5 as adopted; no double arm | done (05 report:47, 697) | `handoff_06.md:230` |
| [M0] | Sim | 4 seabed cells of 7359 next to one debris object have no owner object (one test world) | **accepted, will not be fixed** (owner) | freeze card §3; 05 report §10.6 |

## 3. Requests between modules

| Id | Module | Item | Status | Source |
|---|---|---|---|---|
| R-1 | MCS ← Control | MCS "Replanner mode" (survey-mission launch) | open (no code in MCS) | Control `docs/REQUESTS.md:9`, TODO:10 |
| R-2 | Replanner | A new module | done (the module exists) | Control `REQUESTS.md:51` |
| R-3 | Sim ← Control | `path_source` in `full_mission_launch.py` | **done 2026-11-18**, see §1 | Control `REQUESTS.md:69` |
| R-4 | superproject | Root `CLAUDE.md` rows | applied 2026-10-19 | Control `REQUESTS.md:79` |
| R-5 | MCS/GCS ← Control | Optional path visualisation topic | open, optional | Control `REQUESTS.md:119` |
| R-6 | Sim ← Control | Forward `sim_config` | **done** (launch args, session 03) | Control `REQUESTS.md:142` |
| R-7 | Sim ← Control | `odom_gz` fallbacks | **done** (`sea_state_node.py:240,293`) | Control `REQUESTS.md:160` |
| R-8 | Control ← Sim | Heave / roll / pitch | applied by 04b (Control `b86561f`); leftovers: Coriolis A44/A55 lost, sway added mass 14 vs 133 kg | Control `REQUESTS.md:176-221`; Sim TODO:1396 |
| R-9, R-10 | Control | Disturbance leftovers; no further field measurement | informational; standing rule | Control `REQUESTS.md:222,239` |
| Bel R-1 | Belief ← Perception | A calibrated detector and its base rate | **open, [P0]**: `p_exists` is not a probability until it exists | Belief `docs/REQUESTS.md`; TODO [P0] |
| Bel R-2…R-7 | Belief ← others | Shadow field; MCS `record_inputs`; Control origin latch and zero stamps; unknown-altitude flag; SimGps status gate; replay tooling | open (see Belief `docs/REQUESTS.md`) | Belief `docs/REQUESTS.md` |
| Bel R-8 | Belief ← Perception | Detections from the transducers' point | **done** (= CR-PER-2) | Belief `docs/REQUESTS.md:77` |
| Per R-3 | Aug Studio ← Perception | Intensity mapping for `identity` datasets | open (for `identity` only) | Perception `docs/REQUESTS.md:13` |
| Per R-4, R-5 | — | — | applied | Perception `docs/REQUESTS.md:48,70` |
| RQ-1 | Replanner | = Control R-3, plus the node's clock in simulation (CLK-1) | **done 2026-11-18** | Replanner `docs/REQUESTS.md` |
| CLK-1 | Replanner | The node measured freshness, time-outs and record times on the wall clock, while Control's progress runs on `/clock` (slowed by the ray-cast, paused while a slow ping renders): progress looked stale and no path was sent | **done 2026-11-18**: node parameter `time_source` (`wall` default \| `ros`) and launch arguments `use_sim_time`, `time_source`; in Gazebo `use_sim_time:=true time_source:=ros`. With `wall` every record and published payload is byte-identical to the node of `2f84a46` (gate [26]); gate 294 / 0 / 0 in three environments | Replanner MATH §11.3, `LOCAL_CHECKLIST.md` L-G |
| RQ-6 | owner ← Replanner | The class → aspect-family map | open | Replanner `docs/REQUESTS.md`; HANDOVER §4 |
| RQ-8 | Replanner | Confirmation rule in `model_params_json` | open, low priority | Replanner `docs/REQUESTS.md` |

## 4. Items from the acceptance handoffs

| Id | Item | Status | Source |
|---|---|---|---|
| 01-O1 | Corner path on sand (+28 dB for an upright face) untested by data; needs a bracket key | open (P1) | `handoff_01.md` §5.1 |
| 01-O2 | Beam main and side lobes not measurable on the corpus; elevation pattern and tilt not re-examined | open (P1) | 〃 |
| 01-O3 | Thin plastic shell's shadow is a wide bracket | bracket profiles exist (P1) | 〃 |
| 01-O4 | V5 remainder: rubber, steel-belted tyre wall, rope constants not found | open, paper requests (P2) | 〃 |
| 01-O5 | Shadow fill is the measured 18 dB stand-in; volume reverberation not modelled | stated (P2) | 〃 |
| 01-O6 | Face waviness 0.5° / 0.10 m assumed | open (P2) | 〃 |
| 01-O7 | Port brighter than starboard by about 1 dB on every harbour file; not modelled | documented (P2) | 〃 |
| 01-O8 | Dark rows of harbour-live in a large shadow; stripes at 39 m (now refused) | not investigated (P1) | 〃 |
| 01-O10 | Scatterer-mediated corner path not modelled | open (P2) | 〃 |
| 01-O13 | Stand-in shadow depth drifts with range | open (P2) | 〃 |
| 01-O14 | Echo-path reselection on most pings in clutter | open (P2) | 〃 |
| 01-O15 | V3 away from the flash: ray-cast and reference differ by 4–11 dB far under the peak | open | 〃 |
| 01-O16 | Live run: one 470 ms gap at start-up, 99.90 % of nominal pings | open | 〃 |
| 01-PAPER | Paper requests (polypropylene, rubber at 0.2–1 MHz, Francois & Garrison) | open | `handoff_01.md` §5.3 |
| 03-OPEN | Pitch inertia; a harbour wave and wind measurement; no FIT roll/pitch reference at 25 Hz; sway at the real draft; `parse_urdf` mass 16.01 vs 16.15 kg | open (frozen simulator: future version) | `handoff_03.md:139-170`; Sim TODO:1394-1427 |
| 04-OWN | 0-byte `.npy` logs and poslogs left in the Trash | owner item | `SA/04_control/handoff_04.md:233` |
| 04b-MCS | MCS empty-world runs use `standalone`, which needs an MCS order | open | `SA/04b_control_r8/handoff_04b.md:255` |
| 04c-STAT | Amendment to the statistic definition (exclude 2 m before each corner) not applied | open | `handoff_04c.md:142-180` |
| 09b-DOC | MCS designer, user guide and SEA STATE box text not updated for 09b | open | `handoff_09b.md:83-86` |
| 05-DEF | 05 §10.6 deferred, besides the rows above: label rule on rising seabeds; minimum-signal rule for objects with no trace; refit of the fixed grey mapping; detector training, calibration and the sim-to-real test (Perception) · aspect atlas at both bracket ends instead of the placeholder windows, `v_suite/atlas/atlas_half_widths.json` (Replanner) · C5 contact range and shadow end; V9 convergence on wire meshes; near-range level at 5–8 m; a sea with the harbour's roll and one with larger waves (simulator, future version) · plant refit in closed loop; Gazebo's sway–yaw coupling (Control) · a stale replay test in the SSS suite (five failures with the field drive mounted) · session 02's R5 lower-end check names a deleted class; session 04's run metric truncates long routes (evidence scripts) | open | `SA/05_report/SIM_acceptance_report_2026-11-18.md` §10.6 |
| 05-S1…S27 | Open amendment suggestions to the frozen criteria (verdict rule, V9 half-width definition, B1 wording and band, B3/B4 windows, B5 seeds and speed definition, B6/G0, R6 rubber value, R1 window, C3 wording, C1 on E4 worlds, I5, C5 contacts, R3 "2 × field-matched", R5 lower end, R4 effect) | open, for a future criteria version only | 05 report §12.2 |
| 10-REG | `10_evidence/register_proposals.yaml` does not parse as YAML (unquoted colon in the makurazaki note); kept verbatim, merged through a quoted reading | noted | session 11 |

## 5. Module backlogs (`.claude/TODO.md`)

| Module | Open | Blocking / P0–P1 items |
|---|---|---|
| BlueBoat-SSS-Sim | 3 [P0], 26 [P1] marks, 10 open boxes; **frozen**: candidates for a future version only | — (no item is worked on in v1.0) |
| BlueBoat-SSS | 45 open boxes | CR-OWN-1 (measured arm); A2's residual 0.6 m unexplained; a per-session arm on the real boat |
| BlueBoat-Perception | 26 open boxes | the 2 dB visibility threshold and the merge rule on held-out worlds; 02-CR2; the ray-cast label offsets (+0.10 / +0.04 m) "check before training on ray-cast datasets" |
| BlueBoat-Belief | [P0] ×2 | detector calibration (`p_exists` not a probability); a run with a real detector |
| BlueBoat-Replanner | 25 open boxes, [P0] ×2 | go-ahead for the ROS check on the new node code; the owner's open decisions (class → aspect family); Control's real path update live; Gazebo missions L-G2…L-G4 (L-G1 done 2026-11-18); 0.5 m/s in Gazebo; real-water authority |
| BlueBoat-Control | 10 open boxes | first supervised on-water test; R-1; R-5; real-boat MPC with path updates; yaw-coherence check; real MPC model ≠ identified plant; 5 s reference stall in `from_yaml` runs; PID at 1.0 m/s; stale MPC iterate; `uvr_mpc` unwrap |
| SSS-Dataset-Aug-Studio | 8 open boxes | mostly blocked on field data |
| BlueBoat-MCS | no `TODO.md` (frozen v1.0) | R-1, 04b-MCS, 09b-DOC above |
