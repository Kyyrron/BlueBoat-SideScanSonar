# Link Guardian — bring the boat back if the laptop link is lost

All our software runs on the operator laptop and reaches the boat over the Base Station WiFi.
If that link drops, or the laptop dies, nothing can steer the boat any more.

The **Link Guardian** is a Lua script that runs **on the boat's autopilot** (ArduPilot Rover).
When it stops hearing the laptop, it drives the boat back **along the path it just took**.
When the laptop is heard again, it hands the boat back to the station and the run goes on.

- **ON by default in every real-robot session.** You operate it from the **GUARDIAN** box of
  the Mission Control Station (MCS).
- The on-boat script is installed **once** (see *One-time setup*).

> ⚠ **Not yet tested on the real boat.** It has been tested only against a mocked autopilot
> and fake MAVROS. Follow *Testing it safely* before relying on it in the water.

## What it does

| Laptop silent for | The boat |
|---|---|
| 0–3 s | Keeps its last thrust command (no RC receiver: ArduPilot keeps the last RC override). |
| **3 s** (`LGRD_NEUTRAL`) | Thrusters held at **neutral** (RC channels 1 and 3 at 1500). If the link returns now, the station drives again at once. |
| **15 s** (`LGRD_TIMEOUT`) | **Takeover:** thrusters handed to the autopilot (`SERVO1/3_FUNCTION` 51/53 → 74/73); the autopilot **arms itself** if needed; the boat **retraces its trail** backwards in GUIDED, then holds (LOITER) at the trail start. |

**Link back:** at the **first** laptop heartbeat the script hands back by itself: HOLD,
thrusters back to the station's mapping, MANUAL. A path run continues where it stopped, a
manual target is pursued again, arrow control is at zero. No operator action is needed. This
also works mid-arming, mid-retrace or while holding at the trail start.

Details:

- **Guardian ON** = the flag `LGRD_ON = 1` on the autopilot. MCS sets it when a session
  connects (`guardian.py watch`). The script resets it to 0 at every autopilot boot.
- **Trail:** while ON, a point every 2 m (`LGRD_TRAIL_D`), armed or not. Kept in memory: lost
  at an autopilot restart, restarted when the guardian goes OFF → ON. Up to 1000 points;
  when full, every other point is dropped and the spacing doubles.
- **Retrace:** a point counts as reached within 3 m (`LGRD_RADIUS`); a point not reached in
  60 s (`LGRD_PT_MAX`) is skipped. After a hand-back the trail is cut at the point reached, so
  a second loss retraces from there.
- **Fallback:** no trail, or GUIDED refused → **RTL**, a straight line to HOME. HOME is the
  session start, moved to each run's start while a run is active.
- **E-STOP does not switch the guardian off.** After an E-STOP and a link loss, the boat arms
  itself and retraces. Only **Turn OFF** in the GUARDIAN box (or `LGRD_ENABLE = 0`) does.
- **Arming:** at connection, `robot_interface` (BlueBoat-Control) arms the autopilot. Our stack
  does not need it armed (thrusters on RC passthrough work disarmed); ArduPilot needs it armed
  to drive the boat itself.

```
        LAPTOP (MCS session)                       BOAT (ArduPilot autopilot)
 ┌───────────────────────────────┐  WiFi  ┌──────────────────────────────────────┐
 │ MAVROS ── heartbeat 1/s ──────┼───────►│ link_guardian.lua (checks 5×/s)      │
 │ robot_interface: arms the     │        │  records the trail (every 2 m)       │
 │   autopilot at connection     │        │  silent > 3 s: thrusters neutral     │
 │ guardian.py watch (by MCS):   │        │  silent > 15 s: take over, arm,      │
 │   LGRD_ON = 1, HOME, status   │        │    retrace the trail, hold           │
 └───────────────────────────────┘        │  laptop heard: hand back             │
                                          └──────────────────────────────────────┘
```

## Layout

| File | Runs on | What it is |
|---|---|---|
| `autopilot/link_guardian.lua` | autopilot | The guardian. Copied once onto the boat. |
| `laptop/guardian.py` | laptop | Its companion. MCS starts `guardian.py watch` with every real-robot session. |

Related code elsewhere: `robot_interface.py` in BlueBoat-Control (arming at connection, the
`rearm` command); the GUARDIAN box in BlueBoat-MCS (`mcs/gui/guardian_box.py`,
`mcs/core/guardian.py`).

## One-time setup

Do it on the shore, props off or boat out of the water.

1. **Start a real-robot session from MCS.** The GUARDIAN box says *NOT INSTALLED* (expected).
2. **Press Apply settings** in the GUARDIAN box. It sets:

   | Parameter | Value | Why |
   |---|---|---|
   | `SCR_ENABLE` | 1 | Turns on Lua scripting |
   | `FS_GCS_ENABLE` | 1 | ArduPilot's own GCS failsafe, as a limited backstop |
   | `FS_ACTION` | 1 | Backstop action = RTL |
   | `FS_GCS_TIMEOUT` | 20 | Backstop fires after the guardian (15 s) |
   | `FS_THR_ENABLE` | 0 | No RC receiver on the boat. Set 1 only with a hand transmitter. |
   | `LGRD_TIMEOUT` | 15 | Takeover delay (only once the script runs) |

   It never changes `ARMING_CHECK`. Keep `ARMING_CHECK` non-zero (*Check* warns if it is 0).
3. **Turn Off Connection, then restart the autopilot.** BlueOS (`http://192.168.2.2`) →
   *Autopilot Firmware* → *Restart Autopilot*. This creates the `scripts` folder.
4. **Upload the script.** BlueOS → *File Browser*. Put `autopilot/link_guardian.lua` in the
   `scripts` folder: `configs/ardupilot-manager/firmware/scripts/` (older BlueOS) or
   `ardupilot_logs/firmware/scripts/` (newer). If step 6 still says *NOT INSTALLED*, try the
   other folder. The right folder has not been checked on our boat.
5. **Restart the autopilot again.**
6. **Start a session and press Apply settings once more** (now `LGRD_TIMEOUT` exists). The box
   should show **ON — retraces its path after 15 s without this laptop**, Setup **READY**, and
   *LinkGuard: …* messages from the boat.

**Updating the script:** upload the new file over the old one, restart the autopilot, start a
session, press **Apply settings**.

## Every session

Nothing to do: the guardian turns ON when the session connects. Before the boat leaves, look at
the GUARDIAN box:

| Box says | Meaning / what to do |
|---|---|
| **ON — retraces its path after 15 s without this laptop** | All good. |
| **ON — autopilot disarmed: arms itself on link loss** | Arming failed at connection, or an E-STOP disarmed it. Press **Arm again** (no run active) so a pre-arm problem shows now. *PreArm:* messages say why. |
| **NOT READY / NOT INSTALLED** | See *One-time setup* and the Setup row's tooltip. |
| **OFF — the boat will NOT return** | Someone pressed **Turn OFF**. Press **Turn ON**. |
| **LINK LOST — the boat retraces its path on its own** | Nothing to do: the station drives again when the link is back. |
| **TAKEN OVER — boat in GUIDED; handing back…** | Shown briefly after the link returns. If it stays, press **Take back control**. |

The **HOME** row shows where the RTL fallback would go.

**Ending a session.** *Turn Off Connection* (or closing MCS) with the guardian ON asks:

- **Guardian OFF + disarm, then turn off** — the usual choice. The boat stays where it is. If
  the guardian cannot be confirmed OFF, nothing is turned off.
- **Keep ON — the boat comes back** — after 15 s the boat retraces its trail and holds.
- **Cancel.**

**Ways to stop the guardian:** **Turn OFF** in the GUARDIAN box, or `LGRD_ENABLE = 0` from
QGroundControl connected directly to the boat (stands down at once). E-STOP stops the
thrusters but does **not** switch the guardian off.

**Take back control** (fallback, `guardian.py reclaim`): does the hand-back from the laptop
when the box still says *TAKEN OVER* a few seconds after the link is back.

## `guardian.py` from a terminal

MCS's buttons call these; they also work by hand, with a BlueBoat launch (MAVROS) running:

```bash
source ~/ros2_ws/install/setup.bash
python3 link_guardian/laptop/guardian.py check [--json]   # read-only: installed, configured, ready?
python3 link_guardian/laptop/guardian.py setup            # write the recommended parameters
python3 link_guardian/laptop/guardian.py on | off         # set LGRD_ON
python3 link_guardian/laptop/guardian.py reclaim [--force]  # take control back (--force: even with a run active)
python3 link_guardian/laptop/guardian.py watch            # session companion (MCS starts it)
```

`watch` publishes on `/link_guardian/status` and listens on `/link_guardian/command`.

## Settings (`LGRD_*`, editable in QGroundControl)

| Parameter | Default | Meaning |
|---|---|---|
| `LGRD_ENABLE` | 1 | Master switch. 0 = off immediately, whatever MCS says. |
| `LGRD_ON` | 0 | Session flag, set by MCS; reset to 0 at every boot. |
| `LGRD_TIMEOUT` | 15 | Seconds of silence before takeover. |
| `LGRD_NEUTRAL` | 3 | Seconds of silence before neutral thrust. 0 = off. Keep below `LGRD_TIMEOUT`. |
| `LGRD_TRAIL_D` | 2 | Metres between trail points. |
| `LGRD_RADIUS` | 3 | Metres: a trail point counts as reached. Keep above `LGRD_TRAIL_D`. |
| `LGRD_PT_MAX` | 60 | Seconds to reach one trail point before skipping it. |
| `LGRD_SYSID` / `LGRD_COMPID` | 1 / 191 | MAVLink identity of the laptop's MAVROS. `LGRD_COMPID` 0 = any. |
| `LGRD_SRV1_FN` / `LGRD_SRV3_FN` | 74 / 73 | Thruster functions given to the autopilot on takeover. |
| `LGRD_DETECT` | 1 | 1 = watch the MAVROS heartbeat itself (recommended). 0 = ArduPilot's GCS timer, which on-boat services can fool. |

`LGRD_STAGE1`, `LGRD_WAIT`, `LGRD_S1_MAX` belong to an old script version and do nothing.

Also check `WP_SPEED` (retrace speed) and `RTL_SPEED` (RTL fallback): keep them slow in
enclosed water. Rally points also count as RTL destinations.

## Testing it safely

Move to the next step only when the current one behaves exactly as described. **Restart the
autopilot before every trial**, and keep QGroundControl's *MAVLink Inspector →
`SERVO_OUTPUT_RAW`* open (`servo1_raw` / `servo3_raw` are what the ESCs receive).

**1. Desk (boat on the bench, props removed).** Start a session: ON, Setup READY, HOME set.
No *thrusters neutral* message while the link is fine (if there is one, the heartbeat is late:
raise `LGRD_NEUTRAL` and `LGRD_TIMEOUT`). E-STOP → box says *arms itself on link loss*. Release
E-STOP, **Arm again** → armed.

**2. Bench link loss (props removed).**
1. Start a short run.
2. Cut the Base Station power (or the laptop's WiFi) for 25 s.
3. Expect: from 3 s `servo1_raw` / `servo3_raw` = 1500 and *thrusters neutral*; from 15 s
   *link lost 15 s - taking over*, then *retracing the path (N pts)* (on a bench:
   *back at path start - holding*, LOITER).
4. **While holding, `servo1_raw` and `servo3_raw` must read 1500 ± 100 µs.** About 1100 is a
   **FAIL** (idle at full reverse, see *Limits*): stop and report it.
5. Restore power. Within a second or two: *laptop back - mission resumed*, MANUAL,
   `SERVO1/3_FUNCTION` 51/53, the run going on, box back to ON.
6. Repeat with **E-STOP first**: *disarmed - arming it*, then *armed* about 4 s later, then the
   retrace. Same 1500 ± 100 µs check.
7. **Hiccup:** cut for about 8 s. Expect *thrusters neutral*, then
   *laptop back - thrusters released*, no takeover.
8. **Turn Off Connection → Keep ON:** takeover after 15 s.
9. **Turn Off Connection → Guardian OFF + disarm:** nothing happens.

**3. Detection.** Step 2 proves the guardian fires when the laptop disappears. On-boat BlueOS
services that also use system id 1 must not count as the laptop.

**4. Shallow water, calm day, short distance.** Have a hand RC transmitter or a second person
on QGroundControl ready. Drive 20–30 m along an L or a curve, cut the Base Station power. After
15 s the boat must drive back along the same curve. Restore power halfway: it must turn round
and continue the run.

**Optional, without hardware:** ArduPilot SITL (`sim_vehicle.py -v Rover`, script in its
`scripts/` folder), launch with `fcu_url:=udp://:14551@127.0.0.1:14550`. Our Gazebo simulator
does not run ArduPilot, so it cannot test the guardian.

## Limits (read before using it)

- **Until 3 s of silence the boat keeps its last thrust.** With the guardian **OFF**, nothing
  stops it: the boat keeps going.
- **The return crosses only water the boat already crossed** (within `LGRD_RADIUS`). Only the
  RTL fallback is a straight line.
- **It returns to the trail start** (where the guardian was turned ON, usually the session
  start), not to the run start.
- **A flapping link** switches between retracing and station control; each new loss waits the
  full 15 s again.
- **It needs a GPS fix and passing pre-arm checks** to arm and drive. Without them the boat
  holds with thrusters off and keeps retrying; *PreArm:* messages say why.
- **ArduPilot's own GCS failsafe is only a backstop.** It also hears on-boat services using
  system id 1, fires after 20 + 1.5 s and never in HOLD, and its RTL cannot drive thrusters
  still on passthrough. `FS_GCS_TIMEOUT` must stay above `LGRD_TIMEOUT`.
- **Thruster output range.** On functions 73/74 ArduPilot sets each thruster's ±1000 range only
  while disarmed, once a second. Armed too early, zero thrust comes out near 1100 µs (full
  reverse). So `robot_interface` and the script wait 3.5 s disarmed before arming, and the
  script re-arms first if it never saw the range applied. Keep `ARMING_CHECK` non-zero.
- **Connection window.** At connection and on *Arm again*, the boat sits about 4 s disarmed,
  then about 1 s armed in MANUAL at neutral, before override.
- **The servo change is not saved:** an autopilot restart restores the stored values.
- **Firmware:** Rover 4.5 or newer recommended (Lua with MAVLink receive). On older firmware the
  script says *no MAVLink rx, GCS timer* and uses ArduPilot's GCS timer instead.
- This script is the one piece of project code on the boat. It is autopilot configuration, not
  a ROS node.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| *NOT INSTALLED* | Script not running: `SCR_ENABLE` not 1, wrong folder, or no restart. Look for *LinkGuard: loaded* or a Lua error in the boat messages. |
| Pre-arm error about scripting or memory | Lua error, or too little script memory: raise `SCR_HEAP_SIZE` a little and restart. |
| Setup: *Laptop identity* fails | MAVROS's identity differs from `LGRD_SYSID` / `LGRD_COMPID`. The tooltip shows the real values; copy them in. |
| *autopilot disarmed* after connecting | Arming failed (no GPS fix, EKF not ready). Read *PreArm:*, then **Arm again**. |
| Guardian never fires in test step 2 | Identity mismatch, or `LGRD_DETECT = 0` with on-boat services on system id 1. |
| Guardian fires while the laptop is fine | WiFi drops longer than 15 s. Check the Base Station placement. |
| *thrusters neutral* while the laptop is fine | Heartbeats arrive late. Raise `LGRD_NEUTRAL` (below `LGRD_TIMEOUT`). |
| Idle at ~1100 µs after a takeover | Output range not applied (see *Limits*). Report it with the dataflash log (`LGRD` records). |
| RTL but the boat does not move | Thrusters still on passthrough (*could not set SERVO…*), or *no HOME set*. |
| Box stays *TAKEN OVER* | Old script on the boat (Check: *Script version*), or the hand-back failed (*could not restore SERVO1/3*, *MANUAL refused*). Press **Take back control**. |
| *Take back control* greyed | Normal: the script already handed back. |
| Boat stops at every trail point | `LGRD_RADIUS` too small against `LGRD_TRAIL_D`, or `WP_RADIUS` large. |
| *guardian.py not found* | MCS cannot find this folder: incomplete checkout, or set `guardian.script` in `~/.config/blueboat_mcs/config.json`. |
