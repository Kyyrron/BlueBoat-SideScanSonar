# BlueBoat GCS — Handover

## 1. What you received

A complete PySide6 desktop application (`blueboat_gcs/`) replacing
`processed_sss_listener.py`, plus a new launch file
(`launch/SSS_processing_launch.py`) and this documentation. The app runs today in two
modes:

* `python -m blueboat_gcs.main --sim` — full GUI with a built-in simulator, no ROS;
* `python -m blueboat_gcs.main` — field mode, subscribing to the real topics.

Field prerequisites: `blueboat_interfaces` sourced in the environment; the robot-side
`sss_node.py` running (pinging off — START enables it); `pip install PySide6 pyyaml
opencv-python` on the basestation.

## 2. Consumed topics (already implemented, no work needed)

| Topic (config key in `config/default.yaml`) | Type | Rate | Used for |
|---|---|---|---|
| `/sss_processor/processed` (`topics.processed_ping`) | `blueboat_interfaces/ProcessedSSSPing` | ~28 Hz | mosaic, depth, trajectory |
| `/blueboat/odom` (`topics.odom`) | `nav_msgs/Odometry` | ~20 Hz | robot pose/track (throttled to 5 Hz in GUI) |
| `/mavros/global_position/global` (`topics.navsat`) | `sensor_msgs/NavSatFix` | ~5 Hz | GPS origin binding + robot info |
| `/mavros/global_position/compass_hdg` (`topics.compass_hdg`) | `std_msgs/Float64` (deg) | ~10 Hz | heading display |
| `/mavros/vfr_hud` (`topics.vfr_hud`) | `mavros_msgs/VfrHud` | ~4 Hz | ground speed (optional; falls back to odom twist if `mavros_msgs` absent) |
| `/set_path` (`topics.planned_path`) | `nav_msgs/Path` | ~1 Hz | planned mission path overlay (same message `path_publisher.py` sends to RViz; poses in the local odom frame; each message fully replaces the displayed path) |

Published control topics: `std_msgs/Bool` on `/side_scan_sonar/ping/enable`
(START → true, STOP → false) and `/sss_processor/log/enable`.

**Recording sessions (one experiment = one folder).** The toolbar's
"Start recording" button (enabled only while the pipeline is running) opens a
recording session: it publishes `true` once on the processor's log/enable topic
(equivalent to `ros2 topic pub --once /sss_processor/log/enable std_msgs/msg/Bool
'data: true'`) and starts session bookkeeping. **STOP acquisition ends the session**
(it always publishes `false`, closing the .svlog) and automatically assembles:

```
<data_root>/sessions/2026_07_08-14_02_31/
    metadata.json            # times, ping/detection counts, config snapshot,
                             # priority mode, display settings, adopted svlogs
    mosaic/
        sonar_mosaic.npz     # raw planes (legacy keys + closest/oldest/newest)
        sonar_mosaic.png     # quick-look through the display pipeline
        boat_trajectory.csv  # t_since_first_s, x_m, y_m, depth_m
    waterfall/
        waterfall.png        # quick-look
        waterfall_raw.npz    # untouched ping buffer -> AI dataset source
    detections/detections.csv
    svlog/*.svlog            # adopted from the processor (see note)
```

Processing scripts can treat any `sessions/*/` directory as a complete, closed
experiment. Note on the `.svlog`: it is written by `sss_processor_node` wherever that
node decides; after the session ends, every `*.svlog` under `data_root` whose mtime
falls inside the session window is *moved* into `svlog/`. If your processor writes
elsewhere, extend the sweep in `core/recording_session.py::_adopt_svlogs`. If no
recording session was active, STOP and application close export **nothing** — data
only leaves the application through recording sessions.

**Acquisition lifecycle (current workflow).** The processing pipeline is launched
automatically at application startup; all visualization layers start disabled and no
recording is active. **START** = enable pinging + live visualization (no node
restart). **Record ON/OFF** (toolbar toggle) = open / close-and-save a recording
session, fully independent from visualization. **STOP** (or closing the app) =
pinging off, active session closed and saved, ROS 2 nodes gracefully terminated
(SIGINT→SIGTERM→SIGKILL escalation with `pipeline.stop_grace_s` /
`pipeline.stop_term_grace_s`, then a sweep killing anything matching
`pipeline.leftover_process_patterns`, default `sss_processor_node`; the sweep also
runs at startup and before each relaunch). **If no recording session was active,
nothing is exported.** START after STOP relaunches the pipeline automatically.

**Embedded console.** The "Console" toolbar button opens the bottom console dock:
Python prints and app logging (via `core/logging_bus.py`), ROS 2 log messages from
every node via `/rosout`, and the raw stdout/stderr of the launch subprocess — the
operator never needs an external terminal. Removed control: the manual Min/Max dB
dynamic-range sliders are gone; real Omniscan data (uint16 `pwr_results`, per-gain
`min/max_pwr_db` e.g. +7…+64 dB) makes a fixed dB window meaningless, so the range is
always derived from data percentiles, with Contrast/Brightness/Colormap/Opacity as
the operator controls. Panel base width is `PANEL_MIN_WIDTH` in
`gui/main_window.py`.

## 3. Integration points

### 3.1 USBL pinger — `ros/pinger_listener.py` (now the real interface)
* Topic: `topics.pinger` (default `/blueboat/pinger_coordinates`)
* Type: `std_msgs/Float32MultiArray`, `data = [x_world, y_world]` in the world/odom
  frame [m]; extra elements ignored, NaN/short messages dropped.
* Any rate works (last fix displayed). The left panel shows live pinger world
  coordinates and the continuously updated robot↔pinger distance;
  `DEFAULT_ACCURACY_M` draws the dashed ring (no covariance in the message).

### 3.2 AI detections — `ros/detections_listener.py` (placeholder)
* Expected topic: `topics.detections` (default `/sss_ai/detections`)
* Expected type: `vision_msgs/Detection2DArray` with, per detection:
  `results[0].hypothesis.class_id` (class name), `.score` (confidence),
  `bbox.center.position.x/.y` = object position **in the local odom frame** [m],
  `bbox.size_x` = extent [m], `detections[i].id` = **stable uid** — republishing the
  same id after a revisit *updates* the marker and does not double-count it in the
  summary.
* Rate: event-driven. `vision_msgs` import is guarded; if the detection repo settles on
  a custom message, edit `_msg_to_detections()` only.

### 3.3 Future AI pipeline placement
The plan in `info.md` (feed local map patches to the detector) fits naturally as a
separate node subscribing to `/sss_processor/processed` (or to saved mosaic tiles) and
publishing `Detection2DArray` — the GUI needs no change. If you prefer in-process
inference on the basestation, add a `core/detector_service.py` consuming
`signals.sonar_ping` and emitting `signals.detection`; the bus makes both options
equivalent from the GUI's perspective.

## 4. Other integration notes

* **Frame alignment**: the converter assumes the odom frame is ENU (mavros
  convention). If your odom frame is heading-aligned at boot, set
  `map.frame_yaw_offset_deg` (this supersedes `math_helper.local_to_enu(yaw0)`).
* **Launch file installation**: add `launch/SSS_processing_launch.py` to the
  `blueboat_sss` package install rules, next to `SSS_launch.py`. The old
  `SSS_launch.py` remains valid for the legacy workflow; long-term, remove
  `processed_sss_listener.py` from it once the team has switched to the GCS.
* **Transducer offsets**: still `TODO = 0.0` in `sss_processor_node.py` — measure and
  fill before localization-accuracy experiments (C3); the GUI displays whatever the
  processor publishes.
* **Tile cache**: browse the experiment area once with internet (dock Wi-Fi); tiles are
  cached in `~/.cache/blueboat_gcs/tiles` and work offline at sea. Respect OSM/Esri
  usage terms for anything beyond research use.
* **Outputs**: STOP (and window close) writes `data/SSS_data/<date>/sonar_mosaic.npz`
  (same keys as before: `mean_intensity`, `count`, `cell_size_m`, `x0`, `y0`),
  `sonar_mosaic.png`, `boat_trajectory.csv` — drop-in compatible with existing scripts.

## 5. Interpolation: should the AI see interpolated images?

**Recommendation: no — run detection on raw mosaics only.** Reasons:

1. *Statistical integrity.* The gap fill is a local mean: it invents plausible but
   fictitious texture, smooths exactly the high-frequency content (highlight/shadow
   pairs) the detector keys on, and its footprint correlates with boat speed and turn
   geometry — a detector trained or evaluated on filled images learns artefacts of the
   survey pattern, not of the seabed.
2. *Thesis integrity.* Contribution C3 evaluates detector localization accuracy;
   interpolated cells have no measurement behind them, so any detection centred on a
   filled cell would contaminate the (detection, USBL ground truth) statistics. C5
   promises an open dataset of real sonar data; the `.npz` therefore always stores raw
   data, and this must stay true.
3. *Nothing is lost.* Small along-track gaps are sub-object-size at survey speed; a
   YOLO-class detector is robust to a few missing pixels, and the adaptive replanner's
   revisit pass fills genuine coverage holes with *real* data — which is the whole point
   of the thesis.

Use interpolation for what it is: a **display aid for the human operator** (and for
figures, clearly labelled). If you ever experiment with feeding filled patches to the
detector, `fill_small_gaps` returns the fill mask — log it alongside so interpolated
detections can be excluded from any accuracy statistic.

**Waterfall domain and AI datasets.** The Waterfall view (`View` selector, right
panel) displays raw pings stacked in acquisition order — the domain from which future
AI datasets will primarily be generated — and is now fully interactive (wheel zoom,
drag pan, vertical scrolling through the whole ring buffer; it follows the newest
ping while at the bottom and releases the moment you scroll into history). Its pixel
values go through the display pipeline for *viewing only*; for dataset generation use
the data upstream of any rendering: the per-ping `intensity_db`/`y_local` arrays from
`/sss_processor/processed`, or `waterfall/waterfall_raw.npz` in a recording session
(the untouched ring buffer). Interpolation never applies in the waterfall domain, and
the mosaic-side densification (`mapping/rasterizer.py`) only resamples between
adjacent real measurements — set `mosaic.densify: false` / `bilinear_splat: false`
for strictly legacy accumulation in A/B studies. The mosaic `.npz` keeps the legacy
keys and the `closest/oldest/newest` planes; `SSS opacity` and all other Display
controls are pure visualization and never touch stored data.

## 6. Suggested future improvements

* **Processor-side GPS**: add lat/lon (and roll/pitch) to `ProcessedSSSPing` so the
  mosaic could be georeferenced without the GUI-side origin binding, and to enable
  attitude-compensated projection (C4 / Lei et al. 2026 direction).
* **Rosbag replay tab**: the listeners already tolerate any publisher; a thin
  `ros2 bag play` wrapper in the toolbar would formalise post-mission review.
* **Dirty-rect rendering**: the 4 Hz full-raster render is fine to multi-km² at
  25 cm cells; if surveys grow past that, render only the changed bounding box.
* **Belief-grid / replanner layers**: when the adaptive replanner exists, its belief
  grid and planned waypoints are two more `map_layers` classes + two signals.
* **Click-to-export patch**: right-click → save the N×N metre raw patch around the
  cursor (useful for building the detection dataset).
* **Persist UI state** (checkboxes, last view, dock sizes) via `QSettings`.
