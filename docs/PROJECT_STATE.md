# Where the project stands (2026-11-18)

*Replace in place when the state changes; dated history goes to `docs/HISTORY.md`. Open items:
`docs/OPEN_ITEMS.md`.*

## In one paragraph

The simulator was frozen on **2026-11-18** (`sim-freeze-v1.0-2026-11-18`, code digest `cc29e08780aac4cd`) after
the acceptance round (sessions 01–10, `~/ros2_ws/sim_runs/sim_acceptance/`). The pre-registered protocol's literal
verdict is **NOT READY**: V9 fails on the wire pot, C5 fails on the contact field meanings, C3 is not met on two
formal points, and field validation fails B1–B6. The owner froze the code anyway, as a **model-conditional tool**.
Its sonar physics is verified, its accuracy against the field is limited and stated, and it serves the thesis
question: a paired comparison of survey strategies on the same simulated harbour, not a field detection rate.
Every simulated result is produced and stated under `SIM_VALIDITY_CONDITIONS.md`, and the literal verdict is
stated beside the decision wherever the simulator is described.

## Modules

| Module | State |
|---|---|
| BlueBoat-SSS-Sim | **Frozen.** Production sensor `raycast_harbour_fast` (20 m, 1200 bins, 44.3 µs; altitude 4.5–7.0 m); campaign generator with object set version 2 (11 classes); seas `calm` / `harbour_chop` / `field_matched`. About 44 missions of 20 simulated minutes a day; 24 396 of 24 396 pings on the test mission. A code change is a new version, by owner decision |
| BlueBoat-Control | Frozen at `v1.0`, additions only. The identified plant (`sim_config:=field_equivalent`) is frozen with the simulator. MPC field gains = headline controller, LoS = disturbance arm. First supervised on-water test of the live path update still open |
| BlueBoat-MCS | Frozen at `v1.0`, additions only. Sea situation file and `thrust_gain` options added (09b). No "Replanner mode" yet (R-1) |
| BlueBoat-SSS | Driver, processor, GCS in use; one set of transducer offsets (fore/aft arm −0.345 m, adopted from the simulator, not measured) |
| BlueBoat-Perception | Dummy detector by default; YOLO over tiles built, **not trained**. The lever arm (CR-PER-2) is applied (`0d55d76`; re-checked by session 12). The dataset-label shadow end no longer uses the contact's `shadow_bins` (PER-LBL-1, done 2026-11-18); the class map is still the legacy 29 classes |
| BlueBoat-Belief | Built and installed; run under ROS, live in Gazebo with the dummy detector, and on one real recording. Never with a real detector. `p_exists` is not a probability until a calibrated detector exists |
| BlueBoat-Replanner | Built and installed; dev loop on Belief's core (preliminary: at the full budget no adaptive condition is distinguishable from C2; it predates Belief's arm, CR-REP-1). Run under ROS on an isolated graph, and **once in Gazebo** (2026-11-18): a C2 development run in a built world beside Control's node, Belief, Perception (dummy) and the GCS, the node on simulated time (`time_source: ros`); never on the boat |
| SSS-Dataset-Aug-Studio | Optional; nothing depends on it |
| Evaluation | Planned, not built |
| `link_guardian/` | Built; tested on the boat (owner, 2026-11-25) |

## Next work, in order

1. **Perception's lever arm (CR-PER-2):** done in code and confirmed live (2026-11-18: Perception's tests
   230 / 28; in Gazebo, Perception and Belief place the same ping sample within 0.057 m). The dataset labels'
   shadow end is fixed (PER-LBL-1); the class map (02-CR2) is still open.
2. **The dataset and the detector:** dataset worlds from the campaign generator, R6 low end, disjoint seed
   ranges for dataset and evaluation worlds, labels from the picture and the world metadata, level and per-ping
   gain augmentation; calibrate on held-out simulated worlds (CM-11).
3. **The pipeline in Gazebo:** sonar → Perception → Belief → Replanner → Control ran end to end once on
   2026-11-18 (a C2 development run in a built world, R-3 done; `~/ros2_ws/sim_runs/pipeline_dev/`). Next: C4 and
   the stop test (Replanner L-G2…L-G4), then the E4 C2 freeze on Gazebo tuning worlds.
4. **ICAROB Experiment 2** re-run on the frozen simulator.
5. **E4/E5 campaign:** paired comparisons, ≥ 3 seeds, both R1 ends, the 8–20 m band reported apart, an
   oracle-detector arm.

## Owner's closing steps of the freeze

Tag every module and the superproject; sign `freeze_decision.md`; rebuild once so the build stamp names the head;
re-run `provenance --check` (`docs/OPEN_ITEMS.md` FRZ-1, FRZ-2). Session 11 merged the register entries (FRZ-3).
