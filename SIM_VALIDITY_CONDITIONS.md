# Simulator validity conditions

*Permanent context for every session that runs the simulator or interprets its results (dataset, detector,
pipeline, campaign, thesis text). Version 1.0, 2026-11-18, after acceptance session 05 and evidence session 10.*

**Status.** The acceptance protocol's verdict is **NOT READY**. The owner froze the simulator anyway as a
**model-conditional tool** (`sim-freeze-v1.0-2026-11-18`). The simulator code is not changed any more. A result is
usable in the thesis only if it was produced inside the envelope of §2 and is stated with the rules of §5.

**Detail lives in:** `~/ros2_ws/sim_runs/sim_acceptance/10_evidence/SIM_FREEZE_CARD.md` (digests, defect sizes),
`~/ros2_ws/sim_runs/sim_acceptance/10_evidence/EVIDENCE_REPORT.pdf` (pictures),
`~/ros2_ws/sim_runs/sim_acceptance/05_report/SIM_acceptance_report_2026-11-18.md` (05),
`~/ros2_ws/sim_runs/sim_acceptance/freeze_decision.md` (the owner's decision). If this file
and the freeze card disagree, the freeze card wins on numbers and this file wins on interpretation.

---

## 1. What a simulated result means

The simulator answers one kind of question well: **"on the same seabed, with the same objects and the same sea,
which survey strategy does better, and by how much?"** It does not answer "what detection rate would we get in a
real harbour?".

Every result sentence starts with *"In a calibrated simulation environment, …"* and is a **comparison** (strategy A
against strategy B, easy sea against hard sea, one object family against another), never an absolute field number.

## 2. Envelope: run only inside these conditions

| Setting | Allowed | Reason |
|---|---|---|
| Sonar | 20 m range, 1200 bins, 44.3 µs pulse, both sides, production profile `raycast_harbour_fast_sonar.yaml` | The only setting compared with real data and where the first-return rule is verified. Never 600 bins or long pulses |
| Altitude above seabed | **4.5 to 7.0 m** | Level checked against real data at 4.7 and 6.9 m. Near 10 m it is unproven (05: +6 to +16 dB at two sites; session 10: undecided) |
| Ground range | 5 to 20 m; also give every result for **8 to 20 m** alone | 5 to 8 m is 2 to 4.5 dB too bright |
| Worlds | Campaign generator, with sediment patches; each world named by its content digest | Patched worlds are the closest to real pictures. The real-harbour replica is a validation world, not a results world |
| Sea | `calm` (reference), `harbour_chop` (easy), `field_matched` (hard) | Roll 0.24° and 2.2°: a quarter and twice the July harbour roll, so they bracket it. `field_matched_x2` is not a rougher sea (only yaw moment doubled): yaw arm for PID and LoS only |
| Controller | **MPC, field gains**, for the headline; **LoS** as the high-disturbance arm; always `sim_config:=field_equivalent` | MPC is the best-matched controller (speed within 1 %). Simulated MPC yaws less than the real boat, simulated LoS yaws more: together they bracket the real motion |
| Brackets | R1 flash narrow / wide; R2 clutter low / high; R5 corner low / high; R6 material low / high | Aspect response, clutter and three materials were never measured in the field |
| R6 choice | Dataset rendered at the **low** end; evaluation at **both** ends, low end quoted as the headline | The one real harbour tyre looks like the low end (dark ring, no highlight) |
| Fouling | Drawn per world, U(0.2, 1.0); recorded with every run | It sets object visibility strongly. Compare strategies on the **same world**, never across worlds without it |
| Seeds | At least 3 per condition; dataset worlds and evaluation worlds from disjoint seed ranges | |
| Statistics window | Drop the first 20 s after start and everything after the route ends | Start hold and run-up are not survey motion (as amendment A-07) |

## 3. What the simulator does well (why its results are relevant)

- **Sonar physics is verified.** Tests V1 to V8 pass against independent references. The flash of a flat face is
  0.6 to 0.75° wide, within 8.5 % of the reference.
- **The seabed picture is close to real inside the envelope.** Background level within 2 dB at 8 to 20 m ground
  range; all texture statistics pass. With per-picture normalisation the owner could not tell real from simulated
  (21 of 40, chance).
- **Geometry is right.** Objects, blocks, quay and shadows appear where the world says. A given roll produces
  stripes of the same sign and period as in the real rough-sea recording, at 64 to 84 % of the real size.
- **Disturbance reaches the picture.** In a closed-loop mission the recorded attitude reproduces the live picture
  within 0.03 dB; removing the attitude removes the banding and moves the patches. Under MPC in the hard sea the
  main effect is the heading swing, not roll.
- **Boat motion is right where it sets time and coverage.** Speed within 1 %, thrust per metre within 13 %,
  mission time within 3 %.
- **The whole chain runs.** 24 396 of 24 396 pings on the test mission; about 44 missions of 20 simulated minutes
  per day. Every object has exact ground truth in the world metadata.

## 4. Where it is weak, and which way that pushes the headline comparison

| Weakness | Size | Effect on "adaptive against two-pass" |
|---|---|---|
| Simulated pictures are brighter and more uniform than real (no ping-to-ping level lines) | About +1 to +2 dB at 8 to 20 m; a trained eye picks the source 73 % of the time in a fixed mapping | None on the comparison (same for both). A detector trained here is **not** shown to work on real data |
| MPC yaw rate on straight legs too low | 25 to 46 % low | Simulated pictures steadier than real. Mixed: the first survey misses less, revisits are cleaner. Covered by the LoS arm |
| Cross-track error too high | 25 to 95 % high | Against adaptive (revisits less precise) |
| Turns too long | 12 to 30 % on lawnmower; about 0.6 s per turn under MPC | Against adaptive (it turns more) |
| Structures (blocks, quay): levels off, shadows too crisp | 4 to 9 dB in highlight | None on targets; structures are a false-alarm context only |
| Plastic box | Shadow too short at the beach; at 7 m altitude neither highlight nor measurable shadow | Box is a low-recall class for both strategies; conservative. Not validated at harbour depth |
| Frame pot, net | Frame pot invisible, net a faint smudge at 7 m altitude | Low-recall classes; report per family, do not drop them silently |
| Wire pot (test V9) | Fast and reference settings differ by 1.06 dB highlight, 1.61 dB shadow | Same picture; quote the V9 note with any wire-pot result |
| Aspect response never measured in the field | Unknown; bracketed by R1 | The core mechanism of the thesis is model-based. Always give both R1 ends |
| Rough-sea water column | No aeration, no surface reverberation | Simulated rough sea is cleaner than real; same for both strategies |
| Ground-truth contact fields | `slant_range_m` is across-track range (up to 6 bins off); `shadow_bins` is geometric, 5 to 35 bins too long | None if labels come from the picture and the world metadata (rule below) |
| Offline rebuild time base | Waterfall rows 5.11 s behind ping time on the test mission | Align on seabed images' `t_s` or ground-truth `t_sim` before labelling |

Net direction: the known motion biases mostly work **against** the adaptive strategy, so a measured gain is on the
cautious side. This is an argument, not a proof; say it as such.

## 5. Rules for every experiment, figure and sentence

1. Give the conditions with every figure: world digest, profile, sea, controller, bracket ends, fouling, seeds.
2. Give every headline number at both R1 ends, and for 8 to 20 m ground range beside 5 to 20 m.
3. Compare strategies **paired**: same world, same seeds, same sea schedule.
4. A time difference inside **±3 % plus 0.6 s per turn** is not a result.
5. Labels come from the rendered picture and the world metadata. A contact is never a label.
6. Report detection per object family, and add an **oracle-detector arm** beside the trained detector, so the
   strategy result does not depend on the detector.
7. Train the detector with level and per-ping gain augmentation (the simulated level is not the real one).
8. State the literal verdict NOT READY beside the owner's freeze decision wherever the simulator is described.

## 6. Never claim

- Any detection rate or probability of detection **in the field**; that the detector works on real data.
- "Validated against held-out harbour data" (no untouched harbour recording remains).
- That simulated and real pictures are indistinguishable.
- "The simulated boat moves like the real one"; that the simulated sea reproduces the harbour's roll; "twice the
  field-matched sea".
- Quantitative highlight or shadow levels of structures or of the plastic box; any shadow length.
- Anything at more than 7 m altitude, on mud, or at 5 to 8 m ground range taken alone.
- A contact's range as true range to better than 0.1 m, or its shadow length to better than 0.6 m.
- That an offline replay reproduces the live chain object for object.

## 7. Identity (check before a run)

Engine digest `ffacf236faa57010`; simulator code digest `cc29e08780aac4cd`
(`python3 -m blueboat_sss_sim.core.provenance --check`); production profile SHA `f74ce9206906953a`; sea presets
`harbour_chop` `a69e7e07c63f895f`, `field_matched` `f01fe797827b38fb`; Control head `b86561f`. If a digest differs,
stop: the result is not from the frozen simulator.

Launch argument `path_source` (`mission`, default, or `replanner`) added to `full_mission_launch.py` on 2026-11-18 by owner order (R-3), before the freeze tag. Launch files are outside the code digest and the default is unchanged, so runs with `path_source:=replanner` are runs of the frozen simulator.

## 8. When this file changes

Only when new field data arrives (a harbour day with known objects at 5 to 7 m would test the aspect response and
the box; a deeper recording at 1200 bins would settle the altitude limit) or when the owner opens a new simulator
version. A session never widens the envelope on its own.
