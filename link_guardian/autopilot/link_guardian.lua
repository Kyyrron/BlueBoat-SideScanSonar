--[[
link_guardian.lua - BlueBoat connection-loss guardian (ArduPilot Rover, runs ON the autopilot)

What it does
  Our whole software stack runs on the operator laptop and reaches the boat over the
  Base Station WiFi. If that link dies (or the laptop is switched off without warning),
  nothing on the laptop can steer the boat any more. This script runs on the autopilot
  itself and brings the boat back to HOME on its own.

    1. Every 200 ms it checks when the laptop's MAVROS heartbeat (MAVLink system
       LGRD_SYSID, component LGRD_COMPID - MAVROS 2 sends 1 / 191) was last received.
    2. The guardian is ON while the session flag LGRD_ON = 1. The laptop
       (`guardian.py watch`, started by the Mission Control Station with every real-robot
       session) sets it when the session connects; the script resets it to 0 at every
       boot, so a flag from an old session never survives a reboot. It becomes active
       once the laptop has been heard with the flag on.
    3. While the guardian is ON it records the boat's TRAIL: a point every LGRD_TRAIL_D
       metres (default 2), armed or disarmed, link up or down, whatever the laptop is
       driving (path, manual target, arrows). It lives in the script's memory: reset at
       every boot and whenever the guardian goes from OFF to ON (one trail per session).
       1000 points at most; when full, every other point is dropped and the spacing
       doubles, so the whole path is kept, coarser.
    4. Laptop silent for LGRD_NEUTRAL seconds (default 3): hold the thrusters at neutral.
       Our stack drives them through RC passthrough (SERVO1/3_FUNCTION = 51/53) with RC
       overrides, and with no RC receiver on the boat ArduPilot keeps the LAST override
       value forever once the laptop stops sending - the boat would keep its last thrust.
       The script overrides those RC channels with 1500 until the link is back (MAVROS's
       20 Hz stream then wins again) or until the takeover below.
    5. Laptop silent for LGRD_TIMEOUT seconds (default 15): take over.
         a. remember SERVO1/3_FUNCTION (the station's passthrough mapping), then hand the
            thrusters to the autopilot: LGRD_SRV1_FN / LGRD_SRV3_FN (74 ThrottleRight /
            73 ThrottleLeft, the BlueBoat default), which ArduPilot's navigation modes
            drive. Not saved: a reboot restores the stored values.
         b. ARM the autopilot if it is not armed (after an E-STOP, or when arming failed
            at connection). This only works after (a): ArduPilot refuses to arm while the
            thrusters are on passthrough. The first attempt waits ARM_SETTLE_MS (below),
            then it keeps retrying (pre-arm checks such as a GPS fix must pass) and holds
            meanwhile.
         c. RETRACE: GUIDED to each trail point in reverse order, newest first. A point
            counts as reached within LGRD_RADIUS m; one not reached within LGRD_PT_MAX s
            is skipped. At the oldest point: LOITER (else HOLD) and wait there.
            No trail, or GUIDED refused: RTL (straight line to HOME) instead.
    6. When the link comes back (first laptop heartbeat) the guardian hands control back
       at once: HOLD, SERVO1/3_FUNCTION back to what they were before the takeover,
       MANUAL. The station's RC override then drives again, so the run (or manual
       target) continues where the laptop left it - no operator action. The trail is cut
       back to the point reached, so a second loss retraces from there. A disarm while
       the laptop is connected (the operator's E-STOP) never triggers anything; a disarm
       nobody could have sent (link down) is undone.

Thruster output range (why the arming waits)
  For 73/74 Rover must scale each output channel -1000..+1000 (0 = 1500 us, stopped). It
  applies that range only in its 1 Hz loop, and only while DISARMED. A channel armed on
  73/74 before that happened gets a 0..100 range instead: zero thrust then comes out near
  1100 us (full reverse) and small forward commands saturate. Once a disarmed 1 Hz pass
  has run on 73/74 the good range sticks until reboot. So:
    - the first arm attempt is made ARM_SETTLE_MS after switching to 73/74 (disarmed);
    - the script remembers whether, since boot, it has seen the autopilot disarmed on
      73/74 for SCALING_SETTLE_MS. If not, a takeover while armed first disarms and goes
      through (b) instead of switching the thrusters under an armed autopilot.
  (With ARMING_CHECK enabled Rover's own pre-arm motor check already prevents the bad
  case in practice; this does not rely on it.)

HOME is set by ArduPilot at arming (the session start) and moved by the laptop to the
start of each run while the link is up. Only the RTL fallback goes there.

Parameters (appear after the first boot with the script; see README.md):
  LGRD_ENABLE   1     master switch; 0 = guardian off (stands down immediately)
  LGRD_ON       0     session flag, set by the laptop; reset to 0 at every boot
  LGRD_TIMEOUT  15    s of laptop silence before taking over
  LGRD_RADIUS   3     m, a trail point counts as reached within this distance
  LGRD_SYSID    1     MAVLink system id of the laptop (MAVROS 2: the target system, 1)
  LGRD_COMPID   191   MAVLink component id of the laptop (MAVROS 2: 191); 0 = any
  LGRD_SRV1_FN  74    SERVO1_FUNCTION on takeover (ThrottleRight)
  LGRD_SRV3_FN  73    SERVO3_FUNCTION on takeover (ThrottleLeft)
  LGRD_DETECT   1     1 = watch the laptop heartbeat itself (recommended)
                      0 = use ArduPilot's own GCS-heartbeat time (gcs:last_seen)
  LGRD_NEUTRAL  3     s of laptop silence before holding the thrusters at neutral;
                      0 = off. Keep it below LGRD_TIMEOUT.
  LGRD_TRAIL_D  2     m between two trail points (the spacing doubles when it is full)
  LGRD_PT_MAX   60    s to reach one trail point before skipping to the next
(LGRD_STAGE1 / WAIT / S1_MAX, table entries 3-5, existed until 2026-10-28; the retrace
replaced them. Their entries are not reused.)

Messages are kept under 50 characters (one MAVLink STATUSTEXT, "LinkGuard: " included):
longer ones are split and the station only shows the first piece.
--]]

local TAG = "LinkGuard: "
local PERIOD_MS = 200
local ARM_RETRY_MS = 2000
local ARM_REPORT_MS = 15000
local ARM_SETTLE_MS = 3500       -- disarmed on 73/74 before the first arm attempt
local SCALING_SETTLE_MS = 2000   -- disarmed on 73/74 this long = output range applied
local NEUTRAL_PWM = 1500
local MAX_TEXT = 50              -- MAVLink STATUSTEXT text field
local TRAIL_MAX = 1000           -- trail points kept (thinned by half when full)

-- ArduPilot Rover mode numbers
local MODE_MANUAL = 0
local MODE_HOLD = 4
local MODE_LOITER = 5
local MODE_RTL = 11
local MODE_GUIDED = 15
local MODE_NAME = {[0] = "MANUAL", [4] = "HOLD", [5] = "LOITER", [10] = "AUTO",
                   [11] = "RTL", [12] = "SMART_RTL", [15] = "GUIDED"}

-- SERVOx_FUNCTION values RCIN1..RCIN16 (RC passthrough)
local FN_RCIN1, FN_RCIN16 = 51, 66

-- MAV_SEVERITY
local SEV_CRITICAL, SEV_WARNING, SEV_NOTICE, SEV_INFO = 2, 4, 5, 6

---------------------------------------------------------------------------
-- Parameters
---------------------------------------------------------------------------
local PARAM_TABLE_KEY = 87     -- must be unique among the scripts on this autopilot
local PARAM_PREFIX = "LGRD_"

assert(param:add_table(PARAM_TABLE_KEY, PARAM_PREFIX, 16), "LinkGuard: could not add param table")

local function bind_add_param(name, idx, default_value)
  assert(param:add_param(PARAM_TABLE_KEY, idx, name, default_value),
         "LinkGuard: could not add param " .. PARAM_PREFIX .. name)
  local p = Parameter()
  assert(p:init(PARAM_PREFIX .. name), "LinkGuard: could not bind " .. PARAM_PREFIX .. name)
  return p
end

local P_ENABLE  = bind_add_param("ENABLE",  1, 1)
local P_TIMEOUT = bind_add_param("TIMEOUT", 2, 15)
-- 3, 4, 5: LGRD_STAGE1 / WAIT / S1_MAX until 2026-10-28 - never reuse these indices.
local P_RADIUS  = bind_add_param("RADIUS",  6, 3)
local P_SYSID   = bind_add_param("SYSID",   7, 1)
local P_COMPID  = bind_add_param("COMPID",  8, 191)
local P_SRV1_FN = bind_add_param("SRV1_FN", 9, 74)
local P_SRV3_FN = bind_add_param("SRV3_FN", 10, 73)
local P_DETECT  = bind_add_param("DETECT",  11, 1)
local P_ON      = bind_add_param("ON",      12, 0)
local P_NEUTRAL = bind_add_param("NEUTRAL", 13, 3)
local P_TRAIL_D = bind_add_param("TRAIL_D", 14, 2)
local P_PT_MAX  = bind_add_param("PT_MAX",  15, 60)

-- A session flag must never outlive the session: every boot starts OFF until the
-- laptop sets it again (runtime value only; the laptop's own set is what is saved).
param:set(PARAM_PREFIX .. "ON", 0)

---------------------------------------------------------------------------
-- Helpers
---------------------------------------------------------------------------
local function say(sev, text)
  gcs:send_text(sev, string.sub(TAG .. text, 1, MAX_TEXT))
end

local function now_ms()
  return millis():tofloat()
end

local function mode_name(m)
  return MODE_NAME[m] or tostring(m)
end

-- Dataflash log entry on every state change, for post-run analysis. Never fatal.
local STATE_CODE = {idle = 0, watch = 1, arming = 2, retrace = 3, stage2 = 4, held = 5}
local function log_state(state, age_ms)
  pcall(function()
    logger:write("LGRD", "State,Age", "Bf", STATE_CODE[state] or 255, (age_ms or -1) / 1000.0)
  end)
end

---------------------------------------------------------------------------
-- Laptop heartbeat detection
---------------------------------------------------------------------------
-- We listen to HEARTBEAT (msgid 0) ourselves and keep only the laptop's MAVROS
-- (LGRD_SYSID / LGRD_COMPID). ArduPilot's own "GCS last seen" accepts any component of
-- the GCS system id, and in a session that id is 1 - which on-boat BlueOS services may
-- also use, so it can keep looking "connected" with the laptop gone.
local mav_ok = false
local last_hb_ms = nil       -- last laptop heartbeat, autopilot clock

do
  local ok = pcall(function()
    mavlink:init(10, 1)        -- (queue length, number of msg ids) - the binding's order
    mavlink:register_rx_msgid(0)
  end)
  mav_ok = ok
end

-- msg is a packed mavlink_message_t: checksum(2) magic len incompat compat seq, then
-- sysid at byte 8 (1-based). Newer firmware (MAVLink 2.1, 298-byte struct) has a 32-bit
-- sysid; older (291 bytes) a 1-byte one.
local function header_ids(msg)
  if #msg >= 298 then
    local sysid, compid, msgid = string.unpack("<I4BI3", msg, 8)
    return sysid, compid, msgid
  end
  local sysid, compid, msgid = string.unpack("<BBI3", msg, 8)
  return sysid, compid, msgid
end

local function drain_heartbeats()
  if not mav_ok then return end
  local want_sys = math.floor(P_SYSID:get())
  local want_comp = math.floor(P_COMPID:get())
  for _ = 1, 20 do
    local msg = mavlink:receive_chan()
    if not msg then break end
    local ok, sysid, compid, msgid = pcall(header_ids, msg)
    if ok and msgid == 0 and sysid == want_sys and (want_comp == 0 or compid == want_comp) then
      if last_hb_ms == nil then
        say(SEV_INFO, string.format("laptop heard (sys %d comp %d)", sysid, compid))
      end
      last_hb_ms = now_ms()
    end
  end
end

-- Age of the laptop link in ms, or nil if the laptop was never seen since boot.
local function laptop_age_ms()
  if P_DETECT:get() >= 1 and mav_ok then
    if last_hb_ms == nil then return nil end
    return now_ms() - last_hb_ms
  end
  local seen = gcs:last_seen():tofloat()
  if seen == 0 then return nil end
  return now_ms() - seen
end

---------------------------------------------------------------------------
-- Thruster output range (see the header): has a disarmed 1 Hz pass run on 73/74?
---------------------------------------------------------------------------
local scaling_ok = false
local disarmed_on_fn_since = nil

local function on_autopilot_functions()
  local s1, s3 = param:get("SERVO1_FUNCTION"), param:get("SERVO3_FUNCTION")
  return s1 ~= nil and s3 ~= nil
     and math.floor(s1) == math.floor(P_SRV1_FN:get())
     and math.floor(s3) == math.floor(P_SRV3_FN:get())
end

local function track_scaling(armed)
  if scaling_ok then return end
  if not armed and on_autopilot_functions() then
    local t = now_ms()
    disarmed_on_fn_since = disarmed_on_fn_since or t
    if t - disarmed_on_fn_since >= SCALING_SETTLE_MS then
      scaling_ok = true
      say(SEV_INFO, "thruster range OK")
    end
  else
    disarmed_on_fn_since = nil
  end
end

---------------------------------------------------------------------------
-- Actions
---------------------------------------------------------------------------
local function thrusters_to_autopilot()
  local targets = {{"SERVO1_FUNCTION", P_SRV1_FN:get()}, {"SERVO3_FUNCTION", P_SRV3_FN:get()}}
  for _, t in ipairs(targets) do
    local name, want = t[1], math.floor(t[2])
    local cur = param:get(name)
    if cur == nil or math.floor(cur) ~= want then
      if not param:set(name, want) then
        say(SEV_CRITICAL, "could not set " .. name)
      end
    end
  end
end

-- Hold the RC channels that SERVO1/3 pass through at neutral. Does nothing once the
-- thrusters are on the autopilot's own functions.
local function hold_neutral()
  for _, name in ipairs({"SERVO1_FUNCTION", "SERVO3_FUNCTION"}) do
    local fn = param:get(name)
    if fn ~= nil then
      fn = math.floor(fn)
      if fn >= FN_RCIN1 and fn <= FN_RCIN16 then
        local ch = rc:get_channel(fn - FN_RCIN1 + 1)
        if ch then ch:set_override(NEUTRAL_PWM) end
      end
    end
  end
end

-- Try each mode in order; return the one that was accepted, or nil.
local function enter_first(modes)
  for _, m in ipairs(modes) do
    if vehicle:set_mode(m) then return m end
  end
  return nil
end

---------------------------------------------------------------------------
-- Trail: where the boat has been this session, oldest first
---------------------------------------------------------------------------
-- Plain lat/lng integers (1e-7 deg), not Location objects: 1000 points cost a few kB.
local trail_lat, trail_lng = {}, {}
local trail_n = 0
local trail_scale = 1        -- spacing = LGRD_TRAIL_D x this (doubled at every thinning)

local function trail_clear()
  trail_lat, trail_lng, trail_n, trail_scale = {}, {}, 0, 1
end

-- Trail point i as a Location (a copy of `template` keeps its altitude frame).
local function trail_point(i, template)
  local loc = template and template:copy() or Location()
  loc:lat(trail_lat[i])
  loc:lng(trail_lng[i])
  return loc
end

-- Keep every other point, always the newest, and double the spacing.
local function trail_spacing()
  return math.max(P_TRAIL_D:get(), 0.5) * trail_scale
end

local function trail_thin()
  local lat, lng, k = {}, {}, 0
  for i = 1, trail_n do
    if (trail_n - i) % 2 == 0 then
      k = k + 1
      lat[k], lng[k] = trail_lat[i], trail_lng[i]
    end
  end
  trail_lat, trail_lng, trail_n = lat, lng, k
  trail_scale = trail_scale * 2
  say(SEV_INFO, string.format("trail thinned, %.0f m spacing", trail_spacing()))
end

local function trail_record(here)
  if trail_n > 0 and here:get_distance(trail_point(trail_n, here)) < trail_spacing() then
    return
  end
  if trail_n >= TRAIL_MAX then trail_thin() end
  trail_n = trail_n + 1
  trail_lat[trail_n], trail_lng[trail_n] = here:lat(), here:lng()
end

-- Drop the points after `n` (already driven back over).
local function trail_cut(n)
  for i = trail_n, n + 1, -1 do
    trail_lat[i], trail_lng[i] = nil, nil
  end
  trail_n = math.min(trail_n, n)
end

---------------------------------------------------------------------------
-- State machine
---------------------------------------------------------------------------
local state = "idle"         -- idle | watch | arming | retrace | stage2 | held
local expected_mode = nil    -- mode the guardian put the vehicle in
local saved_fn = nil         -- {SERVO1, SERVO3}_FUNCTION before the takeover
local retrace_i = nil        -- trail point being driven to
local retrace_pt_ms = nil    -- when it became the target
local link_was_ok = true
local neutral_active = false
local last_reassert_ms = 0
local arm_start_ms = nil
local arm_not_before_ms = 0
local last_arm_try_ms = 0
local last_arm_report_ms = 0

local function set_state(s, age)
  if s == state then return end
  state = s
  log_state(s, age)
end

local function start_rtl(age)
  -- Mode first, then thrusters: the autopilot must already be steering when the
  -- outputs are handed over.
  if not ahrs:home_is_set() then
    say(SEV_CRITICAL, "no HOME set - holding position")
  end
  local m = enter_first({MODE_RTL, MODE_LOITER, MODE_HOLD})
  thrusters_to_autopilot()
  expected_mode = m
  set_state("stage2", age)
  if m == MODE_RTL then
    say(SEV_CRITICAL, "returning HOME (RTL)")
  else
    say(SEV_CRITICAL, "RTL refused, now in " .. mode_name(m or -1))
  end
end

-- First trail point, from the newest down, farther than LGRD_RADIUS from `here`.
local function next_point(i, here)
  while i > 1 and here:get_distance(trail_point(i, here)) <= P_RADIUS:get() do
    i = i - 1
  end
  return i
end

local function start_retrace(age)
  local here = ahrs:get_location()
  if trail_n == 0 or not here then
    say(SEV_WARNING, "no trail - RTL instead")
    start_rtl(age)
    return
  end
  retrace_i = next_point(trail_n, here)
  if vehicle:set_mode(MODE_GUIDED)
     and vehicle:set_target_location(trail_point(retrace_i, here)) then
    thrusters_to_autopilot()
    expected_mode = MODE_GUIDED
    retrace_pt_ms = now_ms()
    set_state("retrace", age)
    say(SEV_CRITICAL, string.format("retracing the path (%d pts)", retrace_i))
    return
  end
  say(SEV_WARNING, "GUIDED refused - RTL instead")
  start_rtl(age)
end

-- Armed: start the return proper.
local function go(age)
  start_retrace(age)
end

-- Disarmed: hold, hand the thrusters over (so pre-arm can pass) and arm once Rover has
-- applied the thruster output range (ARM_SETTLE_MS, see the header).
local function start_arming(age)
  thrusters_to_autopilot()
  expected_mode = enter_first({MODE_HOLD})
  arm_start_ms = now_ms()
  arm_not_before_ms = arm_start_ms + ARM_SETTLE_MS
  last_arm_try_ms = 0
  last_arm_report_ms = arm_start_ms
  set_state("arming", age)
  say(SEV_CRITICAL, "disarmed - arming it")
end

local function takeover(age)
  neutral_active = false
  say(SEV_CRITICAL, string.format("link lost %.0f s - taking over", age / 1000))
  -- The station's mapping (passthrough), given back when the laptop returns.
  local s1, s3 = param:get("SERVO1_FUNCTION"), param:get("SERVO3_FUNCTION")
  if s1 ~= nil and s3 ~= nil and not on_autopilot_functions() then
    saved_fn = {math.floor(s1), math.floor(s3)}
  else
    saved_fn = nil
  end
  if not arming:is_armed() then
    start_arming(age)
  elseif scaling_ok then
    go(age)
  else
    -- Armed, but the thruster output range was never seen applied: switching to 73/74
    -- now could leave idle at full reverse. Go through a disarmed pass instead.
    say(SEV_CRITICAL, "thrust range unchecked - re-arming")
    if arming:disarm() then
      start_arming(age)
    else
      say(SEV_CRITICAL, "disarm refused - retrace anyway")
      go(age)
    end
  end
end

-- The laptop is back: give the boat straight back to the station (HOLD, its servo
-- mapping, MANUAL - what `guardian.py reclaim` does), so the run goes on by itself.
local function resume(age)
  if state == "retrace" and retrace_i then
    trail_cut(retrace_i)
  elseif state == "held" then
    trail_cut(1)
  end
  enter_first({MODE_HOLD})
  local ok = true
  if saved_fn then
    ok = param:set("SERVO1_FUNCTION", saved_fn[1]) and ok
    ok = param:set("SERVO3_FUNCTION", saved_fn[2]) and ok
  end
  if not ok then
    say(SEV_CRITICAL, "could not restore SERVO1/3")
  end
  if not vehicle:set_mode(MODE_MANUAL) then
    say(SEV_CRITICAL, "MANUAL refused - " .. mode_name(vehicle:get_mode()))
  end
  saved_fn = nil
  expected_mode = nil
  retrace_i = nil
  neutral_active = false
  set_state("watch", age)
  say(SEV_NOTICE, "laptop back - mission resumed")
end

-- While the link is down, something else (ArduPilot's own GCS/RC failsafe) may switch
-- the mode; put ours back, at most every 2 s.
local function reassert(age)
  if vehicle:get_mode() == expected_mode then return end
  local t = now_ms()
  if t - last_reassert_ms < 2000 then return end
  last_reassert_ms = t
  if state == "retrace" then
    if not (vehicle:set_mode(MODE_GUIDED)
            and vehicle:set_target_location(trail_point(retrace_i, ahrs:get_location()))) then
      start_rtl(age)
    end
  elseif state == "arming" then
    local m = enter_first({MODE_HOLD})
    if m then expected_mode = m end
  elseif state == "held" then
    local m = enter_first({MODE_LOITER, MODE_HOLD})
    if m then expected_mode = m end
  else
    local m = enter_first({MODE_RTL, MODE_LOITER, MODE_HOLD})
    if m then expected_mode = m end
  end
end

local function update_retrace()
  local here = ahrs:get_location()
  if not here then return end
  local reached = here:get_distance(trail_point(retrace_i, here)) <= P_RADIUS:get()
  local late = now_ms() - retrace_pt_ms > P_PT_MAX:get() * 1000
  if not (reached or late) then return end
  if late and not reached then
    say(SEV_WARNING, string.format("point %d not reached, skipped", retrace_i))
  end
  if retrace_i <= 1 then
    expected_mode = enter_first({MODE_LOITER, MODE_HOLD})
    set_state("held")
    say(SEV_CRITICAL, "back at path start - holding")
    return
  end
  retrace_i = next_point(retrace_i - 1, here)
  retrace_pt_ms = now_ms()
  if not vehicle:set_target_location(trail_point(retrace_i, here)) then
    say(SEV_WARNING, "GUIDED target refused - RTL")
    start_rtl()
  end
end

local function update()
  drain_heartbeats()

  local armed = arming:is_armed()
  track_scaling(armed)

  if P_ENABLE:get() < 1 or P_ON:get() < 1 then
    if state ~= "idle" then
      say(SEV_WARNING, P_ENABLE:get() < 1 and "LGRD_ENABLE=0 - standing down"
                                          or "guardian OFF (LGRD_ON=0)")
    end
    neutral_active = false
    set_state("idle")
    return
  end

  local age = laptop_age_ms()
  local link_ok = age ~= nil and age < P_TIMEOUT:get() * 1000

  -- Flag on: become active once the laptop is heard. A new trail per session.
  if state == "idle" then
    if link_ok then
      trail_clear()
      set_state("watch", age)
      link_was_ok = true
      say(SEV_NOTICE, string.format("ON, retrace after %.0f s silence%s",
          P_TIMEOUT:get(), armed and "" or ", disarmed"))
    end
    return
  end

  if link_ok and not link_was_ok then
    say(SEV_NOTICE, "laptop back - " .. state .. ", " .. mode_name(vehicle:get_mode()))
  end
  link_was_ok = link_ok

  if state == "watch" then
    -- Armed or not, link up or not: the trail is always recorded.
    local here = ahrs:get_location()
    if here then trail_record(here) end
    if link_ok then
      local neutral_s = P_NEUTRAL:get()
      if neutral_s > 0 and age >= neutral_s * 1000 then
        if not neutral_active then
          neutral_active = true
          say(SEV_WARNING, string.format("no laptop %.0f s - thrusters neutral", age / 1000))
        end
        hold_neutral()
      elseif neutral_active then
        neutral_active = false
        say(SEV_NOTICE, "laptop back - thrusters released")
      end
    elseif age ~= nil then
      takeover(age)
    end
    return
  end

  -- From here on the guardian is in charge (arming / retrace / stage2 / held).
  if link_ok then
    -- The laptop is back: its mission goes on, nothing for the operator to do.
    resume(age)
    return
  end

  if not armed and state ~= "arming" then
    -- Link down: nobody could have disarmed it on purpose.
    start_arming(age)
    return
  end

  if state == "arming" then
    reassert(age)
    if armed then
      say(SEV_NOTICE, "armed")
      go(age)
      return
    end
    local t = now_ms()
    if t >= arm_not_before_ms and t - last_arm_try_ms >= ARM_RETRY_MS then
      last_arm_try_ms = t
      thrusters_to_autopilot()
      arming:arm()
    end
    if t - last_arm_report_ms >= ARM_REPORT_MS then
      last_arm_report_ms = t
      say(SEV_CRITICAL, string.format("not armed after %.0f s, see PreArm",
          (t - arm_start_ms) / 1000))
    end

  elseif state == "retrace" then
    reassert(age)
    if state == "retrace" then update_retrace() end

  else  -- stage2 (RTL fallback) or held (back at the path start)
    reassert(age)
  end
end

---------------------------------------------------------------------------
-- Entry point: a runtime error must not kill the guardian silently.
---------------------------------------------------------------------------
local function protected_update()
  local ok, err = pcall(update)
  if not ok then
    say(SEV_CRITICAL, "error: " .. tostring(err))
    return protected_update, 1000
  end
  return protected_update, PERIOD_MS
end

if mav_ok then
  say(SEV_INFO, "loaded - watching laptop heartbeat")
else
  say(SEV_WARNING, "loaded - no MAVLink rx, GCS timer")
end
return protected_update, 1000
