# Project history (superproject)

*Dated decisions and session outcomes, newest last, one short paragraph each, with the evidence to read. Module
histories: each module's own documents (`BlueBoat-SSS-Sim/docs/HISTORY.md`, `SSS-Dataset-Aug-Studio/docs/HISTORY.md`,
Control and MCS: skill `git-history`). Created 2026-11-18 (session 11) from the dated lines of the root
`CLAUDE.md` and the session handoffs.*

## 2026-08 to 2026-10: building the chain

- **2026-09-04.** `robot_interface` and `param_set` restore the default servo mapping themselves; CM-16 was
  reworded: a closed gate streams neutral instead of writing nothing (`docs/DESIGN.md` §5 CM-15, CM-16).
- **2026-09-14.** `BlueBoat-Control` and `BlueBoat-MCS` tagged `v1.0` (Control `65b15bb`, MCS `790934f`); frozen
  on 2026-09-18 (`docs/DESIGN.md` §3).
- **2026-09-17/18.** The simulator review (`sim_review.md`) and the project review (`project_review.md`); the
  review's Part 6 update plan was implemented on 2026-09-18 (`sim_review.md` Part 7).
- **2026-09-28.** Owner: all code runs on the laptop, nothing of ours on the boat (`.claude/CLAUDE.md` §1.1).
  Acquisition defaults equal in simulation and real water.
- **2026-09-28 to 2026-10-16.** Dated owner orders opened Control and MCS by additions (documentation splits,
  sea-state UI, run sessions, v1.1 run bags and replay, link guardian, live path update, the Perception companion
  in MCS): skill `git-history`.
- **2026-10-09.** Run-session plumbing exists only in a real-robot launch (CM-2 exception).
- **2026-10-14.** The connection-loss guardian (`link_guardian/`), the one owner-ordered exception to "nothing
  runs on the boat"; `LGRD_TIMEOUT` 5 → 15 s and the automatic hand-back on 2026-10-28.
- **2026-10-15.** Live path update `/blueboat/update_path` (`UpdatePath.srv`) added to Control.
- **2026-10-16.** BlueBoat-Perception became the station's one detection source; dataset mode.
- **2026-10-20.** Owner decisions: the module chain sonar → Perception → Belief → Replanner → Control; the
  headline detector is trained on simulated datasets (CM-11, which replaced "real imagery only"); Control and MCS
  are updated by additions only; new modules may own their interfaces package (CM-1).
- **2026-10-23.** Perception's YOLO over tiles (YOLO11s / YOLO26s, no trained weights yet).
- **2026-10-27.** SonarView's acquisition timing adopted (50 ms); a run bag can drive the simulated sonar.

## 2026-11: Belief, Replanner, and the simulator acceptance round

- **2026-11-02.** The GCS starts the simulated sonar beside a bag replay.
- **2026-11-04.** BlueBoat-Belief built (the Belief brief governs Belief's design).
- **2026-11-12.** Belief run under ROS (isolated graph, live in Gazebo, one real recording); Perception's image
  records feed Belief.
- **2026-11-13.** BlueBoat-Replanner built and installed (gate 278/0/0; dev loop on Belief's core, preliminary).
- **2026-11-13 to 2026-11-18. The simulator completion and acceptance round**, sessions 01–10 (evidence root
  `~/ros2_ws/sim_runs/sim_acceptance/`; criteria pre-registered in
  `00_README_order_rules_acceptance_criteria_FROZEN.md`): 01 sonar physics, 02 World Builder and campaign
  generator (object set version 2), 02b ray-cast fix, 03 sea state, 04 / 04b / 04c control plant, 06 the lever arm
  in the processor, GCS, Belief and Perception (2026-11-15), 09a / 09b run records and MCS options, 05 the
  acceptance report (literal verdict NOT READY), 10 the evidence report. One paragraph per session:
  `BlueBoat-SSS-Sim/docs/HISTORY.md`.
- **2026-11-15.** One set of transducer offsets across the chain (fore/aft arm −0.345 m, adopted from the
  simulator): the processor, the GCS (CR-SSS-1/2), Belief (CR-BEL-1, D-12) and Perception (CR-PER-1/2,
  `0d55d76`).
- **2026-11-18. The owner froze the simulator** (`sim-freeze-v1.0-2026-11-18`, code digest `cc29e08780aac4cd`)
  as a model-conditional tool; conditions in `SIM_VALIDITY_CONDITIONS.md`; decision
  `~/ros2_ws/sim_runs/sim_acceptance/freeze_decision.md`.
- **2026-11-18, session 11.** Post-freeze clean-up. 12.18 GB of regenerable acceptance data was deleted (every
  result kept); session 10's register entries were merged; every `CLAUDE.md` was brought under 200 lines, the
  moved text kept verbatim in topic files and `docs/DESIGN.md`; documents were merged (`docs/DOC_MAP.md`); the
  instruction files were audited. Report: `~/ros2_ws/sim_runs/sim_acceptance/11_cleanup/REPORT.md`.
- **2026-11-18, session 12** (Perception, in parallel). Confirmed that CR-PER-2 was already in the code; added
  tests (222 pass / 28 skip) and measured the A1 gap on real data (0.763 → 0.073 m):
  `~/ros2_ws/sim_runs/perception/handoff_12_cr_per_2.md`.
- **2026-11-18, session 13.** R-3 by owner order before the freeze tag: `full_mission_launch.py` takes `path_source`
  (outside the code digest, default unchanged); the Replanner's node clock `time_source` (`ros` in Gazebo, `wall`
  byte-identical by default); the whole chain ran once in Gazebo (a C2 development run, Replanner `done`, CR-PER-2
  confirmed live); `sim_acceptance/` reviewed again, nothing removed: `~/ros2_ws/sim_runs/replanner/handoff_13_R-3.md`.
