# Link Guardian — brings the boat back if the laptop link is lost

All our software runs on the laptop and steers the boat over the Base Station WiFi. If that link
drops, nothing steers the boat any more and it keeps its last thrust. The **Link Guardian** is a
Lua script on the boat's autopilot (ArduPilot Rover): when the laptop goes silent it stops the
thrusters, then drives the boat back along the path it came (or along a **safety way back** drawn
for the run, §2), and hands it back as soon as the laptop is heard again.

**ON by default in every real-robot session**, shown in the **GUARDIAN** box of MCS.
Tested on the real boat.

## 1. The parts

- `autopilot/link_guardian.lua`: the guardian, installed once on the autopilot (§3).
- `laptop/guardian.py`: its helper on the laptop. MCS starts `guardian.py watch` with every
  real-robot session; it switches the guardian ON, reports the **Guardian Home** (§2) and feeds
  the GUARDIAN box. Its other commands (`check`, `setup`, `on`, `off`, `reclaim`, `set_home`) are
  what the box's buttons call; `safety_load` / `safety_clear` are sent by MCS at START RUN / STOP RUN.
- `test/`: offline checks (no boat): `lua_harness.py` runs the real script against a simulated
  autopilot, `test_guardian_safety.py` checks `guardian.py`'s upload logic (§7).

The script decides that the laptop is gone by watching the heartbeat MAVROS sends once a second
(MAVLink system 1, component 191).

## 2. What happens, and when

**At session start** the guardian switches ON by itself and the autopilot is armed (so it can
drive the boat later). From then on the script records the boat's **trail**: one point every
2 m. Its first point is the **Guardian Home** (below).

**When the link drops**, counting from the last laptop heartbeat:

| After | The boat |
|---|---|
| 0 – 3 s | Nothing changes: the thrusters keep the laptop's last command. |
| **3 s** | **Thrusters to neutral**: zero thrust, the boat drifts to a stop (see below). |
| **15 s** | **Takeover**: the autopilot takes the thrusters, arms itself if needed (after an E-STOP, for example), and drives back along the trail, newest point first — or along the run's **safety way back** if it has one (below). |
| at the Guardian Home (or the way back's last point) | **Holds position there** (LOITER) and waits. |

If the trail is empty, the boat goes straight to HOME instead (RTL; HOME is kept on the Guardian
Home, so it is the same point).

**When the link comes back**, at the first heartbeat, at any point of the above:

- before 15 s: the laptop simply drives again;
- after the takeover: the script hands back by itself (thrusters back to the laptop, mode
  MANUAL). The run continues where it stopped. **Nothing to press.**

A second loss later drives back from where the first one stopped.

### Guardian Home and Set Home

The **Guardian Home** is where a drive back along the trail ends and the boat holds (LOITER):

- by default, **where the guardian came ON** (the session start);
- after **Set Home** (GUARDIAN box, guardian ON and connected; it asks for confirmation), **the
  boat's position at that moment**: the trail recorded so far is dropped and starts again from
  there. A link loss then brings the boat back along its path **to exactly this point**, then
  LOITER. Use it when the run has no safety way back (a loaded way back still wins during its
  run; the Guardian Home is used again after STOP RUN).

MCS draws it on the map as a green point **Guardian Home** (layer *Guardian Home*, ON by default)
and shows it in the box's **HOME** row (*guardian ON · lat, lon* or *Set Home · lat, lon*).

- **Only Set Home moves it** (since 2026-11-26; START RUN / STOP RUN no longer move HOME). The
  script keeps ArduPilot's own HOME on it (the RTL fallback goes to the same point).
- **"Exactly"**: the last point counts as reached within `WP_RADIUS` + 0.5 m (at most
  `LGRD_RADIUS`), so the boat drives up to it; LOITER then holds it within `LOIT_RADIUS`. Add the
  GPS error (≈ 1–2 m). Lower `WP_RADIUS` for a tighter stop.
- **How:** MCS sends `set_home`; `guardian.py` sets `LGRD_HOME = 1`; the script answers
  *home … set* with the coordinates and `LGRD_HOME = 0` (or *set home refused: …* and −1:
  guardian not ON, no GPS position).
- Lost with the trail when the autopilot restarts: the Guardian Home is then where the guardian
  comes ON again.

### Safety way back (GPS-anchored patterns)

A GPS-anchored pattern can carry a hand-drawn **safety way back**: in the Pattern Designer,
**✚ Safety way back** (key **B**), click its points in order; the **last point is where the boat
will hold**. It is saved with the pattern.

- **When it is used:** from **START RUN to STOP RUN** of a run on that pattern (the path, and the
  position keeping after its end). Outside a run, the trail as above.
- **What the boat does on a takeover:** it goes to the **point of the way back closest to it**
  (straight there), follows the way back **in the drawn order** to its last point, and LOITERs
  there. A hand-back works as above; a second loss re-joins at the new closest point.
- **On the MCS map** it is drawn like in the designer (dashed orange line, its points, *LOITER*
  at its end) whenever its path is the mission shown: the next run's, the running one's, or a
  Gazebo launch's. Layer *Safety way back (guardian)*, ON by default.
- **How it gets to the boat:** at START RUN, MCS sends it to `guardian.py`, which uploads it as the
  autopilot's **mission** (we never use AUTO, so that storage is free), reads it back to check it,
  then sets `LGRD_SAFE = 1`. The script checks it and answers `LGRD_SAFE = 2` (*way back N pts
  ready*). At STOP RUN, `LGRD_SAFE = 0`.
- **If it cannot be loaded** (old script, upload refused, …) **the run starts anyway**: the GUARDIAN
  box's **Way back** row turns red and the state says *safety way back NOT loaded*, and a link
  loss uses the trail.

### What "neutral", HOLD and LOITER mean

- **Neutral (from 3 s)** = the script sends **1500 µs (zero thrust)** to both thrusters in place
  of the laptop's last command.
  - It is **not an emergency stop**: the autopilot stays armed, nothing latches, nothing has to be
    released. The laptop's next command simply takes over again.
  - It is **not position holding**: nothing steers, so the boat drifts with wind and current.
- **HOLD** (an ArduPilot mode, used for a moment while arming and handing back): the autopilot
  stops the thrusters. No position keeping either.
- **LOITER** (at the end of the drive back): **active position holding**. The autopilot drives the
  thrusters to keep the boat within `LOIT_RADIUS` of that point.

The guardian's neutral is also different from MCS's **E-STOP**: E-STOP stops the thrusters,
latches until you release it, and does **not** switch the guardian off. After an E-STOP and a
link loss, the boat still arms itself and drives back.

## 3. Setup (once)

On the shore, props off or boat out of the water.

1. Start a real-robot session in MCS. The GUARDIAN box says *NOT INSTALLED* (expected).
2. Press **Apply settings**. It turns on Lua scripting (`SCR_ENABLE = 1`) and sets ArduPilot's own
   failsafe as a backstop that fires later than the guardian (`FS_GCS_ENABLE = 1`,
   `FS_ACTION = 1` RTL, `FS_GCS_TIMEOUT = 20`, `FS_THR_ENABLE = 0`). Keep `ARMING_CHECK`
   non-zero.
3. Turn Off Connection, then restart the autopilot: BlueOS (`http://192.168.2.2`) →
   *Autopilot Firmware* → *Restart Autopilot*.
4. Upload the script: BlueOS → *File Browser* → put `autopilot/link_guardian.lua` in the
   `scripts` folder: `configs/ardupilot-manager/firmware/scripts/` (older BlueOS) or
   `ardupilot_logs/firmware/scripts/` (newer - to try first).
5. Restart the autopilot again.
6. Start a session, press **Apply settings** once more. The box must show
   **ON — retraces its path after 15 s without this laptop** and Setup **READY**.

**To update the script:** upload the new file over the old one, restart the autopilot, press
**Apply settings**, then re-test (§7).

## 4. Every session

Nothing to do. Before the boat leaves, read the GUARDIAN box:

| Box says | Do |
|---|---|
| **ON — retraces its path after 15 s…** | Nothing, all good. The boat comes back to the **Guardian Home** on the map; press **Set Home** to move it to where the boat is now. |
| **ON — follows the safety way back after 15 s…** | Nothing: a run with a safety way back is in progress (row **Way back**: *N pts until STOP RUN*). |
| **ON — safety way back NOT loaded…** | The run goes on, but a link loss would use the trail. The **Way back** row says why. |
| **ON — autopilot disarmed: arms itself on link loss** | Press **Arm again** (no run active) so a pre-arm problem shows now. *PreArm:* messages say why. |
| **OFF — the boat will NOT return** | Press **Turn ON**. |
| **NOT INSTALLED / NOT READY** | See §3 and the Setup row's tooltip. |
| **LINK LOST / TAKEN OVER** | Wait: it hands back by itself. If *TAKEN OVER* stays once the link is back, press **Take back control**. |

**Ending the session.** *Turn Off Connection* asks: **Guardian OFF + disarm** (usual: the boat
stays where it is), **Keep ON** (the boat comes back by itself after 15 s), or **Cancel**.

**Switching it off:** **Turn OFF** in the box, or `LGRD_ENABLE = 0` from QGroundControl.

## 5. Settings (`LGRD_*`, in QGroundControl)

| Parameter | Default | Meaning |
|---|---|---|
| `LGRD_NEUTRAL` | 3 s | Silence before neutral thrust (0 = off; keep below `LGRD_TIMEOUT`). |
| `LGRD_TIMEOUT` | 15 s | Silence before the takeover. |
| `LGRD_TRAIL_D` | 2 m | Distance between trail points. |
| `LGRD_RADIUS` | 3 m | A trail point counts as reached (keep above `LGRD_TRAIL_D`). |
| `LGRD_PT_MAX` | 60 s | A point not reached in this time is skipped (longer for a long leg: 2 × its length / `WP_SPEED`). |
| `LGRD_SAFE` | 0 | Safety way back: 0 none, 1 asked by the laptop, 2 loaded and checked, −1 invalid. Reset at every boot. Set by `guardian.py`, not by hand. |
| `LGRD_SAFE_N` | 0 | Number of points of the uploaded way back. |
| `LGRD_HOME` | 0 | Set Home: 1 = set it here, 3 = report it (both from `guardian.py`); the script answers 0 (done) or −1 (refused). Reset at every boot. Not by hand. |
| `LGRD_ENABLE` | 1 | Master switch; 0 = off at once. |
| `LGRD_ON` | 0 | Set by MCS each session; reset at every autopilot boot. |
| `LGRD_SYSID` / `LGRD_COMPID` | 1 / 191 | Identity of the laptop's MAVROS heartbeat. |

Drive-back speed is `WP_SPEED`, RTL speed `RTL_SPEED`: keep both slow in enclosed water.

## 6. Limits

- **The first 3 s keep the last thrust.** With the guardian OFF, nothing ever stops the boat.
- **It goes back to the Guardian Home** (where the guardian came ON, or the last Set Home), not
  to the run start, and only over water the boat already crossed since then.
- **It needs a GPS fix and passing pre-arm checks** to arm. Otherwise it waits in HOLD (thrusters
  stopped, drifting) and keeps retrying.
- **The trail is lost if the autopilot restarts.** The safety way back is not: `guardian.py`
  loads it again by itself after the restart (if the laptop is connected).
- **Safety way back:** the boat goes **straight** to the closest point of the way back, so draw it
  where a straight approach from the survey area is safe. At most 200 points. It needs
  `guardian.py` running when the run starts (it always does in an MCS session).
- **Thrust range:** ArduPilot sets the thrusters' zero point only while disarmed. Armed too
  early, "zero thrust" comes out as full reverse (about 1100 µs). So arming always waits 3.5 s
  disarmed first. Keep `ARMING_CHECK` non-zero as a second guard.
- **Firmware:** Rover 4.5 or newer.

## 7. Re-test after any change

Props removed, QGroundControl's *MAVLink Inspector → `SERVO_OUTPUT_RAW`* open.

1. Start a short run, cut the Base Station power for 25 s. Expect *thrusters neutral* at 3 s
   (`servo1_raw` / `servo3_raw` = 1500), *taking over* at 15 s, then *retracing the path* and
   *holding*. **While holding, both must read 1500 ± 100 µs**; about 1100 is a failure.
2. Restore power: *laptop back - mission resumed*, run continuing, box back to ON.
3. Repeat after an E-STOP: *disarmed - arming it*, *armed*, then the drive back.
4. Cut for 8 s only: *thrusters neutral*, then *thrusters released*, no takeover.
5. **Safety way back:** draw a short one on a GPS-anchored pattern, start a run; the **Way back**
   row must say *safety way back (N pts)*. Cut the power: at 15 s *safety way back from pt k/N*;
   the boat goes to the closest point, follows the way back and holds at its end (*end of way back
   - holding*). Restore power: hand-back as in step 2. After STOP RUN the row says *its own trail*.
6. **Set Home:** with no safety way back, drive a little, press **Set Home**: the HOME row says
   *Set Home · …* and the green *Guardian Home* point moves to the boat. Drive 20 m away, cut the
   power: the boat retraces to that point (*back at path start - holding*) and LOITERs on it.

**Offline, before going to the boat** (no hardware needed):

```bash
python3 -m venv /tmp/luavenv && /tmp/luavenv/bin/pip install lupa      # once
/tmp/luavenv/bin/python link_guardian/test/lua_harness.py              # ALL SCENARIOS PASSED
source ~/ros2_ws/install/setup.bash && python3 link_guardian/test/test_guardian_safety.py
```

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| *NOT INSTALLED* | `SCR_ENABLE` not 1, wrong folder (try the other one in §3), or no restart. |
| Setup: *Laptop identity* fails | Copy the values from the tooltip into `LGRD_SYSID` / `LGRD_COMPID`. |
| *thrusters neutral* while the link is fine | Heartbeats arrive late: raise `LGRD_NEUTRAL`. |
| Takeover while the laptop is fine | WiFi drops over 15 s: move the Base Station. |
| Idle near 1100 µs after a takeover | Thrust range not set (§6). Report it with the dataflash log (`LGRD` records). |
| Box stays *TAKEN OVER* | Press **Take back control**; check Setup for *Script version*. |
| Boat stops at every trail point | `LGRD_RADIUS` too small against `LGRD_TRAIL_D`. |
| Way back: *script too old (no LGRD_SAFE)* | Upload the current `link_guardian.lua` (§3, *To update the script*). |
| Way back: *mission read back differs* / *upload refused* | Start the run again; if it repeats, check the WiFi link. The trail is used meanwhile. |
| *Safety way back* tool greyed in the designer | The pattern is not GPS-anchored: *Set GPS Origin…* first. |
| **Set Home** greyed: *no Set Home* | Upload the current `link_guardian.lua` (no `LGRD_HOME` on the autopilot). |
| *set home refused: no position* | No GPS fix yet on the autopilot. |
