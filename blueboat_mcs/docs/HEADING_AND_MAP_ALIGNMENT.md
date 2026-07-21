# Heading & Map Alignment — why the glyph pointed wrong, and the fix

Short, self-contained note. Applies to any app that draws a robot on a map
from odometry while also having GPS. Reusable outside this project.

## The core misunderstanding

There are **two different frames**, and they are rotated relative to each
other by an angle nobody told you about:

1. **World/odom frame** — the frame your `nav_msgs/Odometry` is in. Its
   origin and axes are decided by wherever the localization node started.
   Its `+x` is *not* east. `yaw` from odometry is measured in this frame.
2. **Geographic frame (ENU)** — east/north, i.e. the real world and the
   satellite tiles.

The rotation between them, call it **`theta`** (world `+x` axis, as a
bearing CCW from east), is unknown at startup. If you draw the robot using
odometry `yaw` directly on a north-up / tile-backed map, everything is off
by `theta`: the glyph heading is wrong and world coordinates don't line up
with the map. It looks like "a heading bug" but it is a **frame-alignment**
problem — the heading is just its most visible symptom.

## Why you cannot know `theta` at startup

`theta` is only observable once the vehicle **moves**: you compare how the
GPS track (in ENU) turns versus how the odom track (in world) turns. With
one stationary fix you know the *origin* (a translation) but not the
*rotation*. So there are two stages:

- **Translation-only (immediately):** from the first GPS fix you can place
  the map origin and show tiles. `theta = 0` is a placeholder — **do not
  trust heading yet.**
- **Rotation-aligned (after a few metres):** fit a rigid transform
  (Kabsch/Umeyama, scale = 1) between paired `(odom_xy, gps_en)` samples.
  Now `theta` is real and heading can be trusted.

## The fix (backend only)

In the georeferencer (`mcs/core/geo.py`):

- Emit a **translation-only `GeoFit` from the very first GPS fix** so
  `is_valid` is true immediately. This is what lets the satellite layer turn
  on "at the first sign of GPS" instead of waiting for motion.
- Add a **`heading_aligned`** flag: `False` for the translation-only fit,
  `True` once the Kabsch fit succeeds (enough motion, `min_spread_m`).
- Expose the alignment on `GeoFit`:
  - `world_heading_offset` → `theta` (add to a world-frame yaw).
  - `world_yaw_to_true(world_yaw)` → `world_yaw + theta`, normalised.

In the state store (`mcs/models/store.py`):

- `robot_true_heading()` returns the north-referenced heading
  (`world_yaw_to_true(yaw)`) once `heading_aligned`, else `None` so callers
  fall back to raw `yaw`.

Any map/view then aligns by rotating its rendering (or just the glyph) by
`theta`, using `robot_true_heading()` when available. The rule of thumb:

> Compute heading **after** you have both robot world info (odom `yaw`) **and**
> the odom↔GPS georeference — never from `yaw` alone.

## Guard rails

- Coordinate conversion that needs rotation (e.g. deploying a GPS-anchored
  mission into the current world frame) must **refuse a fit that is not
  `heading_aligned`** and retry — otherwise it silently rotates everything
  by the placeholder `theta = 0`.
- A manually entered GPS origin (no live GPS) is a *declared* frame: treat
  its rotation as given, not as heading-aligned evidence.

## One-paragraph recipe for the other app

Keep two fit stages. Turn tiles on as soon as you have any GPS fix
(translation-only). Keep a boolean that says whether rotation has been
solved yet. Only rotate/interpret heading once that boolean is true; until
then draw the glyph from raw yaw and label the heading as "north not yet
aligned". Solve rotation by fitting odom-vs-GPS tracks after the vehicle has
moved a few metres. The offset you get is the single number that aligns
heading *and* coordinates *and* tiles at once.
