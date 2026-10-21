---
name: git-history
description: Dated history of the owner's orders that opened the frozen BlueBoat-Control and BlueBoat-MCS submodules (2026-09-28 to 2026-10-16) — what each order changed, which files, which interfaces were added. Use before judging whether a change in Control or MCS is covered by an earlier order, or when tracing why one of their additive interfaces exists.
---

# Git history of the frozen modules

Moved verbatim from the superproject `.claude/CLAUDE.md` §3 (2026-10-21). The standing
rules (frozen at `v1.0`, add-only, no commits) stay in the root file; this is the dated record.

## 3. Git architecture

The six module directories are git **submodules**, each an independent repository; root
`git status` shows a submodule as modified without naming files — inspect inside it.
`.gitmodules` paths are authoritative for the layout.

**Frozen modules (recorded 2026-09-18).** `BlueBoat-Control` and `BlueBoat-MCS` are frozen at
tag `v1.0` (Control `65b15bb` "Dev V1.0 (#1)", MCS `790934f` "V1.0 (#1)", both on
`origin/main`, 2026-09-14). The superproject gitlinks point at the `dev` HEADs `d64ac71` /
`3cfb58c`, trees byte-identical to the tags (`git rev-parse v1.0^{tree}` = `HEAD^{tree}` in
both, verified 2026-09-17); the tag is not an ancestor of `dev`, so `git describe --tags`
fails there by design. **Sessions do not edit these two submodules** unless the user
explicitly orders it; a needed change becomes a post-v1.0 item in the requesting module's
`TODO.md` or a review's update plan. **Add-only rule (owner, 2026-10-20):** Control and MCS
are updated **by additions only** — a new topic, service, parameter, launch argument or UI
element; nothing proven is renamed, retyped or changed in behaviour unless the behaviour stays
identical *and is shown to be* (`BlueBoat-Control/test/mc_harness.py --compare HEAD`, MCS's
smoke test, the interface baseline). Every dated order below is an instance of this rule. The
two "frozen" statements and the tree-identity claim here are the **2026-09-18 baseline**: the
gitlinks have since moved on (2026-10-20: Control `b94dd7b`, MCS `490f195`), so the trees are
no longer identical to the tags. Re-verified online 2026-09-28: `origin/main` = `v1.0`,
`origin/dev` = the gitlink, trees identical. **On 2026-09-28 the user ordered documentation,
comment and UI-text corrections** in both (the §1.1 deployment wording; no behaviour change),
and on 2026-10-08 a split of each `.claude/CLAUDE.md` into a trimmed root plus nested
`CLAUDE.md` files (Control: `blueboat_control/src/`, `blueboat_description/`, `log_reviewer/`;
MCS: `mcs/designer/`) — documentation only. **Also on 2026-10-08 the user ordered the MCS sea-state UI
redesign** (`mcs/core/sea.py`, `gui/dialogs/sea_state_dialog.py`, new
`gui/dialogs/sea_timeline_dialog.py`, `gui/sea_state_box.py`, `gui/theme.py`, the smoke-test
sea blocks and the MCS docs) — a behaviour change of those files only; launch arguments and
topics unchanged. **On 2026-10-09 the user ordered the run-session update in both modules**
(a real-robot launch connects and idles; runs are started / stopped from the station, one
log per run; Update Mission between runs; arrow-key control; Release E-STOP): Control's
`master_control.py`, `robot_interaction/robot_interface.py`, `launch/BlueBoat_launch.py`
and their docs; MCS's station code, smoke test and docs. Additive interface only — new
`/blueboat/run_command`, `/blueboat/run_state`, `/blueboat/run_log`,
`/blueboat/arrow_thrust`, parameters `session_mode`, `arrow_timeout` and launch argument
`session_mode` (default `False`, so the CLI and `Sim_launch.py` keep their behaviour);
nothing renamed or retyped (§4.1). **Also on 2026-10-09 the user opened both modules for the
sea-state follow-ups** ("if there's anything you need to update in control or mcs, you can do
it"): Control's `simulation_interface.py` re-publishes `/blueboat/controller_ready` every 1 s
like `robot_interface` (QoS unchanged); MCS's `launch_manager.companion_command` starts the
sea companion for every empty-world launch, a null sea included, and the SEA STATE box flags
a run on Gazebo's box hull (`mcs/core/sea.py`, `gui/sea_state_box.py`, smoke test, docs). No
interface changed. **On 2026-10-12 the user ordered a Rotation slider in MCS's ARROW CONTROL box**
(3–15 N, default 5; Power default 10 N): `gui/arrow_box.py`, `config/settings.py`, the
`core/arrows.py` docstring, the smoke test and the user guide. No interface changed — the
stream still carries the composed `[right, left]`. **On 2026-10-13 the user ordered v1.1 in both
modules: run bags and bag replay.** Every real-robot run also records a ros2bag of every
non-SSS topic, filed into its `Robot_data/<stem>/` folder (`robot_interface` + the ROS-free
`run_bag.py`: a separate `ros2 bag record` process, pre-armed paused between runs, resumed at
run start); and MCS's Gazebo launch gains Source **"From a ros2bag"** → Control's new
`Replay_launch.py` / `bag_replay` node: the boat moves **kinematically** along the recording
(the force-free `blueboat_description replay:=true` description — no hydrodynamics, collision,
gravity or thrusters, velocity pinned to zero — so sea state, wind and current cannot move it),
in the empty world or a GPS-anchored built world (read-only: `world.sdf` + `metadata.yaml`).
Additive interface only (§4.1): `/replay/state`, `/replay/command`, the `/replay/<name>`
namespace, `robot_interface` parameters `record_bag` / `trajectory`, launch argument
`record_bag` (default `True`, session runs only) and three additive `/blueboat/run_log` fields.
Nothing renamed or retyped; BlueBoat-SSS-Sim untouched. **On 2026-10-14 the user ordered the
link guardian in both modules (MCS v1.1):** Control's `robot_interface` arms the autopilot at
session connection *before* going to override (MANUAL → `default` → arm → `override`; a failed
arm never blocks the session) and gains the `input_str` token `rearm` and parameters
`arm_on_connect` / `arm_timeout` / `arm_default_timeout` (interface baseline re-taken); MCS
gains the GUARDIAN box (top of the left column), starts `guardian.py watch` with every
real-robot launch, asks at Turn Off Connection / exit whether to turn the guardian off and
disarm, moves LAYERS to the right column above MAP TOOLS and drops the robot heading arrow.
Additive interface only: `/link_guardian/status`, `/link_guardian/command`, the `rearm` token.
**On 2026-10-15 the user ordered the live path update in Control** (the Replanner entry
point; `BlueBoat-Control/docs/PATH_UPDATE_*.md`): new service `/blueboat/update_path`
(`blueboat_interfaces/srv/UpdatePath.srv`, the package's first addition since `v1.0`), topics
`/blueboat/path_progress` and `/blueboat/path_update_event`, parameter / launch argument
`path_source` (default `mission`) and `path_update_*` thresholds, the `configure` field and
`run_state` key `path_source`, and a run's `-pathlog.csv`. Additive only. Fixed-mission
behaviour was proven bit-identical by `test/mc_harness.py --compare HEAD` (21/21 on
2026-10-15). **Re-run 2026-10-20 against Control's uncommitted working tree: 15/21** — all six
PID scenarios differ (LoS, MPC and the real-parameter row are identical) because the working
tree changed the simulation branch's default PID gains (`outer_gains_x` 6.0 → 8.0,
`inner_gains_u` 2.0 → 2.5 in `master_control.py`), a behaviour change that the add-only rule
(above) does not allow without the harness showing identity. The path update itself has been
demonstrated in Gazebo only, not on water, and has no client. MCS was not edited, so its
"Replanner mode" row is still a request (Control `docs/REQUESTS.md` R-1).
**On 2026-10-16 the user ordered the BlueBoat-Perception companion in MCS** (additions only,
compatible with Control's requested "Replanner mode" row): `PerceptionConfig`
(`config/settings.py`), `perception_command` / `perception_dataset_name` and a third
companion (`ros/launch_manager.py`), the launch dialog's **Session** row (*Normal session* /
*Dataset creation*, field `LaunchParameters.perception_mode`, no launch argument), the smoke
test's `perception ok` block and the MCS docs. Every existing `to_cli()`, launch target and
sea companion is unchanged (pinned). No interface changed; BlueBoat-Control was not edited.
BlueBoat-Perception itself (added 2026-10-16) is not frozen.
