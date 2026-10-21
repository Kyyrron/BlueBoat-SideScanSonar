# Link Guardian — bring the boat home if the laptop connection is lost

All of our software runs on the operator laptop and talks to the boat through the BlueBoat
Base Station WiFi. If that link drops, or the laptop is switched off without warning,
nothing on the laptop can steer the boat any more. The **Link Guardian** is a small script
that runs **on the boat's autopilot**. When it stops hearing from the laptop, it drives the
boat back to HOME by itself.

It is **ON by default in every real-robot session** and is operated from the
**GUARDIAN box** of the Mission Control Station (MCS). You only install the on-boat part
once (§3); everything after that happens in MCS.

> ⚠ **Status: new, not yet tested on the real boat.** It has been tested against simulated
> stand-ins only (§7). Follow the test ladder in §7 before relying on it in the water.
> Reviewed against ArduPilot Rover 4.5.7 / 4.6 / master source on 2026-10-20 (thruster output
> range, RC override behaviour, failsafe timing — §9); fixes applied the same day.

---

## 1. How it works

```
        LAPTOP (MCS session)                       BOAT (ArduPilot autopilot)
 ┌───────────────────────────────┐  WiFi  ┌──────────────────────────────────────┐
 │ MAVROS ── heartbeat 1/s ──────┼───────►│ link_guardian.lua (checks 5×/s)      │
 │ robot_interface: arms the     │        │  "When did I last hear the laptop?"  │
 │   autopilot at connection     │        │                                      │
 │ guardian.py watch (started by │        │  guardian ON and silent > 3 s:       │
 │   MCS): guardian ON, HOME =   │        │   thrusters held at neutral          │
 │   run start, GUARDIAN box     │        │  silent > 5 s:                       │
 └───────────────────────────────┘        │   1. thrusters back to the autopilot │
                                          │   2. arm (if not armed)              │
                                          │   3. RTL: drive HOME and hold        │
                                          └──────────────────────────────────────┘
```

**Two different "arm" things, so no confusion:**
* **Motors enabled** (MCS launch option, E-STOP / Release E-STOP) is *our* switch on the
  laptop: it decides whether `robot_interface` sends thrust or neutral. It disappears with
  the laptop.
* **Armed** is the *autopilot's* own state (what QGroundControl shows). Our stack doesn't
  need it: during a session the thrusters are on *RC passthrough*, which works disarmed.
  ArduPilot needs it to drive the boat **itself**, which is what the return home does.

**What happens in a session:**
1. **Connection.** `robot_interface` puts the autopilot in MANUAL and switches to the normal
   thruster mapping (ArduPilot refuses to arm while the thrusters are on passthrough). It
   waits about 3.5 s **disarmed** on that mapping, so ArduPilot sets the thrusters' output
   range (§9), then **arms** the autopilot and switches to override as before. ArduPilot
   sets **HOME** where it was armed: the **session start**. If arming fails (no GPS fix yet…), the session
   continues anyway and the GUARDIAN box says so; you can press **Arm again** later.
2. **Guardian ON.** MCS starts `guardian.py watch`, which checks the script is installed and
   sets the guardian flag `LGRD_ON = 1` on the autopilot. The script clears that flag at every
   autopilot boot, so it never stays ON after a session.
3. **Runs.** At each START RUN, HOME moves to the **run start**. At STOP RUN it moves back to
   the session start.
4. **The link is lost** (WiFi down, laptop off, MCS crashed) while the guardian is ON.
   - **For the first 3 s the boat keeps its last thrust command.** The boat has no RC
     receiver, and ArduPilot keeps the last RC override value when the laptop stops sending.
   - **After 3 s** (`LGRD_NEUTRAL`) the script holds the thrusters at neutral (RC channels
     1/3 at 1500). If the link comes back before 5 s, the station's commands take over again
     at once: a WiFi hiccup costs at most a short stop.
   - **After 5 s** (`LGRD_TIMEOUT`) the script takes over and does three things on its own:
     - hands the thrusters back to the autopilot (`SERVO1/3_FUNCTION` 51/53 → 74/73);
     - **arms it if it is not armed**: after an E-STOP, or when arming failed at connection.
       The first attempt comes 3.5 s after the switch (output range, §9). It keeps retrying
       while holding position, because pre-arm checks such as the GPS fix must pass;
     - switches to **RTL**. The boat drives in a straight line to HOME and holds there.
5. **The link comes back.** The boat keeps returning (or holding) until you press **Take back
   control**. It never resumes a mission by itself.

**The guardian stays ON through an E-STOP.** The E-STOP stops the thrusters (and disarms),
but if the link is then lost, the boat still comes home. Only the GUARDIAN box's **Turn
OFF**, or the Turn Off Connection choice (§5), switches it off.

## 2. What is in this folder

| File | Where it runs | What it is |
|---|---|---|
| `autopilot/link_guardian.lua` | on the autopilot | The guardian. Copied once onto the boat (§3). |
| `laptop/guardian.py` | on the laptop | Its companion. MCS starts `guardian.py watch` with every real-robot session; the other subcommands (`check`, `setup`, `on`, `off`, `reclaim`) are what the GUARDIAN box buttons do, and also work from a terminal. |
| `README.md` | — | This file. |

Elsewhere in the project:
* `BlueBoat-Control` `robot_interface.py`: arm-before-override at connection, and the
  `rearm` command.
* `BlueBoat-MCS`: the GUARDIAN box (`mcs/gui/guardian_box.py`, `mcs/core/guardian.py`), the
  companion start (`launch_manager.guardian_command`), and the Turn Off Connection choice.

**What is a Lua script on ArduPilot?** ArduPilot contains a small Lua interpreter. You put a
`.lua` text file in the autopilot's `scripts/` folder, turn on `SCR_ENABLE`, and restart the
autopilot. ArduPilot then runs the script itself, five times per second here, with no laptop
involved. Scripts run in a sandbox, so a script error cannot crash the autopilot. A script
that fails to load **blocks arming** with a pre-arm error, so a broken guardian shows up on
the shore.

## 3. One-time setup (on the shore, props off or boat out of the water)

1. **Start a session from MCS** as usual (real robot). The GUARDIAN box will say
   *NOT INSTALLED* — expected for now.
2. **Apply the ArduPilot settings.** In the GUARDIAN box press **Apply settings**. It sets:

   | Parameter | Value | Why |
   |---|---|---|
   | `SCR_ENABLE` | 1 | turns on Lua scripting |
   | `FS_GCS_ENABLE` | 1 | ArduPilot's own GCS failsafe, a limited backstop (§9) |
   | `FS_ACTION` | 1 | the backstop's action is RTL |
   | `FS_GCS_TIMEOUT` | 10 | the backstop fires after the guardian |
   | `FS_THR_ENABLE` | 0 | no RC receiver on the boat; while armed, the radio failsafe would otherwise fire. Keep it at 1 only if you use a hand transmitter. |

   **Apply settings** never touches `ARMING_CHECK`, but **Check** warns if it is 0. Keep it
   enabled (§9).

3. **Turn Off Connection**, then **restart the autopilot**. In BlueOS
   (`http://192.168.2.2`): *Autopilot Firmware* → *Restart Autopilot*. ArduPilot creates its
   `scripts` folder at this restart, because scripting is now on.
4. **Upload the script.** In BlueOS open the **File Browser**. Find the `scripts` folder that
   appeared after step 3. It depends on the BlueOS version:
   `configs/ardupilot-manager/firmware/scripts/` (older) or
   `ardupilot_logs/firmware/scripts/` (newer). Upload `autopilot/link_guardian.lua` there.
   If neither folder exists, create `scripts` in the first one. If step 6 then still says
   *NOT INSTALLED*, try the other folder. The location has not been checked on our boat.
5. **Restart the autopilot again.**
6. **Start a session from MCS.** The GUARDIAN box should now show **ON — returns HOME after
   5 s without this laptop**, Setup **READY**, and *LinkGuard: …* messages from the boat.

**Updating the script later:** upload the new file over the old one, then restart the
autopilot.

## 4. Every session

Nothing to do: the guardian switches ON by itself when the session connects. Before the boat
leaves, glance at the GUARDIAN box:

| Box says | Meaning / what to do |
|---|---|
| **ON — returns HOME after 5 s without this laptop** | All good. |
| **ON — autopilot disarmed: arms itself on link loss** | Protected, but arming failed at connection or an E-STOP disarmed it. Press **Arm again** (when no run is active) so a pre-arm problem shows up now, not during a loss. Messages starting with *PreArm:* say why. |
| **NOT READY / NOT INSTALLED** | See §3 and the Setup row's tooltip. |
| **OFF — the boat will NOT return** | Someone pressed **Turn OFF**. Press **Turn ON**. |
| **TAKEN OVER — boat in RTL** | The guardian (or an ArduPilot failsafe) is driving. Stop the run, then **Take back control**. |
| **LINK LOST — the boat returns HOME on its own** | The laptop lost the boat. Nothing to do from here until the link is back. |

The **HOME** row shows where the boat would go: the session start, or the current run's start.

## 5. Ending a session

**Turn Off Connection** (or closing MCS) while the guardian is ON asks you what to do. Once the
laptop goes silent the boat would otherwise come home by itself:
* **Guardian OFF + disarm, then turn off.** The usual choice at the end of a session. The
  guardian is turned off and the autopilot disarmed; the boat stays where it is. If the
  guardian cannot be confirmed OFF, nothing is turned off and MCS tells you.
* **Keep ON — the boat returns home.** Turn off anyway; the guardian brings the boat back to
  HOME.
* **Cancel.**

## 6. Taking control back after the guardian acted

When the link is back:
1. Press **STOP RUN** if a run was active. Otherwise the boat would resume it the moment
   control returns, so the button refuses until you do.
2. Press **Take back control** in the GUARDIAN box. The boat stops (HOLD), the thrusters go
   back to the station's mapping, then MANUAL. The station drives again; the boat stays armed
   and the guardian keeps watching.

Other ways to stop the guardian at any time:
* **E-STOP** stops the thrusters. It does **not** switch the guardian off.
* The neutral hold (3 s of silence) needs nothing from you: it ends by itself when the link
  is back.
* **Turn OFF** in the GUARDIAN box.
* From QGroundControl connected directly to the boat: set `LGRD_ENABLE = 0`. It stands down
  immediately.

## 7. Testing it safely (in order — move on only when a step behaves exactly as described)

**Already done (off the boat):**
* Script logic run in a Lua 5.3 interpreter (ArduPilot's version) against a mocked autopilot.
  The mock reproduces Rover's 1 Hz output-range setup and its pre-arm motor check. Covered:
  - neutral hold: none before 3 s, RC 1/3 at 1500 from 3 s, released when the link is back
    (4 s hiccup), stopped at takeover;
  - the 5 s takeover → RTL, with the ±1000 output range on both thrusters;
  - self-arming after an E-STOP, first attempt ≥ 3.5 s after the switch;
  - armed with the output range never seen applied (ARMING_CHECK=0 case): disarm, re-arm,
    RTL with the correct range. The mock reproduces the 0..100 bug when this check is
    skipped;
  - retrying without GPS, then arming once it is back;
  - stage 1 (GUIDED to the last-link point, RTL after `LGRD_S1_MAX`);
  - the flag reset at boot; Turn OFF (nothing happens, no log spam);
  - other heartbeats (system 1 component 194, system 255) not counting as the laptop;
  - both MAVLink message layouts (291 and 298 bytes);
  - every boat message fits one STATUSTEXT (< 50 characters).
* `robot_interface`'s arm-before-override, its failure path and `rearm`, run against a fake
  autopilot. Since 2026-10-20 the first arm request comes ~3.5 s after `default` is confirmed.
* `guardian.py watch` (auto-ON, check, on/off, setup, reclaim) against a fake MAVROS; `check`'s
  ARMING_CHECK, neutral-hold and old-script warnings against stub parameters.
* The MCS smoke test.

**Before every trial below, restart the autopilot.** The output-range problem (§9) can only
appear after a boot, and an earlier good setup hides it. Keep QGroundControl's **MAVLink
Inspector → `SERVO_OUTPUT_RAW`** open: `servo1_raw` / `servo3_raw` are what the ESCs receive.

**Step 1 — Desk (boat on the bench, props removed).** Start a session. The box shows ON —
ARMED, Setup READY, HOME set. The boat messages must **not** show *thrusters neutral* while the
link is fine. If they do, MAVROS's heartbeat is slower than 1 Hz or the WiFi drops: raise
`LGRD_NEUTRAL` and `LGRD_TIMEOUT`. Press E-STOP: Autopilot shows *disarmed*, the box shows
*arms itself on link loss*. Release E-STOP, then **Arm again**: ARMED again.

**Step 2 — Bench link loss (props removed, boat on a stand).**
1. Start a short run (HOME = run start).
2. **Unplug the Base Station's power** (or turn off the laptop's WiFi).
3. Wait 10 s and plug it back in.
4. Expected:
   * from 3 s: `servo1_raw` / `servo3_raw` = **1500**, message *thrusters neutral*;
   * from 5 s: the box shows *TAKEN OVER — boat in RTL*, with the messages *link lost - taking
     over* and *returning HOME (RTL)*;
   * the ESCs receive commands — keep the props **off**;
   * **with the boat at HOME (run start = where it sits), `servo1_raw` and `servo3_raw` read
     1500 ± 100 µs.** About 1100 is a **FAIL**: idle at full reverse, the output-range problem
     of §9. Stop and report it.
5. STOP RUN, then **Take back control**: MANUAL, station driving.
6. Repeat with **E-STOP first, then unplug**: the boat must arm itself (*disarmed - arming
   it*, then about 4 s later *armed*) and go to RTL. Same 1500 ± 100 µs check.
   Repeat 2 and 6 a few times, each after an autopilot restart.
7. **Hiccup:** unplug for about 4 s only. Expected: *thrusters neutral* at 3 s, then *laptop
   back - thrusters released*, no takeover, and the station drives again.
8. Repeat with **Turn Off Connection → Keep ON**: the boat must take over after 5 s.
9. Repeat with **Turn Off Connection → Guardian OFF + disarm**: nothing may happen.

**Step 3 — Detection check (important).** The script listens for heartbeats from MAVROS
(system 1, component 191; the box's Setup check compares them with MAVROS's real values). Some
BlueOS services on the boat also use system id 1, and they must **not** count as the laptop.
Step 2 proves detection works: the guardian must fire when the laptop disappears.

**Step 4 — Shallow water, short distance, calm day.**
* Have a **hand RC transmitter** or a second person with QGroundControl ready.
* Start a run close to the shore, drive 20–30 m away, then cut the Base Station power.
* Watch the boat return to the run start and hold. Restore power, then Take back control.

**Optional — ArduPilot SITL.** To test without hardware, run ArduPilot's software-in-the-loop
Rover (`sim_vehicle.py -v Rover`, with the script in its `scripts/` folder) and point the launch
at it (`fcu_url:=udp://:14551@127.0.0.1:14550`). Our Gazebo simulator does **not** run
ArduPilot, so it cannot test the guardian.

## 8. Settings (`LGRD_*` parameters, editable in QGroundControl)

| Parameter | Default | Meaning |
|---|---|---|
| `LGRD_ENABLE` | 1 | Master switch. 0 switches the guardian off immediately, whatever MCS says. |
| `LGRD_ON` | 0 | Session flag, set by MCS (`guardian.py watch`); reset to 0 at every boot. |
| `LGRD_TIMEOUT` | 5 | Seconds of laptop silence before taking over. Higher tolerates WiFi hiccups better. |
| `LGRD_NEUTRAL` | 3 | Seconds of laptop silence before the thrusters are held at neutral (until the link is back or the takeover). 0 = off. Must stay below `LGRD_TIMEOUT`. |
| `LGRD_STAGE1` | 0 | 1 = first return to the last point with a link, wait there, then go HOME. |
| `LGRD_WAIT` | 30 | Seconds to wait at that point. |
| `LGRD_S1_MAX` | 180 | Maximum seconds spent on stage 1 before going HOME anyway. |
| `LGRD_RADIUS` | 5 | Metres: "arrived at the last-link point". |
| `LGRD_SYSID` / `LGRD_COMPID` | 1 / 191 | MAVLink identity of the laptop's MAVROS (ROS 2 MAVROS: target system 1, component 191). |
| `LGRD_SRV1_FN` / `LGRD_SRV3_FN` | 74 / 73 | Thruster functions given to the autopilot on takeover (BlueBoat default). |
| `LGRD_DETECT` | 1 | 1 = watch the MAVROS heartbeat itself (recommended). 0 = ArduPilot's GCS timer, which on-boat services can fool. |

Also worth a look:
* `WP_SPEED` / `RTL_SPEED`: return speed. Keep it slow in enclosed water.
* `WP_RADIUS`: how close counts as "at home".
* **Rally points**: RTL goes to the closest of HOME and the rally points.

## 9. Good to know / limits

* **The return is a straight line.** In enclosed water, check that no obstacle sits between
  your work area and the run start; add a rally point on the safe side if one does.
* **It needs a GPS fix and passing pre-arm checks** to arm and drive. Without them the boat
  holds (thrusters off) and keeps retrying; the *PreArm:* messages say why.
* **Until the guardian acts, the boat keeps its last thrust.** With no RC receiver, ArduPilot
  keeps the last RC override value forever once the laptop goes silent: the passthrough
  thrusters keep the station's last command. The guardian holds them at neutral after
  `LGRD_NEUTRAL` (3 s). With the guardian **OFF** nothing does this, so the boat keeps going.
* **ArduPilot's own GCS failsafe (the "backstop") is limited.**
  - It only watches heartbeats from system `MAV_GCS_SYSID`. `param_set` sets that to MAVROS's
    1 in override, so any on-boat service using system id 1 also keeps it quiet.
  - It fires after `FS_GCS_TIMEOUT` + `FS_TIMEOUT` (10 + 1.5 s), and never while in HOLD.
  - Its RTL **cannot drive the thrusters**, which stay on passthrough with the last command.
  - Only the script stops the boat and brings it home.
* **Thruster output range (why arming waits).** On 73/74, ArduPilot Rover must scale each
  thruster output ±1000 (0 = 1500 µs, stopped). It does that once per second, **only while
  disarmed**.
  - Armed before that has happened, a channel gets a 0..100 range: zero thrust then comes out
    near 1100 µs (full reverse) and small forward commands saturate.
  - The good range then stays until the autopilot reboots.
  - With `ARMING_CHECK` enabled, Rover's pre-arm motor check makes the bad case practically
    impossible. Defence in depth all the same:
    - `robot_interface` and the script wait 3.5 s disarmed on 74/73 before arming;
    - the script remembers whether it has seen the range applied since boot. If not, a
      takeover while armed disarms and re-arms first (about 4 s more).
  - Keep `ARMING_CHECK` non-zero (Check warns otherwise).
* **Arming changes ArduPilot's behaviour while the link is up.** ArduPilot's own failsafes
  become live. That is why `FS_THR_ENABLE = 0` is recommended (no RC receiver), and why a
  failsafe mode change during a session shows as *TAKEN OVER* in the box (Take back control
  clears it).
* **Connection window.** At connection, and on Arm again, the boat sits about 4 s on the
  normal thruster mapping **disarmed**, then about a second armed in MANUAL at neutral, before
  override.
* **The servo change is temporary.** It is not saved: restarting the autopilot restores what
  was saved last.
* **ArduPilot version.** Lua scripting with MAVLink receive is needed (Rover 4.5 or newer
  recommended). On older firmware the script reports *no MAVLink rx, GCS timer* and falls back
  to ArduPilot's GCS timer; test step 2 then matters even more.
* **Project rule.** Root `CLAUDE.md` §1.1 says no project code runs on the boat. This script
  is the one exception, ordered by the owner on 2026-10-14. It is autopilot configuration,
  not a ROS node.

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| *NOT INSTALLED* | Script not running: `SCR_ENABLE` not 1, wrong folder, or no autopilot restart. Look for *LinkGuard: loaded* or a Lua error in the boat messages. |
| Pre-arm error mentioning scripting or memory | Lua error, or not enough script memory: raise `SCR_HEAP_SIZE` a little and restart. |
| Setup: *Laptop identity* fails | MAVROS's identity differs from `LGRD_SYSID`/`LGRD_COMPID`. The tooltip shows MAVROS's real values; copy them into the `LGRD_*` parameters. |
| *autopilot disarmed* after connecting | Arming failed (no GPS fix yet, EKF not ready). Read the *PreArm:* messages, then **Arm again**. |
| Guardian never fires in test step 2 | Identity mismatch (above), or `LGRD_DETECT = 0` where on-boat services use system id 1. |
| Guardian fires while the laptop is fine | WiFi drops longer than `LGRD_TIMEOUT`. Raise it (8–10 s) and check the Base Station placement. |
| Idle at ~1100 µs (servo1/3_raw) after a takeover | Thruster output range not applied (§9). Should be impossible with the current script and `ARMING_CHECK` on: report it, with the boat's dataflash log (`LGRD` records). |
| *thrusters neutral* messages while the laptop is fine | Heartbeats arrive late: WiFi drops, or MAVROS's heartbeat is slower than 1 Hz. Raise `LGRD_NEUTRAL` (keep it below `LGRD_TIMEOUT`). |
| Mode RTL but the boat does not move | Thrusters still on passthrough (*could not set SERVO…* message), or no GPS / no HOME (*no HOME set*). |
| *Take back control* greyed | A run is still active (STOP RUN first), or the boat is not under guardian control. The tooltip says which. |
| Box says *guardian.py not found* | MCS can't find this folder: the superproject is incomplete, or set `guardian.script` in `~/.config/blueboat_mcs/config.json`. |
