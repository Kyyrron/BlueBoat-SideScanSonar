"""Side-scan sonar renderers.

:class:`SonarRenderer` is the replaceable-backend interface: it turns a
sensor pose + a :class:`~blueboat_sss_sim.worldgen.scene.SceneModel` into one
:class:`~blueboat_sss_sim.core.types.RenderedPing` per side. Everything above
it (ROS node, encoder, dataset tooling) depends only on this interface, so
a GPU / tube-tracing / learning-based backend can be dropped in later.

:class:`GeometricRenderer` (v1) implements the classic heightfield SSS
model used across the synthetic-SSS literature (KTH draping line, UUV
simulator lineage):

1. Sample the seabed along the athwartship ground line of the ping.
2. Compute slant range, depression angle and local incidence per sample.
3. **Horizon culling** gives acoustic shadows: a sample is insonified only
   if its elevation angle (seen from the transducer) exceeds the running
   maximum of all nearer samples. Proud objects therefore cast
   geometrically correct shadows for free, and the nadir water-column gap
   appears naturally because no seabed sample has slant range < altitude.
4. Weight by material backscatter (Lambertian), vertical beam pattern
   (riding on vehicle roll -- the USV surface-motion signature), and the
   residual range response after idealised TVG.
5. Accumulate into ``num_results`` slant-range bins.

Known simplifications (see docs/sonar_model.md for the full list):
straight rays, no multipath, single-bounce, static scene, along-track
beam treated as a delta (one ground line per ping).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

import numpy as np

from ..core.types import (GroundTruthContact, Ping, Pose3D, RenderedPing,
                          Side)
from ..worldgen.objects import CATALOG
from ..worldgen.scene import SceneModel
from . import acoustics
from .config import AcquisitionParams, SonarModelConfig


class SonarRenderer(abc.ABC):
    """Backend interface: pose -> one rendered ping for one side."""

    @abc.abstractmethod
    def render(self, side: Side, vehicle_pose: Pose3D, t_sim: float) -> RenderedPing:
        """Render one noiseless ping (noise is applied by the caller so that
        renderers stay deterministic and comparable)."""


@dataclass
class _PingGeometry:
    """Intermediate per-ping geometry, kept for testability."""

    slant: np.ndarray            # slant range per ground sample [m]
    visible: np.ndarray          # bool, horizon-culling result
    depression: np.ndarray      # ray depression angle below horizontal [rad]
    cos_incidence: np.ndarray
    reflectivity: np.ndarray
    altitude: float


class GeometricRenderer(SonarRenderer):
    """Heightfield ray model with horizon-culling shadows (see module doc)."""

    def __init__(self, scene: SceneModel, acquisition: AcquisitionParams,
                 model: SonarModelConfig) -> None:
        self._scene = scene
        self._acq = acquisition
        self._cfg = model

    # ------------------------------------------------------------------ API
    def render(self, side: Side, vehicle_pose: Pose3D, t_sim: float) -> RenderedPing:
        sensor = self._sensor_pose(side, vehicle_pose)
        geom = self._ping_geometry(side, sensor)
        power = self._shade(geom, side, sensor)
        ping = Ping(
            side=side,
            power=power,
            pose=sensor,
            altitude_m=geom.altitude,
            t_sim=t_sim,
            start_mm=self._acq.range_start_mm,
            length_mm=self._acq.range_length_mm,
        )
        contacts = self._ground_truth_contacts(side, sensor, geom)
        return RenderedPing(ping=ping, contacts=contacts)

    # ------------------------------------------------------ sensor mounting
    def _sensor_pose(self, side: Side, p: Pose3D) -> Pose3D:
        """Vehicle base pose -> transducer pose (rigid mount offset)."""
        cfg = self._cfg
        c, s = np.cos(p.yaw), np.sin(p.yaw)
        ox = cfg.mount_x_m
        oy = side.sign * cfg.mount_y_abs_m
        return Pose3D(
            x=p.x + c * ox - s * oy,
            y=p.y + s * ox + c * oy,
            z=p.z - cfg.sensor_depth_m,
            roll=p.roll, pitch=p.pitch, yaw=p.yaw,
        )

    # --------------------------------------------------------- geometry pass
    def _ping_geometry(self, side: Side, sensor: Pose3D) -> _PingGeometry:
        acq, cfg = self._acq, self._cfg
        r_max = acq.range_max_m

        # Athwartship look direction in the world frame.
        look = sensor.yaw + side.sign * np.pi / 2.0
        dx, dy = np.cos(look), np.sin(look)

        # Ground-line samples (horizontal distance y_k from the transducer).
        ds = max(cfg.sample_step_m, self._scene.grid.resolution * 0.5)
        y_k = np.arange(ds, r_max + ds, ds)
        px = sensor.x + dx * y_k
        py = sensor.y + dy * y_k

        z_k = self._scene.sample_height(px, py)
        rho = self._scene.sample_reflectivity(px, py)

        dz = sensor.z - z_k                      # positive: seabed below sensor
        slant = np.hypot(y_k, dz)
        depression = np.arctan2(dz, y_k)         # 0 horizontal .. pi/2 nadir

        # Horizon culling: elevation angle (negative-down) must exceed the
        # running max of nearer samples to be insonified.
        elevation = -depression
        run_max = np.maximum.accumulate(elevation)
        visible = elevation >= run_max - 1e-9

        # Local incidence from the along-profile slope.
        slope = np.gradient(z_k, ds)
        # Ray direction (horizontal, vertical) = (y_k, -dz)/slant; surface
        # normal (2D profile) = (-slope, 1)/sqrt(1+slope^2).
        denom = slant * np.sqrt(1.0 + slope ** 2)
        cos_inc = np.clip((dz + y_k * slope) / np.maximum(denom, 1e-9), 0.0, 1.0)

        altitude = float(sensor.z - self._scene.sample_height(
            np.array([sensor.x]), np.array([sensor.y]))[0])

        return _PingGeometry(slant=slant, visible=visible,
                             depression=depression, cos_incidence=cos_inc,
                             reflectivity=rho, altitude=max(altitude, 0.05))

    # ----------------------------------------------------------- shading pass
    def _shade(self, g: _PingGeometry, side: Side, sensor: Pose3D) -> np.ndarray:
        acq, cfg = self._acq, self._cfg

        roll_toward_side = -side.sign * sensor.roll  # roll pushing fan down
        bs = acoustics.backscatter(g.reflectivity, g.cos_incidence,
                                   cfg.lambert_exponent)
        w = acoustics.beam_weight(g.depression, cfg, roll_toward_side)
        rng_resp = acoustics.net_range_response(g.slant, cfg)

        contrib = bs * w * rng_resp * g.visible

        # Bin by slant range.
        start_m = acq.range_start_mm / 1000.0
        bin_m = acq.bin_size_m
        idx = np.floor((g.slant - start_m) / bin_m).astype(np.int64)
        ok = (idx >= 0) & (idx < acq.num_results)
        power = np.bincount(idx[ok], weights=contrib[ok],
                            minlength=acq.num_results).astype(np.float64)

        # Normalise by samples-per-bin so power is footprint-independent.
        counts = np.bincount(idx[ok], minlength=acq.num_results)
        power = np.where(counts > 0, power / np.maximum(counts, 1), 0.0)
        return power

    # ------------------------------------------------------------ ground truth
    def _ground_truth_contacts(self, side: Side, sensor: Pose3D,
                               g: _PingGeometry) -> list[GroundTruthContact]:
        """Which scene objects does *this* ping insonify, and where?

        An object is 'in this ping' if its centre lies within half the
        along-track resolution cell (beam footprint + object length) of the
        ping's ground line. Shadow length uses the classic flat-bottom
        approximation  L_s = h_obj * r / altitude."""
        acq, cfg = self._acq, self._cfg
        contacts: list[GroundTruthContact] = []
        look = sensor.yaw + side.sign * np.pi / 2.0
        dxl, dyl = np.cos(look), np.sin(look)
        fwd_x, fwd_y = np.cos(sensor.yaw), np.sin(sensor.yaw)
        half_beam = np.radians(cfg.horizontal_aperture_deg) / 2.0

        for o in self._scene.objects:
            rx, ry = o.x - sensor.x, o.y - sensor.y
            across = rx * dxl + ry * dyl          # >0: on this side
            along = rx * fwd_x + ry * fwd_y
            if across <= 0.2 or across > acq.range_max_m:
                continue
            footprint_along = across * np.tan(half_beam) + o.footprint_radius
            if abs(along) > footprint_along:
                continue

            z_obj = float(self._scene.sample_height(np.array([o.x]),
                                                    np.array([o.y]))[0])
            slant = float(np.hypot(across, sensor.z - z_obj))
            if slant > acq.range_max_m:
                continue

            # Occlusion check against rendered visibility near the object.
            ds = g.slant[1] - g.slant[0] if len(g.slant) > 1 else 0.05
            k = int(np.clip(round(across / max(cfg.sample_step_m,
                                               self._scene.grid.resolution * 0.5)) - 1,
                            0, len(g.visible) - 1))
            k0, k1 = max(0, k - 3), min(len(g.visible), k + 4)
            visible = bool(g.visible[k0:k1].any()) and o.effective_height > 0.005

            bin_m = acq.bin_size_m
            extent_bins = max(o.footprint_radius * 2.0, bin_m) / bin_m
            shadow_m = o.effective_height * slant / max(g.altitude, 0.1)
            contacts.append(GroundTruthContact(
                object_id=o.object_id, object_type=o.type, side=side,
                slant_range_m=slant, extent_bins=float(extent_bins),
                shadow_bins=float(shadow_m / bin_m), visible=visible))
        return contacts
