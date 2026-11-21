# Document map (2026-11-18, session 11)

*Every documentation or instruction file that was merged, moved, split or deleted in session 11, and where its
content is now. Files not listed stayed where they were. Deleted originals were tracked and unchanged at HEAD, so
git history keeps them (`git show HEAD:<path>` before the owner's commit); no original was untracked or dirty, so
nothing went to an archive folder. "Verbatim" means the text was moved without rewording; corrections made
after a move are marked "(2026-11-18)" in place.*

## Superproject

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` §1 (system overview, module table, §1.1 deployment), §2 (workspace), §3 (git architecture), §5 (CM-1…CM-16 full text) | `docs/DESIGN.md`, verbatim, same section numbers; `.claude/CLAUDE.md` keeps one short line per rule, the new §0 "Simulator frozen" and the import line of `SIM_VALIDITY_CONDITIONS.md` (written `@../` + the file name, resolved from `.claude/`) |
| `.claude/CLAUDE.md` dated narrative (module build dates, owner orders) | `docs/HISTORY.md` (one line each); the owner orders stay in skill `git-history` |
| `README.md` lines 51–158 (an old copy of the BlueBoat Control README) | dropped: `BlueBoat-Control/README.md` holds the v1.0 text of the same content |
| — (new) | `docs/PROJECT_STATE.md`, `docs/OPEN_ITEMS.md`, `docs/HISTORY.md`, `docs/DESIGN.md`, `docs/DOC_MAP.md` |
| `SIM_VALIDITY_CONDITIONS.md` | unchanged except lines 10–11: four paths made absolute (`~/ros2_ws/sim_runs/sim_acceptance/…`) |
| `.claude/interface-contract.md`, `.claude/synthesis-discrepancies.md`, skills `file-interfaces`, `sim-run-recording` | in place; stale lines corrected (CR-PER-2, ray-cast contacts, renderer default, envelope, dead paths) |

## BlueBoat-SSS-Sim

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` §1, §2, §7, §8 | `.claude/development.md`, verbatim |
| `.claude/CLAUDE.md` §3 (3.1–3.5) | `.claude/interface.md`, verbatim |
| `.claude/CLAUDE.md` §4 (NC #1–#17) | `.claude/constraints.md`, verbatim; one line per rule stays in `CLAUDE.md` |
| `.claude/CLAUDE.md` §5, §6 | `.claude/data-config.md`, verbatim |
| `README.md` "Start tutorial" (Steps 1–7, "If something goes wrong") | `docs/TUTORIAL.md` (repository root), verbatim |
| `README.md` "The ray-cast sensor" (state of 2026-11-07 to 11-11) | `README.md` (rewritten to the frozen state) and `docs/HISTORY.md` (the dated facts) |
| — (new) | `docs/HISTORY.md`, `docs/TUTORIAL.md` (repository root, not installed) |
| `blueboat_sss_sim/docs/**` | **unchanged**: installed by `setup.py` and cited by the frozen code |
| — (new, 2026-11-21, session 14) | `docs/population/POPULATION_MODEL.md`, `docs/population/EVIDENCE.md`, `docs/population/figures/` (repository root, not installed); `blueboat_harbour_population/` (the second package); `blueboat_sss_sim/blueboat_sss_sim/builder/CLAUDE.md` gained a section on Screen 5's Mission-like mode |

## BlueBoat-SSS

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` "ROS 2 interface" + `sss_node.py` + "BlueBoat GCS" | `.claude/interface.md`, verbatim |
| `.claude/CLAUDE.md` `sss_processor_node.py` | `.claude/processor.md`, verbatim |
| `.claude/CLAUDE.md` NON-NEGOTIABLE constraints (NC #1–#16) | `.claude/constraints.md`, verbatim (NC #11 marked superseded by CM-11) |
| `.claude/CLAUDE.md` Measured acquisition settings, Data produced | `.claude/acquisition-data.md`, verbatim |
| `.claude/CLAUDE.md` Commands | `.claude/commands.md`, verbatim |
| `blueboat_sss/blueboat_gcs/CLAUDE.md` Key GCS design decisions | `.claude/gcs-design.md`, verbatim |
| `blueboat_sss/blueboat_gcs/CLAUDE.md` Data produced by the GCS | `.claude/gcs-data.md`, verbatim |
| `blueboat_sss/blueboat_gcs/CLAUDE.md` Testing and performance notes | `.claude/gcs-testing.md`, verbatim |
| `blueboat_sss/terminals.txt` | **kept**: it differs from the root `terminals.txt` and is cited by `blueboat_sss/README.md` and `.claude/commands.md` |

## BlueBoat-Control

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` §2 Interface | `.claude/interface.md`, verbatim |
| `.claude/CLAUDE.md` §3 Build, launch, run (+ Gates) | `.claude/build-run.md`, verbatim |
| `.claude/CLAUDE.md` §4 Control architecture, §5 Thrust path | `.claude/control-architecture.md`, verbatim |
| `.claude/CLAUDE.md` §6 Data, §7 Trajectories, §8 `blueboat_description`, §9 `log_reviewer/` | `.claude/data-trajectories.md`, verbatim |
| `blueboat_control/src/CLAUDE.md` §4 detail | `.claude/src-control-detail.md`, verbatim |
| `blueboat_control/src/CLAUDE.md` §5 detail, bag-replay evidence | `.claude/src-thrust-detail.md`, verbatim |
| `log_reviewer/CLAUDE.md` §9.3–§9.7 | `.claude/log-reviewer-detail.md`, verbatim |
| `README.md` | in place; one state note added at the top (additions only) |

## BlueBoat-MCS

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` §1 Layout & internals | `.claude/layout.md`, verbatim |
| `.claude/CLAUDE.md` §2 ROS 2 interface (subscriptions, publications, launch modes, frames) | `.claude/interface.md`, verbatim |
| `.claude/CLAUDE.md` §4 Map, §5 Pattern Designer, §6 Control-stack files | `.claude/map-designer-control.md`, verbatim |
| `.claude/CLAUDE.md` §7 Commands and gates, §8 Documentation set | `.claude/commands-docs.md`, verbatim |
| `README.md` | in place; one state note added at the top (additions only) |

## BlueBoat-Perception

| Old path | Now |
|---|---|
| `.claude/CLAUDE.md` §6 Gates | `.claude/gates.md`, verbatim (a summary stays) |
| `README.md`, `.claude/TODO.md` | in place; state note, stale lines corrected |

## BlueBoat-Belief

| Old path | Now |
|---|---|
| `README.md` §3 "How it works, and the science behind it" (3.1–3.9) | `blueboat_belief/docs/DESIGN.md` §8 (8.1–8.9), verbatim |
| `README.md` §8 Main references (list) | condensed in place; every entry is in `blueboat_belief/docs/REFERENCES.md` |
| `blueboat_belief/docs/REQUESTS.md` R-8, `DESIGN.md` L22 | updated in place (done: Perception applies the arm) |

## BlueBoat-Replanner

| Old path | Now |
|---|---|
| `README.md` §2 Scientific background | `docs/DESIGN.md` §13, verbatim |
| `README.md` §4 How it works | `docs/DESIGN.md` §14, verbatim |

## SSS-Dataset-Aug-Studio

| Old path (deleted after the merge) | Now |
|---|---|
| `PROJECT_OVERVIEW.md` | `README.md` (Objectives, families, architecture paragraph, configuration system, verbatim) |
| `GETTING_STARTED.md` | `docs/user_manual.md`, first chapter "Getting started", verbatim (test count corrected) |
| `docs/architecture.md` | `docs/DESIGN.md` Part 1, verbatim |
| `docs/developer_guide.md` | `docs/DESIGN.md` Part 2, verbatim |
| `docs/scientific_documentation.md` | `docs/DESIGN.md` Part 3, verbatim |
| `docs/math_appendix.md` | `docs/DESIGN.md` Part 4, verbatim |
| `docs/bibliography.md` | `docs/DESIGN.md` Part 5, verbatim (`sss_aug_studio/documentation/bibliography.bib` unchanged) |
| `docs/future_work.md` | `docs/DESIGN.md` Part 6, verbatim |
| `docs/history/architecture_update_v0.2.md`, `docs/history/architecture_update_v0.2.1.md`, `docs/history/architecture_update_v0.3.md` | `docs/HISTORY.md`, verbatim |
| `.claude/CLAUDE.md` Layout, Core data model, Augmentation families, Extension contract, GUI architecture | `.claude/code-architecture.md`, verbatim |
| `.claude/CLAUDE.md` Commands, Testing conventions | `.claude/commands-testing.md`, verbatim |

References to the moved Aug Studio files were updated in `AUGMENTATION_STRATEGIES.md`, `.claude/CLAUDE.md`,
`.claude/code-architecture.md`, `docs/DESIGN.md`, `docs/HISTORY.md`, `docs/user_manual.md` and the docstring of
`sss_aug_studio/gui/encyclopedia.py`.

## Automatic loading (added 2026-11-18)

Each repository's `.claude/rules/*.md` (all but Belief; the Replanner's three rules predate this) are path-scoped
rules that import the `.claude/` topic files above when a matching file is read or edited. The topic files stay
where this map says.
