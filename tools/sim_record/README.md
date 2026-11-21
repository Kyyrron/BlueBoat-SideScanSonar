# sim_record — run and record a simulated survey from the command line

One command does what the operator does by hand with the two apps:

1. **MCS** launches a Gazebo world with a survey path and a sonar model;
2. the **GCS** runs its pipeline, START, Record, and writes a recording session (`.svlog`,
   seabed images, mosaic, waterfall, `metadata.json`).

Nothing is re-implemented: MCS's own launcher and the GCS's own window run offscreen and are
driven through the same signals as their buttons. No package is modified.

## Before a run

- One run at a time. Nothing else may be running (no simulation, no GCS); the tool refuses and
  lists what it found.
- The installed simulator must match its source tree. Check:
  `python3 -m blueboat_sss_sim.core.provenance --check`. If it fails, rebuild:
  ```bash
  cd ~/ros2_ws && rm -rf build/blueboat_sss_sim install/blueboat_sss_sim && colcon build --packages-select blueboat_sss_sim
  ```
- For a result run, stay inside [`SIM_VALIDITY_CONDITIONS.md`](../../SIM_VALIDITY_CONDITIONS.md)
  (sensor `harbour_fast`, 20 m range, 4.5–7 m altitude, allowed seas and controllers).
- A world folder (`~/worlds/<path>/<world>/` with `metadata.yaml`) and an MCS trajectory
  (name in `~/.config/blueboat_mcs/trajectories/`, or a file path).

## Run

```bash
cd ~/ros2_ws/src/BlueBoat-SideScanSonar
python3 tools/sim_record/record_run.py \
    --world ~/worlds/<path>/<world> --trajectory <MCS trajectory name> \
    --sensor harbour_fast --name my_run --rtf 2.0
```

No sourced shell and no display needed: the drivers source `~/ros2_ws/env.sh` themselves.
Ctrl-C ends the run cleanly. Exit code 0 = `completed` or `stop_after`; 1 otherwise.

## Options

| Option | Default | Meaning |
|---|---|---|
| `--world` | required | World folder |
| `--trajectory` | required | MCS trajectory name or file (GPS-anchored) |
| `--sensor` | required | `geometric`, a profile file, or a ray-cast short name: `harbour_fast`, `harbour_live`, `fast`, `live`, `default` (= `config/raycast_<name>_sonar.yaml`, installed copy first) |
| `--name` | required | Run name: the folder under `--out` (must not exist) |
| `--out` | `~/ros2_ws/sim_runs/recorded_runs` | Where run folders go |
| `--rtf` | 1.0 | Slow-down (Gazebo real-time factor). x2 for the fast variants, x0.5 for the others |
| `--controller` | `MPC` | Controller |
| `--range-m` | 0 (profile's) | Sonar range at the start, metres |
| `--range-at S:R` | — | Change the range to `R` m at `S` m along the path (repeatable) |
| `--waves`, `--waves-from` | calm, 0 | Wave preset of the MCS dialog (e.g. `harbour_chop`), direction it comes from (compass °) |
| `--current`, `--current-from` | none, 0 | Current preset (e.g. `weak`, `moderate`), direction |
| `--sea-seed` | 7 | Sea-state seed |
| `--sonar-seed` | 0 (fresh, logged) | Sensor-noise seed |
| `--record-from-m S` | 0 | Boat leaves first; Record ON `S` m along the path (after a lead-in) |
| `--stop-after-s` | 0 (off) | Stop this many simulated seconds after the boat leaves |
| `--max-wall-min` | 120 | Wall-clock limit, minutes |
| `--session-name` | — | Rename the session folder |
| `--private-data-root` | off | Write the session under the run folder instead of the GCS data root |
| `--ground-truth-bag` | off | Also record the simulator's ground truth (see below) |
| `--allow-stale` | off | Run even if the installed simulator is stale |
| `--extra K:=V ...` | — | Extra launch arguments (`headless:=true` is always added) |

## What happens

1. **Checks** (see *Before a run*).
2. **Launch.** MCS's launcher starts the world with the chosen sonar, controller, slow-down
   and sea. The path is not deployed yet, so the boat holds at the origin.
3. **GCS**, once the sonar is ready: pipeline, START, then Record ON when pings flow.
4. **Deploy.** The path is written in the world frame (MCS's own deploy); the boat leaves. With
   `--record-from-m`, Record ON comes later instead.
5. **Range changes** at each `--range-at` (GCS "Apply range").
6. **End:** last waypoint reached (within 2.5 m, after at least 80 % of the path), a stall
   (90 simulated s without 1 m of progress), `--stop-after-s`, `--max-wall-min` or Ctrl-C.
   Then Record OFF, STOP, `default` on `/blueboat/input_str`, and MCS's own stop.
7. **Write** `run.json`.

## Output

| What | Where |
|---|---|
| Session | Where the GCS writes it: `~/ros2_ws/data/SSS_data/sessions/<stamp>/` (or under the run folder with `--private-data-root`); `recorder_run.json` = a copy of `run.json` |
| Run folder | `<out>/<name>/`: `run.json`, `run.log`, `mcs_launch.log`, `gcs_driver.log`, `gcs_summary.json`, `boat_track.csv`, `gpu_mem.csv`, `deployed_path.yaml`, `ground_truth_bag/` (with `--ground-truth-bag`) |

`run.json` holds:

- `status`: `completed`, `stall`, `wall_limit`, `stop_after`, `aborted`, `launch_failed`
  (replanner runs also `no_first_path`, `replanner_<state>`);
- world, trajectory and sensor-profile digests, the provenance line, the session path;
- pings, seabed images, range changes applied, cross-track error while recording;
- wall time, GPU peak, counts of `render failed` / `behind the sim clock` / `process has died`
  in the launch log (the first two should be 0), and anything left running;
- the simulator's run configuration, copied from its run record
  (`~/.cache/blueboat_sss_sim/runs/<run_id>.json`): `sim_config`, `thrust_gain`,
  `sea_schedule` and its SHA-256, simulator commit and dirty flag, running digest;
- `control_code`: a SHA-256 over the installed `~/ros2_ws/install/blueboat_control`;
- `path_source`: `mission` or `replanner`.

A value the simulator did not record is `null`, never guessed.

## Ground truth for labelling

The GCS session holds no ground truth. `--ground-truth-bag` records
`/side_scan_sonar/ground_truth/contacts` and `/side_scan_sonar/ground_truth/sensor` into
`<out>/<name>/ground_truth_bag`. Make the labels offline afterwards:

```bash
ros2 run blueboat_perception blueboat-perception-offline <session> --dataset <name> \
    --world <world folder> --ground-truth-bag <out>/<name>/ground_truth_bag [--data-dir <root>]
```

`--data-dir` keeps the dataset out of `~/ros2_ws/data/Dataset_data`.

## Replanner-owned runs

`--extra path_source:=replanner`: Control holds the boat at the spawn pose until the
Replanner's first path. The MCS path is still deployed (the launch needs one) but not flown.

- The tool **does not start** Belief or the Replanner. Start them yourself, and call
  `/replanner/start`, after the log says "path deployed".
- The run ends on the Replanner's `/replanner/status`: `done` or `stopped_holding` →
  `completed`; `failed` or `run_ended` → `replanner_<state>`.
- No first path within 600 simulated s of the deploy → `no_first_path`.
- Progress is distance travelled (`boat_track.csv` column `travelled_m`); a stall is 90
  simulated s with less than 1 m travelled.
- `--range-at` and `--record-from-m` are refused (they are distances along the deployed path).

## Limits

- The boat spawns at the world origin heading east. A path whose first leg heads elsewhere
  starts with a wide swing: begin it with a lead-in and use `--record-from-m`.
- Keep the ray-cast range at 30 m or less on an 8 GB GPU (never above 40 m).
- It never kills a process it did not start. "process has died" lines at the end of the launch
  log are the normal teardown.

## Layout

| File | What |
|---|---|
| `record_run.py` | The command you run; coordinates the two drivers, writes `run.json` |
| `mcs_driver.py` | MCS side: launch, deploy, stop (started by `record_run.py`) |
| `gcs_driver.py` | GCS side: pipeline, START, Record, range changes, end detection (started by `record_run.py`) |
