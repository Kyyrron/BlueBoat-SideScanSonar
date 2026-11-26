# BlueBoat — aspect-aware side-scan sonar survey

A BlueRobotics **BlueBoat** USV with two **Cerulean Omniscan 450 SS** side-scan sonars surveys
shallow enclosed water (harbours) on its own. It changes its path during the survey to look at
possible targets again from new headings ("aspect-aware" survey).

**All project software runs on the operator laptop**, in the ROS 2 workspace `~/ros2_ws`. The
laptop talks to the boat through the BlueBoat Base Station WiFi. The boat carries only its
hardware and its own firmware (ArduPilot / BlueOS, sonars, GPS, USBL). The one exception is the
connection-loss script in [`link_guardian/`](link_guardian/), copied onto the autopilot.

## How it works

```
sonar (seabed images + metadata) → Perception → Belief → Replanner → Control
```

| Step | What it does |
|---|---|
| Sonar | `BlueBoat-SSS` drives both sonars, builds seabed images, records `.svlog` files |
| Perception | Finds targets in the seabed images (`/sss_ai/detections`) |
| Belief | Turns pings + detections into a belief map (`BeliefGrid`) |
| Replanner | Reads only the belief map and sends a new path |
| Control | Follows the path (`/blueboat/update_path`) and drives the thrusters |

## Modules

Eight git submodules, plus three folders of this repository.

| Module | Role | State |
|---|---|---|
| [BlueBoat-Control](BlueBoat-Control/README.md) | Motion, pose, thrust, path following, live path update, run bags and replay; owns `blueboat_interfaces` | Frozen at `v1.0`, additions only |
| [BlueBoat-MCS](BlueBoat-MCS/README.md) | Mission Control Station: launch and watch missions (real or simulated), Pattern Designer, safe shutdown | Frozen at `v1.0`, additions only |
| [BlueBoat-SSS](BlueBoat-SSS/README.md) | Sonar driver and processor (`blueboat_sss`); GCS app: mosaic, recording, seabed images (`blueboat_gcs`) | In use |
| [BlueBoat-SSS-Sim](BlueBoat-SSS-Sim/README.md) | Gazebo worlds (World Builder), simulated sonar, sea state | **Frozen** (see Status) |
| [BlueBoat-Perception](BlueBoat-Perception/README.md) | The only detector; dataset mode for training data | Dummy detector by default; YOLO built, not trained |
| [BlueBoat-Belief](BlueBoat-Belief/README.md) | Belief map from pings and detections | Built; never run with a real detector |
| [BlueBoat-Replanner](BlueBoat-Replanner/README.md) | Aspect-aware replanner; generates every survey type | Built; run once in Gazebo; never on the boat |
| [SSS-Dataset-Aug-Studio](SSS-Dataset-Aug-Studio/README.md) | Offline augmentation of YOLO datasets | Optional; nothing depends on it |
| [hub/](hub/README.md) | Desktop app that starts, watches and stops every app | Built |
| [link_guardian/](link_guardian/README.md) | Brings the boat back if the laptop link is lost | Built; **tested on the boat** |
| [tools/sim_record/](tools/sim_record/README.md) | Runs and records a simulated survey from the command line | Built |
| Evaluation | Experiment evaluation | **Planned, not built** |

## First-time setup

Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic. The full dependency list (ROS packages, the two
source packages, acados for the MPC controller) is in
[BlueBoat-Control/README.md](BlueBoat-Control/README.md).

**1. Get the code** (with all submodules):

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone --recurse-submodules https://github.com/Kyyrron/BlueBoat-SideScanSonar.git
# already cloned without submodules:
cd BlueBoat-SideScanSonar && git submodule update --init --recursive
```

**2. Python environment.** `~/ros2_ws/env.sh` expects a venv at `~/ros2_ws/.venv`:

```bash
cd ~/ros2_ws
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/BlueBoat-SideScanSonar/requirements.txt
```

Then build the acados C library (BlueBoat-Control README) and point `~/.bashrc` at it:

```bash
export ACADOS_SOURCE_DIR=$HOME/ros2_ws/.venv/src/acados-template
export LD_LIBRARY_PATH=$ACADOS_SOURCE_DIR/lib:$LD_LIBRARY_PATH
```

For the ray-cast sonar (GPU), the simulated sonar node runs on the system Python, so it also
needs `warp-lang` there:

```bash
/usr/bin/python3 -m pip install --user --break-system-packages warp-lang==1.19.0
```

**3. `env.sh`.** It lives in `~/ros2_ws` (not in this repository) and holds:

```bash
source .venv/bin/activate
source install/setup.bash
```

**4. Build.** From a fresh terminal with only ROS sourced (not `env.sh`):

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select blueboat_interfaces   # first: every module uses its types
colcon build
```

Good to know:
- `colcon build` always runs from `~/ros2_ws`. This repository is not the workspace.
- Two ROS packages sit one folder below their git root:
  `BlueBoat-SSS-Sim/blueboat_sss_sim/` and `BlueBoat-Perception/blueboat_perception/`.
- `blueboat_belief_interfaces` builds before `blueboat_belief`; `blueboat_replanner` needs both
  interface packages. colcon orders these itself.
- `blueboat_gcs` and `BlueBoat-MCS` are not colcon packages: they run from their folders.

**5. Every new terminal:**

```bash
cd ~/ros2_ws && source env.sh
```

## Start here: BlueBoat Hub

The easiest way in. [`hub/`](hub/README.md) is one desktop window that launches, watches and
stops every app (MCS, GCS, QGroundControl, World Builder, Gazebo viewer, Log Reviewer, Belief,
Replanner, Aug Studio), shows each app's terminal, runs `colcon build` and opens the data
folders. Install: [hub/INSTALL.md](hub/INSTALL.md) (`cd hub && ./install.sh`).

Without the Hub, start the two main apps by hand:

```bash
cd ~/ros2_ws && source env.sh
cd src/BlueBoat-SideScanSonar/BlueBoat-MCS && python3 run.py              # Mission Control Station
cd ~/ros2_ws/src/BlueBoat-SideScanSonar/BlueBoat-SSS/blueboat_sss && python3 -m blueboat_gcs.main   # GCS
```

## Run a simulated survey

1. Build a world with the **World Builder** (`ros2 run blueboat_sss_sim world_builder`), or
   generate one headless (BlueBoat-SSS-Sim README).
2. In **MCS**: *Launch Mission* → simulation, pick the world, the survey path, the
   **Sonar model** and the **Slow-down**.
3. In the **GCS**: start the pipeline, **START**, then **Record**.
4. Stop with MCS's **Stop Mission** (it runs the safe shutdown first).

Same thing from one command, no clicking: [tools/sim_record/](tools/sim_record/README.md).

Check the simulator before producing results:

```bash
python3 -m blueboat_sss_sim.core.provenance --check   # exit 1 = stale install, rebuild
```

## Run a real survey

1. Boat in the water, Base Station WiFi up, laptop on its network.
2. In **MCS**: *Launch Mission* → real robot, controller, path, motors. The link guardian
   switches ON by itself; check its **GUARDIAN** box ([link_guardian/](link_guardian/README.md)).
3. In the **GCS**: pipeline, **START**, **Record**.
4. End with MCS's **Stop Mission**. E-STOP, servo release and ending the mission are three
   separate buttons.

Details: [BlueBoat-MCS/README.md](BlueBoat-MCS/README.md),
[BlueBoat-SSS/README.md](BlueBoat-SSS/README.md),
[BlueBoat-Control/README.md](BlueBoat-Control/README.md).

## Status

- **Simulator frozen** (2026-11-18, tag `sim-freeze-v1.0-2026-11-18`). The acceptance
  protocol's literal verdict is **NOT READY**. The owner froze it anyway as a
  **model-conditional tool**. A simulated result counts only if produced and stated under
  [`SIM_VALIDITY_CONDITIONS.md`](SIM_VALIDITY_CONDITIONS.md): a comparison of survey strategies
  in simulation, never a field detection rate.
- A world-generation update (v1.1, world generation only) is pending the owner's signature; the
  sonar engine is unchanged.
- **Detector not trained yet.** Perception runs a dummy detector by default.
- **Whole chain in Gazebo:** ran end to end once (development run). Never on the boat.
- **Evaluation:** planned, not built.

Current state and next steps: [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Documents

| File | Read it for |
|---|---|
| [`project_synthesis.md`](project_synthesis.md) | Scope, system architecture, design rules (the reference) |
| [`SIM_VALIDITY_CONDITIONS.md`](SIM_VALIDITY_CONDITIONS.md) | When and how a simulated result may be used |
| [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | Where the project stands |
| [`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md) | Open work across all repositories |
| [`docs/DESIGN.md`](docs/DESIGN.md) | How the modules fit together, interfaces, project-wide rules |
| [`docs/HISTORY.md`](docs/HISTORY.md) | Dated history |
| [`docs/DOC_MAP.md`](docs/DOC_MAP.md) | Where moved or merged documents went |
| [`target_families_and_surrogates.md`](target_families_and_surrogates.md) | Harbour target set and how it is simulated |
| [`literature_conclusions.md`](literature_conclusions.md) | Conclusions from the literature |
| [`project_review.md`](project_review.md), [`sim_review.md`](sim_review.md) | Dated reviews (cited by section from code) |

Each submodule has its own `README.md`.

## License

Apache License 2.0. See [LICENSE](LICENSE).
