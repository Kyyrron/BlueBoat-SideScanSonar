# sim_record — run and record a simulated survey from the command line

One command does what the operator does with the two Apps: the **Mission Control Station** launches a
personalized world with a survey path and a Sonar model, the **GCS** runs its processing pipeline,
START, Record, and writes a recording session (`.svlog`, seabed images, mosaic, waterfall,
`metadata.json`). Nothing is re-implemented: the station's own `LaunchManager` and the GCS's own
window run offscreen and are driven through the signals their buttons emit. No package is modified.

```bash
cd ~/ros2_ws/src/BlueBoat-SideScanSonar
python3 tools/sim_record/record_run.py \
    --world ~/worlds/<path>/<world> --trajectory <MCS trajectory name> \
    --sensor harbour_fast --name my_run --rtf 2.0
```

It needs no sourced shell (the drivers source `~/ros2_ws/env.sh` themselves) and no display.

## What happens, in order

1. **Refusals.** It does not start when a simulation or a GCS is already running, when `<out>/<name>`
   exists, or when the installed simulator is not the source tree
   (`blueboat_sss_sim.core.provenance --check`; `--allow-stale` overrides).
2. **Launch** (`mcs_driver.py`): `LaunchManager.start` with the launch dialog's parameters — world,
   controller (`--controller`, MPC by default), Sonar model (`--sensor`), Slow-down (`--rtf`),
   Extra args (`headless:=true`, the start range, `--extra`). The Perception companion starts as in
   the App. The survey path is **not deployed yet**, so `path_generation` holds the boat at the origin.
3. **GCS** (`gcs_driver.py`), once the launch log says the sonar is ready: the processing pipeline,
   START, and when pings flow, Record ON.
4. **Deploy.** The station's own `io_yaml.deploy_mission` writes the path in the world frame (the
   world's GPS anchor is the georeference). The boat leaves; the whole path is in the recording.
   With `--record-from-m S` the order is reversed: the boat leaves first and Record ON comes `S`
   metres along the path (a path that begins with a lead-in).
5. **Range changes.** At each `--range-at S:R` the GCS's "Apply range" is used (ping off, set
   `range_length_mm`, ping on), `S` metres along the path.
6. **End.** Last waypoint reached (inside 2.5 m, at least 80 % of the path covered, 3 s more), or a
   stall (90 simulated seconds without 1 m of progress), `--stop-after-s`, `--max-wall-min`
   (120 by default) or Ctrl-C. Then Record OFF, STOP, `default` on `/blueboat/input_str`, and the
   station's own stop.
7. **Record.** `<out>/<name>/run.json`, also copied into the session as `recorder_run.json`.

**Ground truth (`--ground-truth-bag`, 2026-11-12).** The GCS does not record the simulator's ground
truth, so a session alone cannot be labelled. With this option the recorder also runs the command of
Perception's launch file, `ros2 bag record --use-sim-time --topics
/side_scan_sonar/ground_truth/contacts /side_scan_sonar/ground_truth/sensor`, into
`<out>/<name>/ground_truth_bag` from the moment the sonar is ready until the GCS has closed the
session. The labels are then made offline exactly as the live dataset mode makes them:

```bash
ros2 run blueboat_perception blueboat-perception-offline <session> --dataset <name> \
    --world <world folder> --ground-truth-bag <out>/<name>/ground_truth_bag [--data-dir <root>]
```

(`--data-dir` keeps the dataset out of `~/ros2_ws/data/Dataset_data`; the tool is not on the PATH,
hence `ros2 run`.)

## Where things go

| What | Where |
|---|---|
| The session | where the GCS writes it: `~/ros2_ws/data/SSS_data/sessions/<stamp>/` (`--session-name N` renames the folder; `--private-data-root` writes under the run folder instead) |
| Run folder | `--out` (default `~/ros2_ws/sim_runs/recorded_runs`) `/<name>/`: `run.json`, `run.log`, `mcs_launch.log` (the launch output), `gcs_driver.log` (the GCS console), `boat_track.csv`, `gpu_mem.csv`, `deployed_path.yaml`, and with `--ground-truth-bag` the folder `ground_truth_bag/` |

`run.json` holds: status (`completed`, `stall`, `wall_limit`, `stop_after`, `aborted`,
`launch_failed`), the world and profile digests, the provenance line, the session path, pings and
images, the range changes actually applied, the cross-track error of the boat against the path while
recording, wall time, GPU peak, the count of `render failed` / `behind the sim clock` lines in the
launch log, and anything left running.

## Sensors

`--sensor` is `geometric`, a profile file, or the short name of a ray-cast variant
(`config/raycast_<name>_sonar.yaml`, the installed copy first, as MCS picks it): `default`, `live`,
`fast`, `harbour_live`, `harbour_fast`. Slow-down: x2 for the fast variants, x0.5 for the others;
the simulation is paused while a ping renders, so no ping is lost either way. Keep the range at
30 m or below on the 8 GB GPU, 40 m at most.

## Limits

- The boat always spawns at the world origin heading east. A path whose first leg heads elsewhere
  is followed with a wide swing (5.8 m measured on a southward start): begin such a path with a
  lead-in and use `--record-from-m`.
- It never kills a process it did not start. `rviz2` exits at once in an offscreen launch; the launch
  log's "process has died" lines at the end are the normal SIGINT teardown.
- One run at a time: two simulations share the ROS graph.
