# BlueBoat GCS — Architecture

Desktop application replacing `processed_sss_listener.py` as the single software used
during sea experiments. Python + PySide6 + rclpy + NumPy + OpenCV, nothing else.

## 1. Big picture

```
                    ROS thread                          GUI thread (Qt event loop)
 ┌────────────────────────────────────┐   queued    ┌─────────────────────────────────────┐
 │ rclpy node "blueboat_gcs"          │   signals   │                                     │
 │  ros/sonar_listener      ──────────┼────────────►│ core/mosaic_service                 │
 │  ros/telemetry_listener  ──────────┼────────────►│   MosaicGrid (reused) ── 4 Hz ──►   │
 │  ros/detections_listener (plchldr) ┼────────────►│   MosaicRenderer → QImage           │
 │  ros/pinger_listener     (plchldr) ┼────────────►│ gui/main_window (composition root)  │
 └────────────────────────────────────┘             │   gui/map_view (QGraphicsView,      │
 ┌────────────────────────────────────┐             │     scene in world metres)          │
 │ ros/pipeline_launcher              │◄────────────┤   gui/map_layers: tiles < mosaic <  │
 │  subprocess: ros2 launch           │  START/STOP │     trajectory < detections <       │
 │  SSS_processing_launch.py          │             │     pinger < measure                │
 └────────────────────────────────────┘             │   left/right panels, toolbar        │
 ┌────────────────────────────────────┐             └─────────────────────────────────────┘
 │ sim/simulator (--sim, no ROS)      ┼──────► same signals, same models
 └────────────────────────────────────┘
```

## 2. Key design decisions and why

### 2.1 Single signal bus, single-threaded data ownership
All data sources (ROS listeners, simulator, launcher) publish plain dataclasses on
`core/signals.AppSignals`. Because the emitters run in non-GUI threads, Qt delivers
these signals as **queued connections**: every consumer slot executes in the GUI
thread. Consequences:

* the mosaic grid, trajectory buffers and every `QGraphicsItem` are touched by exactly
  one thread → **no locks, no races, no flicker**;
* the ROS/Qt boundary is exactly one file per topic (`ros/*_listener.py`), each
  converting a ROS message into a ROS-free model (`models/`). Everything past the bus
  is testable without ROS — which is how the `--sim` mode works.

**Extending with a new topic** = add a model in `models/`, a `Signal` in
`core/signals.py`, a listener in `ros/`, and one `connect()` in
`gui/main_window._connect_signals`. Nothing else changes.

### 2.2 Ingestion decoupled from rendering
The old listener redrew matplotlib figures inside the subscription callback. Here:

* per ping (~28 Hz): `project_to_world` + `MosaicGrid.add_samples` — a vectorised
  scatter-add, sub-millisecond;
* on a 4 Hz `QTimer` (configurable): if the grid is dirty, render mean intensities to a
  `QImage` and swap the pixmap of the existing mosaic item.

The GUI stays smooth regardless of ping rate, and a raster refresh is an atomic pixmap
swap → no flicker.

### 2.3 QGraphicsView with a world-metres scene
The scene coordinate system *is* the local odom frame (with `scene.y = -world.y` so
North-ish is up). Pan/zoom are native view transforms; click → world coordinates is
`mapToScene`; every overlay is an independent item with a z-value:

`tiles (-20) < mosaic (0) < planned path (5) < swath line (8) < trajectory (10) < robot (15) < detections (20) < pinger (25) < measure (30)`

Satellite imagery is therefore structurally *below* the SSS data, which stays the
primary layer. Visibility toggles are `item.setVisible()`. The grid overlay is drawn in
`drawForeground` with adaptive spacing (0.5 m → 1 km depending on zoom).

### 2.4 GPS strategy — one origin, on-demand conversion
`ProcessedSSSPing` carries local coordinates only, and the specification explicitly
warns against per-pixel GPS computation. `mapping/coordinate_converter.py` binds one
origin `(x0, y0) ↔ (lat0, lon0)` from the first `RobotState` that has both a local pose
and a GPS fix (mavros local frame is ENU, so the default local→ENU rotation is
identity; `map.frame_yaw_offset_deg` overrides it). GPS is then computed only for:
clicked points, measurement endpoints, the robot info panel, and tile placement. The
mosaic itself never leaves the metric frame. The equirectangular math is the existing
`math_helper.enu_to_gps`, made bidirectional.

### 2.5 Reuse of the existing code
* `MosaicGrid` and `project_to_world` → `mapping/mosaic.py`, algorithm unchanged
  (`save()` swaps matplotlib for OpenCV; the `.npz` keys are byte-compatible with the
  legacy listener output, so existing analysis scripts keep working).
* The processing logic of `processed_sss_listener._on_processed_ping` (side merging via
  the sign of `y_local`, yaw extraction, depth/trajectory logging, cell size, percentile
  contrast) is ported 1:1 across `ros/sonar_listener.py`, `core/mosaic_service.py` and
  `mapping/renderer.py`.
* `sss_node.py`, `sss_processor_node.py`, `svlog_helper.py` are untouched; the app is a
  pure consumer of `/sss_processor/processed` and of the existing enable topics.
* The geodesy/quaternion math of `math_helper.py` lives on in `utils/geodesy.py`
  (ROS-message-free so the mapping layer has no ROS dependency).

### 2.6 Acquisition control
`ros/pipeline_launcher.py` runs `ros2 launch blueboat_sss SSS_processing_launch.py`
(new launch file, processor node only — the app **never** starts `sss_node.py`, which
runs on the robot) in its own process group. START additionally publishes `true` on
`/side_scan_sonar/ping/enable` and `/sss_processor/log/enable` after a bring-up delay;
STOP publishes `false`, SIGINTs the launch group, escalates to SIGKILL after a grace
period, and saves the mosaic + trajectory to `data/SSS_data/<date>/` (same artifacts as
the legacy listener). All behaviour is configurable in `config/default.yaml`.

### 2.7 Background tiles without new dependencies
`mapping/tiles.py` implements slippy-map math and an async fetcher on Qt's own
`QNetworkAccessManager`, with a persistent disk cache (`~/.cache/blueboat_gcs/tiles`) —
browse the survey area once at the dock and the imagery works offline at sea. Tiles are
positioned by converting their corner lat/lon into the local frame; at harbour scale the
residual Mercator/equirectangular disagreement is far below a pixel. Esri World Imagery
by default (satellite), OSM as the alternative (`map.use_satellite`).

### 2.8 Interpolation (see also HANDOVER §5)
`mapping/interpolation.py` operates **at render time only**: empty cells within
`max_gap_m` of measured cells (distance transform) are filled by a normalized box
convolution of valid neighbours, with a `min_neighbors` acceptance test. The grid's
`(sum, count)` arrays and the saved `.npz` are never modified → reversible by
construction, large unmapped regions stay empty by construction.

### 2.9 Simulator as executable specification
`sim/simulator.py` (`--sim`) emits the same models on the same bus: lawnmower survey,
textured seabed with bright targets + shadows, detections, a pinger fix and the
planned mission path. It exists to (a) develop/demo the GUI with no ROS and no boat,
and (b) pin down the exact contract the placeholder streams must satisfy.

### 2.10 Waterfall view (update)
The waterfall is *not* a map layer: its axes are ping index × across-track distance —
the raw acquisition domain used for future AI datasets — so it gets its own numpy ring
buffer (`core/waterfall_service.py`) and widget (`gui/waterfall_view.py`) instead of
being forced into the georeferenced scene. The central widget is a `QStackedWidget`
switching between MapView and WaterfallView; the inactive view's raster pipeline is
paused. Both views share the same `MosaicRenderer`/`DisplaySettings` value→pixel
pipeline, so the display controls behave identically everywhere.

### 2.11 Display controls & rendering priorities (update)
`DisplaySettings` (`mapping/renderer.py`) carries the SonarView-like operator
controls: colormap, auto (2–98 %) vs. manual dynamic-range window, gamma contrast,
brightness. It only maps values to pixels — raw grids/buffers are never modified.
Where survey lines overlap, the mosaic cell policy is selectable
(`MosaicGrid.PRIORITY_MODES`): *Average* (original running mean), *Closest* (smallest
slant range wins — SonarView default), *Oldest*, *Newest*. All planes are maintained
simultaneously on ingestion (~24 B/cell), so switching is instant and lossless; new
policies = one more plane in `add_samples`. The saved `.npz` keeps the legacy keys and
adds the three priority planes.

### 2.12 Professional-quality mosaic rasterization (update)
**Analysis.** The original mosaic scattered each raw sample into exactly one 25 cm
cell and averaged. Professional packages (SonarView, SonarWiz, HYPACK) instead treat
the waterfall as a continuous image draped onto the seabed: consecutive pings define
thin quadrilaterals rasterized with bilinear interpolation onto the grid (Blondel,
*The Handbook of Sidescan Sonar*, Springer 2009, ch. 5; Cervenka & de Moustier,
"Sidescan sonar image processing techniques", IEEE J. Oceanic Eng. 18(2), 1993).
Point-scatter therefore produced exactly the observed artefacts: nearest-cell
aliasing (jagged edges), fan-shaped holes in turns, and texture that is
simultaneously over-averaged and blocky.

**Chosen strategy** (`mapping/rasterizer.py` + bilinear splatting in
`mapping/mosaic.py`): (1) across-track resampling of each side to cell/2 spacing;
(2) along-track virtual pings — pose lerp + shortest-arc yaw + intensity cross-fade —
until the *swath tip* moves less than cell/2, which evaluates the interior of the
SonarWiz-style quad and closes turn fans by construction; (3) bilinear splatting (the
adjoint of bilinear interpolation = anti-aliased accumulation) for the mean plane,
while priority planes and hit counts keep nearest-cell single-measurement semantics.
Interpolation only ever spans one ping/sample interval between two real measurements
— resampling, not inpainting — and is disabled across pose discontinuities
(dropouts, restarts). Rejected alternative: textured-quad rendering in the scene
graph, which would couple perception data to Qt and break the "grid in, raster out"
modularity; the densification approach is mathematically equivalent on the grid.

**Measured** on a synthetic survey with a U-turn at worst-case ping spacing:
uncovered cells inside the swath 10.6 % → 1.0 % (remainder = genuine nadir gap),
turn-region coverage ×2.1, gradient noise p95 −17 % with target edges preserved;
cost 0.43 ms per full-resolution ping (28 Hz required, ~2300 Hz capacity).
`mosaic.densify` / `mosaic.bilinear_splat` restore the legacy path for A/B studies.

### 2.13 Acquisition lifecycle, recording sessions & console (update)
Lifecycle: the processing pipeline (`sss_processor_node`) is launched **at
application startup** by the launcher state machine
(IDLE→STARTING→RUNNING→STOPPING→IDLE/ERROR, SIGINT→SIGTERM→SIGKILL escalation,
unconditional leftover sweep via pgrep patterns). **START** only enables pinging +
the live-visualization gate (no node restart); **STOP** disables pinging, closes an
active recording session and terminates the nodes (START relaunches them).
Visualization layers all start disabled. Recording is independent: **Record ON**
publishes log_enable and opens a session; **Record OFF** (or STOP / app close)
finalizes one self-contained folder (mosaic, waterfall raw+PNG, trajectory,
detections, adopted .svlog, metadata.json). Nothing is exported unless a session was
active.

The embedded console (`gui/log_console.py`, bottom dock, toolbar toggle) shows
everything textual so no external terminal is needed: `core/logging_bus.py` tees
stdout/stderr + the `logging` module; `ros_manager` subscribes `/rosout`
(rcl_interfaces/Log — logger output of *all* nodes incl. the processor); the
launcher pumps the launch subprocess's raw stdout/stderr through a reader thread.

Live plots: `gui/live_plot.py` is a reusable bounded scrolling y(t) widget (deque +
paintEvent, repaint coalescing, autoscale hysteresis); "Robot Altitude" (fed by
`water_depth` of each ProcessedSSSPing) is its first instance — future plots are one
more instance + one signal connection.

### 2.14 Robot-state robustness (update)
Three independent layers guarantee the displayed pose always re-syncs after
localization dropouts: (1) telemetry throttling uses the **wall clock**, never
message stamps (replayed/sim stamps that jump backwards previously froze the robot
until the stamps "returned"); (2) the staleness watchdog dims the marker and arms a
trajectory break after 3 s without RobotState, whether or not START is involved;
(3) `TrajectoryLayer.add_pose` starts a new polyline segment on any pose jump
> 5 m — a stateless safety net, so recovery (teleporting arrow, no phantom line)
cannot depend on any state machine being in the right state.

## 3. Module map

| Path | Responsibility |
|---|---|
| `main.py` | argparse, Qt app, dependency wiring, `--sim` switch |
| `config/settings.py`, `config/default.yaml` | typed config; YAML overrides; unknown keys fail loudly |
| `core/signals.py` | the signal bus (§2.1) |
| `core/mosaic_service.py` | ping ingestion (via rasterizer), priority mode, throttled rendering, clear, save |
| `core/waterfall_service.py` | ring buffer of raw pings, throttled waterfall rendering, clear, export |
| `core/recording_session.py` | recording sessions: one experiment = one folder |
| `core/logging_bus.py` | stdout/stderr/logging capture -> embedded console |
| `models/` | ROS-free dataclasses: `SonarPing`, `RobotState`, `Detection`, `PingerFix`, `PlannedPath` |
| `ros/ros_manager.py` | rclpy lifecycle in a background thread; enable-topic publishers; graceful no-ROS degradation |
| `ros/sonar_listener.py` | `/sss_processor/processed` → `SonarPing` |
| `ros/telemetry_listener.py` | odom + NavSatFix + compass + VfrHud → `RobotState` (5 Hz) |
| `ros/detections_listener.py` | **placeholder** — AI detections integration point |
| `ros/pinger_listener.py` | USBL pinger (Float32MultiArray [x, y] on /blueboat/pinger_coordinates) |
| `ros/path_listener.py` | planned mission path (`nav_msgs/Path` from path_publisher.py) |
| `ros/pipeline_launcher.py` | acquisition state machine, shutdown escalation, leftover sweep |
| `mapping/mosaic.py` | reused `MosaicGrid` + `project_to_world` + priority planes + bilinear splat |
| `mapping/rasterizer.py` | across/along-track ping densification (SonarView-grade mosaics) |
| `mapping/renderer.py` | raster → RGBA `QImage`; `DisplaySettings` (LUTs, range, gamma) |
| `mapping/interpolation.py` | render-time small-gap fill |
| `mapping/coordinate_converter.py` | local ↔ GPS |
| `mapping/tiles.py` | slippy math + async cached tile fetcher |
| `gui/main_window.py` | composition root; all wiring |
| `gui/map_view.py` | pan/zoom/click/measure; adaptive grid |
| `gui/map_layers.py` | tile/mosaic/planned-path/swath/trajectory/detection/pinger/measure layers |
| `gui/waterfall_view.py` | interactive waterfall (zoom / scroll / pin-to-newest) |
| `gui/log_console.py` | embedded application console (bottom dock) |
| `gui/live_plot.py` | reusable real-time scrolling plot ("Robot Altitude", …) |
| `gui/left_panel.py`, `gui/right_panel.py`, `gui/toolbar.py`, `gui/widgets.py`, `gui/theme.py` | panels, tools, dark theme |
| `sim/simulator.py` | ROS-free data source |
| `launch/SSS_processing_launch.py` | processor-only launch file for START |

## 4. Running

```bash
# bench / demo, no ROS required
python -m blueboat_gcs.main --sim

# field, on the basestation (blueboat_interfaces sourced)
python -m blueboat_gcs.main
python -m blueboat_gcs.main --config my_site.yaml
```
