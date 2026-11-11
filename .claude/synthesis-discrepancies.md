# Discrepancies against project_synthesis.md (superproject CLAUDE.md §6)

<!-- Moved verbatim from .claude/CLAUDE.md on 2026-11-07 (/doctor) so it loads on demand; section numbers unchanged, so "§4.x" / "§6 Dn" references elsewhere resolve here. -->

## 6. Discrepancies against `project_synthesis.md`

Current relational facts. `project_synthesis.md` outranks a module `CLAUDE.md` by convention;
where a module describes something that demonstrably exists and runs, the entry says which
source is the more reliable guide.

**D1 — Where preprocessing runs: resolved 2026-09-28** — on the operator laptop, like every
node (§1.1); anything saying "on the robot" is wrong.

**D2 — SSS ping message schema.** §5.2 specifies a custom two-sided message (`sound_speed`,
`range_max`, `num_samples`, `uint8[] port_intensities`, `uint8[] starboard_intensities`,
`ping_period`). What exists is `blueboat_interfaces/OmniscanProfile`: one-sided, one topic per
side, mirroring the decoded Cerulean header (§4.3). *More reliable:* the modules — the type exists and three
modules consume it; §5.2's schema reads as a pre-implementation sketch. Its *derived* content — the three-step ping→world transform and the slant-range
correction `r_ground = sqrt(r_slant² − h²)` — holds.

**D3 — Maximum ping rate: resolved** — §5.1's 20 Hz is right (§4.3).

**D4 — Continuous world-frame mosaic.** §5.3 ⚠: the world-frame mosaic is generated on demand
or post-mission, not continuously (wasteful, off the critical path); the GCS `MosaicService`
builds one **live** over satellite tiles. *Reconciled:* the ⚠ constrains the **detector's**
input path; the GCS mosaic is an operator display feeding no detector, and CM-10, which
protects the perception pipeline, is not violated. If a detector is ever fed from the mosaic,
the ⚠ binds directly.

**D5 — Range settings: resolved 2026-10-20.** The owner's decision is **20 m per side for
every survey condition** (§4.3, `project_synthesis.md` §8.5, rewritten): the old 30 m coverage /
15 m revisit passes are gone, and the implemented default is the setting. `sssCLAUDE.md` NC #5
(range from water depth, ~4× the deepest expected, because 80 m in shallow water pushed the
bottom return to sample 49/600 and broke bottom detection) still governs very shallow water.
The beach sessions of 2026-09-07 also ran **20 m** at ~1.2 m altitude (what
`config/shallow_beach_sonar.yaml` reproduces). Leftovers that still say 30 m / 15 m are module
lines or opt-in diagnostics (§4.3).

**D6 — TF tree.** §5.2's `map → odom → base_link → sss_link` with lever-arm offsets: **no
module consumes TF and none of those four frames exists** (§4.6 TF); the lever-arm point
surfaces as the transducer-offset disagreement (§4.3).

**D7 — Interface boundary, partly claimed (2026-10-16; chain re-stated 2026-10-20).** The
detector, the belief layer (multi-channel Bayesian grid: `p_target`, `n_observations`,
`aspect_coverage`, `last_intensity`, `max_confidence`) and the replanner are specified in §5.
Since 2026-10-20 the plan is the chain of §1: sonar module → Perception → Belief → Replanner →
Control, and the §5.1 "initial CPP" and "mission manager" boxes are **folded into the
Replanner**, which generates every survey type through Control's live path update.
**BlueBoat-Perception owns the detector boundary:** `/sss_ai/detections` (the GCS map) and
`/sss_ai/image_records` (one record per image, Belief's input contract,
`BlueBoat-Perception/docs/topics.md` §4). Its default detector is still the dummy; the YOLO
adapter over tiles is built (2026-10-23) but has no trained weights; calibration is identity (`calibrated: false`, so `confidence` is no
probability — §8.2 ⚠). **Belief, Replanner and Evaluation are planned, not built, and
unowned**; belief-grid channels, the three replanner rules (resolution, budget, abandonment)
and the confidence-calibration requirement are governed by `project_synthesis.md` §5.2, §8.1,
§8.2 until a module claims them. One fact to carry: the image records hold no survey area, no
anchor and no latitude / longitude, so Belief takes those from the mission, as the chain says.

**D8 — Mission swap: resolved 2026-10-20 (recorded 2026-10-19, Control `docs/REQUESTS.md`
R-4).** The old §5.1 had the mission manager perform a "MAVLink mission swap" to ArduPilot. In
the implementation nothing goes to ArduPilot: `master_control` follows the path on the laptop
and streams RC override (Control N6). `project_synthesis.md` §5.1, §5.2, §7.5, §9 D5 now name
Control's live path update (`/blueboat/update_path`, `/blueboat/path_progress`,
`/blueboat/path_update_event`; §4.1) as the mechanism. It is built and tested in Gazebo, **not
on water, and has no client**; MCS does not use it yet (a survey-mission launch mode is the
planned way); built-world simulations cannot yet run replanner-owned runs (Control R-3). The
caller is the Replanner (D7), unbuilt.

**D9 — Detector family and input geometry: resolved 2026-10-20 (recorded 2026-10-19).** The
old §5.1–§5.2 specified a "classical proposer + CNN classifier" on 512 × 512 patches every N
pings at ~1–2 Hz. Decision: **a YOLO model in BlueBoat-Perception**, on the GCS seabed images
as the code has them — 256 rows × 1200–2402 native slant bins, a new image every 128 rows
(~0.1–0.36 Hz measured), raw dB mapped by `fixed_gray_v1`, the adapter to tile across-track and
merge (`project_synthesis.md` §5.2 describes it). **Built 2026-10-23:** the YOLO adapter
(Ultralytics YOLO11s / YOLO26s; tiles 256 × 256, stride 128, merge `nms` or `greedy_nmm`;
offline = live byte-equal on CPU) and the offline tools — tile datasets split by world,
training, evaluation on held-out worlds. **Not yet:** trained weights, the comparison run
(merge rule and visibility threshold undecided), a calibrator beyond identity. CM-10 holds.

**D10 — "SSS data pipeline: Built, field-validated" (§9 D1; recorded 2026-10-19; synthesis
§9 D1 re-stated 2026-10-20 as built, verified in simulation, field validation partial).** The
pipeline is built and verified live in simulation, but the field validation predates most of
it:
- The corpus holds no field recording made by the current stack. The 2026-09-07 beach logs
  were recorded by Cerulean's SonarLink on BlueOS. **First current-stack field recordings,
  2026-10-27** (one pool, three harbour sessions, `~/ros2_ws/data/SSS_data/sessions/`):
  side identity and the 20 m / 1200-bin acquisition held, but they lost 4–61 % of pings at a
  free-running 34.5 Hz with 4 Hz frozen-stamp pose, against SonarView's 0 % at 20 Hz the
  same morning, and bottom tracking failed in deep water. The acquisition and recording side
  was reworked to SonarView's that day (§4.3, §4.4); it needs a field re-test
  (`sssTODO.md`).
- Only three July harbour logs come from `sss_processor_node`, and they predate the
  September changes: packet-based side identity, counter-offset row assembly, 20 m / 1200
  bins, GPS velocities in `.svlog`, the 0.285 m lever arm and georef convention 2
  (`project_review.md` header; `sssTODO.md` "Needs a real-sonar session", "Needed field
  data").

*More reliable:* the module TODOs. "Field-validated" applies to the July processor and to
offline replays of SonarLink logs, not to the stack as it stands. The "waterfall buffer" of
D1 exists as the GCS's seabed images.
