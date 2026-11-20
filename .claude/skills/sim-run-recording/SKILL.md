---
name: sim-run-recording
description: Run a simulated survey and record it as a GCS session from the command line, with no clicking — the MCS App's own launcher and the GCS App's own window driven offscreen (tools/sim_record). Use when asked to run, record or repeat a simulation run on a world with a survey path and a sonar model, to produce a session's .svlog / seabed images / mosaic for a comparison, or to change the sonar range along a path. Also lists what must be true before a run (the frozen simulator's identity check and validity envelope) and how to read its result.
---

# Recording a simulated run without the GUIs

`tools/sim_record/record_run.py` (superproject, not a submodule) does what the operator does by
hand: MCS launch → GCS pipeline → START → Record → path → Record OFF → STOP → safe shutdown. It
uses the station's `LaunchManager` and the GCS's `MainWindow` offscreen, so the session is a normal
GCS session. Full description: `tools/sim_record/README.md`.

```bash
cd ~/ros2_ws/src/BlueBoat-SideScanSonar
python3 tools/sim_record/record_run.py --world ~/worlds/<path>/<world> --trajectory <name> \
    --sensor harbour_fast --name <run> --rtf 2.0 [--range-m 18.4] [--range-at 74.8:39.0 ...] \
    [--record-from-m 12.1] [--session-name <folder name>] [--max-wall-min 120] [--ground-truth-bag]
```

`--ground-truth-bag` also records the simulator's ground truth beside the run, which the GCS session
does not hold; `ros2 run blueboat_perception blueboat-perception-offline <session> --dataset <name>
--world <world> --ground-truth-bag <run>/ground_truth_bag` then makes the labels (README, step 7) from the
world's metadata and the rendered transducer poses. Labels never come from a contact (conditions file §5.5;
PER-LBL-1, fixed 2026-11-18: no box extent comes from a contact). Align an offline rebuild on the seabed images'
`t_s` or the ground truth's `t_sim` (the offline waterfall ran 5.11 s behind on the C2 mission).

## Before a run

- **The simulator is frozen (2026-11-18).** A result run must be the frozen simulator inside the
  envelope of `SIM_VALIDITY_CONDITIONS.md` (superproject root): `python3 -m blueboat_sss_sim.core.provenance
  --check` gives code digest `cc29e08780aac4cd`; `--sensor harbour_fast` (the production profile), **20 m
  range** (no `--range-at` changes in a result run: those reproduce a real recording's range changes, for
  validation only), 1200 bins / 44.3 µs, altitude 4.5–7.0 m, MPC field gains or LoS, `sim_config:=field_equivalent`,
  seas `calm` / `harbour_chop` / `field_matched`. Record per run what the conditions file lists (world
  digest, profile, sea, controller, bracket ends, fouling, seeds).

- **Ask the owner first.** A run launches Gazebo; sessions never start one unrequested (memory:
  ask-before-live-sim-tests).
- Nothing else may be running (a simulation, the GCS App): the tool refuses and lists it.
- The installed simulator must be the source tree; the tool checks and refuses otherwise. Rebuild:
  `cd ~/ros2_ws && rm -rf build/blueboat_sss_sim install/blueboat_sss_sim && colcon build --packages-select blueboat_sss_sim`.
- The trajectory must be a GPS-anchored MCS file (`~/.config/blueboat_mcs/trajectories/<name>.yaml`)
  with at least one point inside the world.
- The boat spawns at the world origin **heading east**. If the path's first leg heads elsewhere,
  give the path a lead-in and pass `--record-from-m <lead-in length>`.

## Reading the result

- Exit 0 and `run.json` `status: completed` = the last waypoint was reached and the session closed.
- `run.json`: `gcs.pings`, `gcs.seabed_images`, `gcs.range_changes`, `gcs.cross_track_recorded_m`,
  `launch_log_counts` (`render_failed` and `behind_sim_clock` must be 0), `left_running` (must be
  empty), `provenance`.
- The session's `metadata.json["simulation"]` is the simulator's own run record (profile, world
  digest, seeds, acquisition, install = source).
- A try-out that must not touch the owner's data: `--private-data-root --stop-after-s 60`.

## Precedent

`~/ros2_ws/sim_runs/harbour_validation/` (2026-11-12): the real `toOptimize-harbourScan` path on a
world of the real harbour, harbour-fast and harbour-live, with the real run's range changes. Its
`README.md` has the exact commands, and `build_world.py` shows how to write an MCS path and build a
world folder from a script with the projects' own code.
