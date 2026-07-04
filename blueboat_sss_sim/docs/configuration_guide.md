# Configuration guide

Three YAML layers, all with realistic defaults so an empty file works:

1. **World** (`config/default_world.yaml`) — terrain, materials, objects.
2. **Sonar** (`config/default_sonar.yaml`) — acquisition + physics/noise.
3. **Mission** (`config/default_mission.yaml`) — binds a world, a pattern
   and a sonar profile into one reproducible run bundle; may override
   world sections inline.

Unknown keys in the sonar `model:` section raise immediately (typo
protection); world/mission sections ignore unknown keys.

## 1. World config

```yaml
world:
  seed: 42                # every stochastic choice derives from this
  size: [80.0, 60.0]      # m
  origin: [-40.0, -30.0]  # world xy of min corner
  resolution: 0.10        # raster cell, m — keep ≤ half a range bin
```

### terrain

| Key | Default | Effect |
|---|---|---|
| `base_depth` | 4.0 | mean depth (m); the shallow-regime dial |
| `slope.direction_deg`, `slope.grade` | 15, 0.015 | planar tilt |
| `dunes.{enabled, wavelength, amplitude, direction_deg, irregularity}` | on, 6, 0.12, 30, 0.5 | sand-wave field; irregularity 0 = pure sine |
| `roughness.{amplitude, octaves, cells}` | 0.05, 5, 12 | fBm micro-relief |
| `materials.layout` | `patches` | `uniform` (one material) or fBm-rank patches |
| `materials.composition` | sand-dominant mix | area fractions, auto-normalized |
| `materials.patch_cells` | 6 | patch spatial scale |

### objects

| Key | Default | Effect |
|---|---|---|
| `density_per_hectare` | 60 | expected object count / ha |
| `composition` | catalog defaults | relative weights per type (13 types: `tire_car`, `tire_bicycle`, `pipe_pvc`, `bottle_glass`, `bottle_plastic`, `can`, `tent_weight`, `rope`, `cylinder_metal`, `block_concrete`, `brick`, `chain`, `anchor`, `debris`) |
| `margin_m`, `min_separation_m` | 3.0, 1.0 | placement constraints (dart throwing) |
| `size_scale`, `burial_scale` | 1.0 | global multipliers on per-type priors |
| `reflectivity_jitter` | 0.15 | per-instance acoustic variation |
| `overrides.<type>` | — | per-type priors (`length_range`, `burial_range`, …) |

### materials (optional, or `config/materials.yaml`)

Per material: `reflectivity` (0–1 mean backscatter), `texture_amp`,
`texture_cells`, `micro_roughness_m`, `lambert_exp`, `color` (visual only).
Built-ins: seabed `sand/mud/gravel/rocks/seagrass`; object
`rubber/pvc/plastic/glass/metal/concrete/brickclay/rope/generic`.

## 2. Sonar config

`acquisition:` mirrors the six real ROS parameters — see
`docs/topics.md §2`; changing them here changes the launch-time defaults,
and they can still be overridden per run via ROS parameters, exactly like
on the real system.

`model:` (no hardware equivalent):

| Group | Keys | Guidance |
|---|---|---|
| Mounting | `sensor_depth_m`, `mount_x_m`, `mount_y_abs_m`, `beam_tilt_deg` (20), `vertical_aperture_deg` (55), `horizontal_aperture_deg` (0.5) | match the physical bracket; tilt+aperture set the usable swath |
| Acoustics | `lambert_exponent` (1.7), `absorption_db_per_m` (0.10 @450 kHz), `spreading_exponent` (2.0), `tvg_compensation` (0.90) | raise `tvg_compensation` → flatter image |
| Calibration | `calibration_db_offset` (16), `base_scale` (18000), `gain_index_step_db` (3) | match real u16 levels / dB reporting |
| Noise | `speckle` (true), `noise_floor` (0.004), `gain_drift_amp` (0.06), `gain_drift_period_s` (45), `dropped_ping_prob` (0.003), `watercolumn_noise` (0.02) | zero everything for "clean physics" ablation images |
| Sampling | `sample_step_m` (0.05) | renderer ground-sample step; smaller = finer shadows, slower |

## 3. Mission config

```yaml
mission:
  seed: 7
  randomize: false        # true → draw seed/density/pattern per bundle
  world_config: config/default_world.yaml
  sonar_profile: config/default_sonar.yaml
  gazebo_plugin_prefix: ignition   # or gz
  pattern: lawnmower               # lawnmower | spiral | random | waypoints
  lawnmower: {bbox: [-30,-20,30,20], spacing: 8.0, speed: 1.0, heading_deg: 0}
  spiral:    {center: [0,0], r_max: 25.0, spacing: 8.0, speed: 1.0}
  random:    {bbox: [-30,-20,30,20], n_legs: 14, speed: 1.0}
  # waypoints: {points: [[...]], speed: 1.0}

world_overrides:          # section-wise merge onto world_config
  objects: {density_per_hectare: 90}
```

Choose `spacing` < 2 × usable swath (≈ `range_length_mm`·cos-projection −
nadir gap) for full coverage; the 8 m default gives generous overlap at
the 15 m / 4 m-depth defaults.

## 4. Dataset recorder parameters

`output_dir` (required), `tile_pings` (512), `overlap_pings` (64),
`box_mode` `highlight|highlight_shadow` (default includes the shadow —
usually the stronger detector cue), `val_fraction` (0.15, deterministic
hash split), `autosave_period_s` (5), `run_name` (tile prefix).
