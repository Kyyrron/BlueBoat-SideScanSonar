---
name: svlog
description: Read, characterise, compare or decode a .svlog side-scan sonar recording (real or simulated) — which of the project's tools answers which question, the one-screen digest, the Python recipes with the real field names, the corpus map, and the caveats that make sim-vs-real numbers wrong. Use before touching any .svlog, before comparing simulated and field recordings, or when a GCS session's pictures need explaining.
---

# `.svlog` recordings

A `.svlog` is a bare stream of framed Cerulean Ping-Protocol packets. Nothing to
re-derive: the format is documented, and the tools below read it. **Do not hand-parse a
file before running the digest.**

- **Framing and packet ids:** `'B''R' | u16 len | u16 id | u8 src | u8 dst | payload |
  u16 checksum`. The ids:
  - 10: session JSON
  - 12: SonarView view config
  - 150: mavlink JSON (`LOCAL_POSITION_NED`, `GLOBAL_POSITION_INT`, `ATTITUDE`)
  - 2194: Omniscan status
  - 2198: `OS_MONO_PROFILE`, one ping, one side

  Full paragraph: `BlueBoat-SSS/.claude/CLAUDE.md` (the `.svlog` item).
- **2198 byte map:** `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md` §4.
- **What the field logs actually contain** (mis-tags, counters, clocks, sessions):
  `BlueBoat-SSS/blueboat_sss/blueboat_gcs/docs/SONARVIEW_SVLOG_ANALYSIS.md` §3, §9.

## Which tool answers which question

Everything is read-only and needs no ROS. Run each tool from the directory shown, with
`python3 -m`, so the **source** is used. A script run by path imports the installed
`~/ros2_ws/install` copy, which silently describes the last `colcon build`.

| Question | Command | From |
|---|---|---|
| **What is in this file?** Census, sides, acquisition, gain walk, pulse, ping period vs the device law, counter restarts, `channel_number` 255, bottom range, GPS / attitude, clock regime. Stdout only, ~4 s / 175 MB | `python3 -m blueboat_sss_sim.analysis.svlog_digest F.svlog [...] [--json]` | `BlueBoat-SSS-Sim/blueboat_sss_sim` |
| Forensics: sessions, PRI and ping-number gaps, **counter offset**, `src` vs `channel_number`, FBR p10/50/90, waterfall PNGs; cross-file table | `python3 -m blueboat_gcs.analysis.svlog_forensics --out DIR [--no-images] [--compare] LOG...` (skill `svlog-forensics`) | `BlueBoat-SSS/blueboat_sss` |
| Sim vs real: timing law, reported-dB level at fixed slant ranges, texture statistics, several files in one table | `python3 -m blueboat_sss_sim.analysis.svlog_compare --out DIR A.svlog B.svlog ...` (= `sss_svlog_compare`) | `BlueBoat-SSS-Sim/blueboat_sss_sim` |
| Absolute level vs slant range **per altitude band**, recording against a world | `python3 -m blueboat_sss_sim.analysis.calibration_cli --svlog F --world W --trajectory T --out DIR` (= `sss_calibration_report`) | same |
| Quay / wall contrast | `python3 -m blueboat_sss_sim.analysis.wall_contrast F.svlog [--json]` | same |
| An object's signature in a GCS session, sim or real | `python3 -m blueboat_sss_sim.analysis.object_signature <session>/seabed_images --at X Y [--radius 2.5]`, with X Y in that session's GCS frame | same |
| Soundings / bathymetry from the bottom return | `python3 -m blueboat_sss_sim.analysis.bathymetry F.svlog --lat0 .. --lon0 .. [--out CSV]` | same |
| Look at it | GCS: Open SVLOG, the replay window (refits the display model) | `BlueBoat-SSS/blueboat_sss`: `python3 -m blueboat_gcs.main` |

## Python recipes

Run these from `BlueBoat-SSS-Sim/blueboat_sss_sim`.

```python
from blueboat_sss_sim.analysis.svlog_reader import iter_packets, read_svlog, gps_track, pose_track
from blueboat_sss_sim.sonar.encoder import parse_frame, OS_MONO_PROFILE_ID      # 2198
from blueboat_sss_sim.analysis.calibration import scale_to_db, fbr_bin

s = read_svlog(path, with_power=True)   # SvlogStreams: profiles, positions, gps, attitude,
                                        # skew_ms, clock_frozen, n_packets
p = s.profiles[0]                       # ProfileRecord: side (Side.PORT/STARBOARD), ping_number,
                                        # timestamp_ms, length_mm, num_results, gain_index,
                                        # analog_gain, min/max_pwr_db, pwr_results, pulse_duration_sec,
                                        # vehicle_heading_deg, transducer_heading_deg, order
db = scale_to_db(p.pwr_results.astype(float), p.min_pwr_db, p.max_pwr_db)
i = fbr_bin(db)                         # first bottom return bin, None = miss
for pkt in iter_packets(path):          # SvlogPacket(packet_id, payload, raw)
    if pkt.packet_id == OS_MONO_PROFILE_ID:
        d = parse_frame(pkt.raw)        # ping_number start_mm length_mm timestamp_ms ping_hz gain_index
                                        # num_results sos_dmps channel_number pulse_duration_sec
                                        # analog_gain max_pwr_db min_pwr_db transducer_heading_deg
                                        # vehicle_heading_deg pwr_results
_, idx, lat, lon = gps_track(path, s)   # profiles placed on GPS (file order on a frozen clock)
```

The GCS equivalent, with per-segment counter offsets and multi-session handling, is
`blueboat_gcs.core.svlog.load_svlog(path).pings` (from `BlueBoat-SSS/blueboat_sss`).

## Caveats that make numbers wrong

**Any `.svlog`:**
- **Never write into a recording's tree.** `.svlog` files are primary field data (CM-7).
  `svlog_forensics` refuses an `--out` inside one; `svlog_compare` and `calibration_cli`
  do **not** check, so keep `--out` outside `~/ros2_ws/data/SSS_data`.
- **`pwr_results` is normalised per ping** onto `[min_pwr_db, max_pwr_db]`. Convert each
  ping to dB before averaging or stacking.
- **Side comes from `channel_number`** (byte 34). Where it is 255, the wrapped sign of
  `transducer_heading_deg` decides. Never use the `src` byte: it is wrong on up to 29.5 %
  of field packets.
- **The two devices number pings independently.** Offsets of 0, −1 and +60 are measured,
  so align them before pairing sides (forensics reports the offset).
  - `timestamp_ms` is each device's own uptime and runs backwards in file order: sort per
    side.
  - Mavlink `time_boot_ms` is a third clock. Processor-written files **freeze** it; the
    digest says "FROZEN", and pairing is then by file order (`gps_track` / `pose_track`
    do this).
- **Range, bin count and pulse change within a file.** Many field logs switch range
  mid-survey. The digest lists every setting; a single summary number is the mode.
- **Auto-gain walks the gain index 4→7** within real logs, a 20·log10 step in level.
  Simulated logs stay at 4.

**`sss_svlog_compare` specifically:**
- **Subsets are (side, range, bins, gain_index).** The markdown table shows only the 3
  largest per file (`--max-subsets`), and `compare.json` has all of them. Compare
  like-for-like subsets, at the same gain.
- **Levels are averaged over every altitude in the file.** A slant-range dB profile
  depends on altitude, so a single-altitude comparison mistakes a slope for an offset.
  Compare files at similar altitude, or use `calibration_cli`, which bands by altitude.
  Checking the model needs the **two** anchors `bath3` (1.40 m) and
  `reflectionEvidenceFullharbour` (7.33 m).
- **Texture depends on the acquisition.** The along-range lag-1 correlation is 0.29 at
  600 bins / 0.002 and 0.46 at 1200 / 0.00125. It is also measured after subtracting the
  subset's mean range profile, so seabed structure counts as texture. Only compare the
  same `num_results` and pulse.
- **`pulse_law_us` is a reference, not a check.** It assumes 1.2 sample periods at 600
  bins and 1.5 otherwise; a frame does not carry `pulse_len_percent`. A 600-bin SonarView
  file (pulse 0.0025) reads as a mismatch it isn't. The device law is
  `max(44.3 µs, pulse_len_percent × 2R/c)`.
- **"Counter resets" and "% of port stamps also on starboard" are simulator tells, not
  defects.** A re-enable restarts the simulator's counter, and both simulated sides stamp
  from one tick.
- **Power statistics use every 3rd ping** (`--stride 3`); timing uses all of them.
- `python3 -m …svlog_compare` prints a runpy `RuntimeWarning`, because the package
  `__init__` imports the module. It is harmless.
- **Ping period is read off `timestamp_ms`.** A simulated log stamps simulation time, and
  a simulated session can show 60 ms where the device law says 50.

## Corpus map

`~/ros2_ws/data/SSS_data`, read-only. Measured with the digest on 2026-09-28.

| File | Acquisition | Notes |
|---|---|---|
| `beach_sept/bath1-3.svlog` | 20 m / 600, 66.5 µs (SonarView 1.5/N) | bottom at 0.9–1.4 m, live clock; `bath3` is the 1.40 m calibration anchor |
| `beach_sept/object_*.svlog` | 1200 bins, 44.3 µs, ranges changing within the file | the NAFCO box: `object_boiteVsDistance` (19.711 / 39.943 m) |
| `reflectionEvidenceFullharbour.svlog` | 40 m / 600, 106.4 µs (ROS driver 0.002) | the 7.33 m calibration anchor; **frozen clock**; `channel_number` 255 on 6 516 packets |
| `MainReflectionEvidence+misspingsWaterfall.svlog` | 80 m / 600, 212.8 µs | the sea trial, frozen clock, ping loss |
| `DiffSV-US_whenDepthCompensation.svlog` | 40 m / 600, 106.4 µs | frozen clock |
| `diffDepthCompensation.svlog` | 20 → 35.3 m / 600, 66.5 µs | SonarView; the transmit-ringing anchor |
| `fullHarbourCleanExample.svlog` | 95.6 / 125.6 m / 1200, 159.6 µs | harbour survey (SonarView); the quay anchor for `wall_contrast` |
| `OneLineHarbourClean70m.svlog`, `toOptimize-harbourScan.svlog` | 1200 bins | harbour |
| `sessions/<stamp>/*.svlog` | whatever the run used | GCS recording sessions, simulated or real, with the session's `seabed_images/`, `mosaic/`, `waterfall/` |

The simulator's smoke section `[2f]` is gated on this corpus (`$BLUEBOAT_SSS_CORPUS`).
The BlueBoat-SSS corpus tests look for a different, hard-coded external mount and skip
without it.
