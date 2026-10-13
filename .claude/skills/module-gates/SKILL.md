---
name: module-gates
description: Run or report a BlueBoat submodule's gates — the exact test, lint, smoke-test, interface-guard and reproducibility commands per module, their current pass counts, the ROS-shell pitfalls that make them fail spuriously, and which gates survive a fresh clone. Use before running tests in any submodule, or when stating whether a module is green.
---

# Module gates

Moved from the superproject `.claude/CLAUDE.md` §7 (2026-10-08). Counts are snapshots; the
module's own `CLAUDE.md` carries the current one.

Lint in two modules, both `ruff check .`, both clean at ruff 0.16.5. No module has a
type-checker (MCS records a reasoned decline in its `CLAUDE.md` §7; the Aug Studio's
`CLAUDE.md` the same for a type-checker and CI). Several gates exist only in the working tree
and do not survive a fresh clone.

## Shell pitfalls (all modules)

- Do **not** `source ~/ros2_ws/install/setup.bash` before running a pytest gate: it switches
  `python3` to the workspace venv, which lacks pytest and `lark`. Call `/usr/bin/python3`
  explicitly (it has pytest, rclpy, PySide6 and `blueboat_interfaces`).
- In a ROS-sourced shell bare `pytest` dies before collection (plugin autoload pulls
  `launch_testing` → `lark`): prefix `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.
- The sim smoke test takes `/tmp/blueboat_sss_smoke.lock` (a second run waits, and the Stop
  hook runs it too): give the Bash call a timeout well above the suite's ~170 s.

## Per module

| Module | Gates, current state | Fresh clone |
|---|---|---|
| `BlueBoat-SSS-Sim` | `python3 -m test.smoke_test` from `BlueBoat-SSS-Sim/blueboat_sss_sim/` — its offline gate (no lint, type-checker, `pyproject.toml` or `ruff.toml` in the repo): **434 checks** since 2026-10-09 (431 plus one visible SKIP, covering the two bridge checks and the ApplyLinkWrench detection, on an interpreter without ROS; it runs on the venv python too), incl. the 2026-09-18 calibration / shadow-physics / wall-occlusion / land-layer / atomic-build gates, the 2026-09-16 reflectivity / shading / compositor-NaN gates and sections [10] sea state / [11] schema help / objects v3 / walls+pontoons; ~170 s, passing. Run every turn by two hooks in `.claude/settings.json`, both in `.claude/tools/smoke_gate.py` (stdlib only; no ROS, colcon or Gazebo). Its render fixture compares to float precision (1e-12 of an array's scale), not bit-for-bit: the venv's numpy 2.4 and the system numpy 1.26 differ by a few ULP. Optional, outside the gate: `QT_QPA_PLATFORM=offscreen python3 -m test.gui_smoke` (World Builder GUI, 118 checks). **Gazebo gate** (2026-10-08, real time, outside the hooks; needs `source ~/ros2_ws/env.sh` and a built package): `python3 -m test.gazebo_sea_test --world-dir ~/worlds/sea_validation/flat_5p0m --out <dir>` — four scenarios (calm / current / waves / both) of the same survey, headless, recorded and checked; `report.md` + figures in `<dir>` (`docs/sea_state_validation.md`). | `test/smoke_test.py` only — `.gitignore` excludes `.claude/tools/` and `.claude/settings.json`, so no hooks. `[2f]` is gated on a `.svlog` corpus at `$BLUEBOAT_SSS_CORPUS` (default `~/ros2_ws/data/SSS_data`) and skips when absent, so a clone still reaches `ALL CHECKS PASSED`. |
| `BlueBoat-MCS` | `QT_QPA_PLATFORM=offscreen python3 smoke_test.py` (29 checkpoints incl. `replay ok` — the v1.1 bag replay: launch arguments, bag discovery, dialog, REPLAY box, RUN-box Bag row — `sea state ok` — the plain-language sea model, scenario files, timeline segments, the headless sea / timeline dialogs — `sea box ok`, and the six run-session blocks `session launch ok` / `placement ok` / `arrow ok` / `run session ok` / `start marker ok` / `session window ok`; passing 2026-10-09); `ruff check .` from its own `ruff.toml`, needing neither ROS nor a venv. | No lint gate: `ruff.toml` and `requirements-dev.txt` are gitignored, untracked. |
| `SSS-Dataset-Aug-Studio` | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest` (64 tests at v0.4.0, 10 marked `gui`, all passing; without PySide6 the Qt suite skips and stays green); `ruff check .` from the **tracked** `pyproject.toml`; `python tools/repro_gate.py` (the CM-7 byte-reproducibility release gate: one `GenerationConfig` run at 1 and at 4 workers, hard-comparing images, labels and `generation_manifest.json`); `python tools/docs_sync_check.py` (stdlib-only, run by `.githooks/pre-commit`, blocking a commit that changes a file under `augmentations/` without its encyclopedia page and `AUGMENTATION_STRATEGIES.md` section). | Partly (verified 2026-09-28): `tools/`, `tests/test_gui_smoke.py`, `tests/test_dataset_metadata.py`, `docs/history/`, the four `docs/demo_*.png` are tracked; `.githooks/` and `demo_dataset/` are gitignored (of the fixture only `data.yaml` and `sss_aug_dataset.yaml` are tracked) — gate scripts, but no hook and no fixture images. |
| `BlueBoat-SSS` | `QT_QPA_PLATFORM=offscreen /usr/bin/python3 -m pytest -p no:cacheprovider` from `BlueBoat-SSS/blueboat_sss/` (`pytest.ini` already passes `-q`), also a pre-commit hook: the GCS regression suite needing no ROS, one rclpy-gated MCS sim-GPS compatibility test, and `blueboat_sss` node tests that run only with `blueboat_interfaces` on the path. Every test reproducing a MEASURED field number is gated on a `.svlog` corpus at a hard-coded external mount and skips without it. **297 pass / 50 skip on 2026-09-28** with `blueboat_interfaces`; without it and without the corpus, 225 pass / 66 skip (2026-09-15). | Partly (verified 2026-09-28): `blueboat_sss/tests/`, `blueboat_sss/pytest.ini`, `blueboat_gcs/analysis/`, `.claude/skills/` tracked; `.githooks/` and `requirements-dev.txt` gitignored — suite without its pre-commit hook. |
| `BlueBoat-Control` | **No test framework, no committed gate.** One working-tree gate: `python3 .claude/tools/interface_inventory.py --check .claude/tools/interface_baseline.json` (the N1/CM-1 contract surface — 147 pub/sub/service/client/parameter entries since the 2026-10-13 v1.1 run-bag / bag-replay re-baseline, plus the three `blueboat_interfaces` field lists; stdlib only, ~0.15 s; also a `PostToolUse` hook). | None: `.gitignore` excludes `.claude/tools/` and `.claude/settings.json`. |
