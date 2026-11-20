# BlueBoat — aspect-aware side-scan sonar survey (superproject)

> ## 🚀 Start here: BlueBoat Hub
>
> **[`hub/`](hub/) is the desktop app that ties every module together.** One window to:
> - launch, watch and stop every app: Mission Control Station, GCS, QGroundControl, World
>   Builder, Gazebo viewer, Log Reviewer, Aug Studio;
> - see each app's live terminal;
> - build the workspace (`colcon build`);
> - open the data folders.
>
> Every app still opens in its own window. Stopping an app closes it the way its own ✕ does,
> so MCS still runs its safe shutdown.
>
> **Install:** follow [hub/INSTALL.md](hub/INSTALL.md) (`cd hub && ./install.sh`); it ends
> as an icon on your Desktop. Details and how to add a module: [hub/README.md](hub/README.md).

## Project at a glance

A BlueRobotics BlueBoat USV with two Cerulean Omniscan 450 SS runs autonomous, heading-aware
side-scan sonar survey in shallow enclosed water. **All project software runs on the operator
laptop** (this workspace, `~/ros2_ws`), linked to the boat through the BlueBoat Base Station
WiFi; the boat carries only its hardware and its own firmware (plus the connection-loss script in
`link_guardian/`).

The scientific goal is a model-conditional, simulated comparison of adaptive heading-aware
replanning against a seriously tuned two-pass orthogonal survey, with real water used to
validate the simulator, run the heading-response experiment and demonstrate the system.

```
sonar module (seabed images + metadata) → Perception → Belief → Replanner → Control
```

| Module (submodule) | State |
|---|---|
| `BlueBoat-Control` — vehicle motion, run bags / replay, **live path update** | existing (additions only) |
| `BlueBoat-MCS` — Mission Control Station | existing (additions only) |
| `BlueBoat-SSS` — sonar driver, processor, Ground Control Station | existing |
| `BlueBoat-SSS-Sim` — Gazebo worlds, sonar and sea-state simulation | **frozen 2026-11-18** (`sim-freeze-v1.0-2026-11-18`): literal acceptance verdict NOT READY, used as a model-conditional tool under `SIM_VALIDITY_CONDITIONS.md` |
| `BlueBoat-Perception` — detector (dummy by default; YOLO over tiles, not yet trained), per-image records, simulated dataset mode, tile-dataset / training / evaluation tools | existing; lever arm (CR-PER-2) applied |
| `SSS-Dataset-Aug-Studio` — dataset augmentation | optional |
| `BlueBoat-Belief` — belief map: processed pings + detections → `BeliefGrid` (coverage, aspect history, contacts), the Replanner's only target evidence | built; run under ROS and live in Gazebo, never yet with a real detector |
| `BlueBoat-Replanner` — aspect-aware replanner: generates every survey condition (single pass, two-pass orthogonal baseline, append-on-completion, informative) and changes the path mid-run through Control's live path update | built, in `~/ros2_ws/install`; dev loop on Belief's own core; run under ROS on an isolated graph, and once in Gazebo beside Control's node (a C2 development run in a built world, 2026-11-18); never on the boat |
| Evaluation | **planned, not built** |

## Where the project stands (2026-11-18)

The simulator was frozen on **2026-11-18** after the acceptance round (sessions 01–10). The acceptance
protocol's literal verdict is **NOT READY**; the owner froze it anyway as a **model-conditional tool**
(`~/ros2_ws/sim_runs/sim_acceptance/freeze_decision.md`). Every simulated result is produced and stated under
[`SIM_VALIDITY_CONDITIONS.md`](SIM_VALIDITY_CONDITIONS.md). Next work, in order: the dataset and the detector
(Perception), the whole pipeline in Gazebo (one C2 development run on 2026-11-18; C4 not yet), the ICAROB Experiment 2 re-run on
the frozen simulator, then the E4/E5 campaign. Details: [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md); open
items across every repository: [`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md).

## Documents

| Read | For |
|---|---|
| `project_synthesis.md` | scope, evidence architecture, system architecture, the ⚠ rules (the authority) |
| `.claude/CLAUDE.md` | how the modules relate (loaded by every Claude Code session here); full text `docs/DESIGN.md` |
| `SIM_VALIDITY_CONDITIONS.md` | the conditions under which simulated results may be used |
| `docs/PROJECT_STATE.md` · `docs/OPEN_ITEMS.md` · `docs/HISTORY.md` | state, open items, dated history |
| `docs/DOC_MAP.md` | where every merged or moved document went (2026-11-18) |
| `target_families_and_surrogates.md` | harbour target set and its simulation specification |
| `literature_conclusions.md` · `project_review.md` · `sim_review.md` | literature directives; the dated reviews (cited by section from code) |
| `link_guardian/README.md` · `tools/sim_record/README.md` · `hub/README.md` | connection-loss guardian; command-line simulated runs; the Hub |

Each submodule has its own `README.md` and `.claude/CLAUDE.md`. Building, launching and operating the control
stack (robot description, launch files, terminal commands on `/blueboat/input_str`):
[`BlueBoat-Control/README.md`](BlueBoat-Control/README.md). This README carried an older copy of that text until
2026-11-18.

## Build

```bash
cd ~/ros2_ws && colcon build        # the only workspace; blueboat_interfaces first
source /opt/ros/jazzy/setup.bash && source install/setup.bash
python3 -m blueboat_sss_sim.core.provenance --check   # the frozen simulator: code digest cc29e08780aac4cd
```

Build order and per-module gates: `.claude/CLAUDE.md` §2 and the skill `module-gates`.

# License
blueboat package is open-sourced under the MIT License. See the LICENSE file for details.
