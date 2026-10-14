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
    3. If the laptop is silent for LGRD_TIMEOUT seconds while active:
         a. hand the thrusters back to the autopilot. Our stack drives them through RC
            passthrough (SERVO1/3_FUNCTION = 51/53), which ArduPilot's navigation modes
            cannot drive, so SERVO1/3_FUNCTION are set to LGRD_SRV1_FN / LGRD_SRV3_FN
            (74 ThrottleRight / 73 ThrottleLeft, the BlueBoat default). Not saved: a
            reboot restores the stored values.
         b. ARM the autopilot if it is not armed (after an E-STOP, or when arming failed
            at connection). This only works after (a): ArduPilot refuses to arm while the
            thrusters are on passthrough. It keeps retrying (pre-arm checks such as a GPS
            fix must pass) and holds meanwhile.
         c. (optional, LGRD_STAGE1=1) drive back to the last point where the link was
            alive and wait there LGRD_WAIT s, in case the link comes back;
         d. RTL: ArduPilot drives the boat to HOME (straight line) and holds there.
    4. When the link comes back, the boat keeps doing what the guardian set until the
       operator takes control back (MCS GUARDIAN box "Take back control", or any mode
       change from a ground station). It never resumes a mission. A disarm while the
       laptop is connected (the operator's E-STOP) stands the guardian down; a disarm
       nobody could have sent (link down) is undone.

HOME is set by ArduPilot at arming (the session start) and moved by the laptop to the
start of each run while the link is up.

Parameters (appear after the first boot with the script; see README.md):
  LGRD_ENABLE   1     master switch; 0 = guardian off (stands down immediately)
  LGRD_ON       0     session flag, set by the laptop; reset to 0 at every boot
  LGRD_TIMEOUT  5     s of laptop silence before taking over
  LGRD_STAGE1   0     1 = first go back to the last point with a link
  LGRD_WAIT     30    s to wait at that point before RTL
  LGRD_S1_MAX   180   s max for stage 1 (getting there + waiting), then RTL
  LGRD_RADIUS   5     m, "arrived" radius for stage 1
  LGRD_SYSID    1     MAVLink system id of the laptop (MAVROS 2: the target system, 1)
  LGRD_COMPID   191   MAVLink component id of the laptop (MAVROS 2: 191); 0 = any
  LGRD_SRV1_FN  74    SERVO1_FUNCTION on takeover (ThrottleRight)
  LGRD_SRV3_FN  73    SERVO3_FUNCTION on takeover (ThrottleLeft)
  LGRD_DETECT   1     1 = watch the laptop heartbeat itself (recommended)
                      0 = use ArduPilot's own GCS-heartbeat time (gcs:last_seen)
--]]

local TAG = "LinkGuard: "
local PERIOD_MS = 200
local ARM_RETRY_MS = 2000
local ARM_REPORT_MS = 15000

-- ArduPilot Rover mode numbers
local MODE_HOLD = 4
local MODE_LOITER = 5
local MODE_RTL = 11
local MODE_GUIDED = 15
local MODE_NAME = {[0] = "MANUAL", [4] = "HOLD", [5] = "LOITER", [10] = "AUTO",
                   [11] = "RTL", [12] = "SMART_RTL", [15] = "GUIDED"}

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
local P_TIMEOUT = bind_add_param("TIMEOUT", 2, 5)
local P_STAGE1  = bind_add_param("STAGE1",  3, 0)
local P_WAIT    = bind_add_param("WAIT",    4, 30)
local P_S1_MAX  = bind_add_param("S1_MAX",  5, 180)
local P_RADIUS  = bind_add_param("RADIUS",  6, 5)
local P_SYSID   = bind_add_param("SYSID",   7, 1)
local P_COMPID  = bind_add_param("COMPID",  8, 191)
local P_SRV1_FN = bind_add_param("SRV1_FN", 9, 74)
local P_SRV3_FN = bind_add_param("SRV3_FN", 10, 73)
local P_DETECT  = bind_add_param("DETECT",  11, 1)
local P_ON      = bind_add_param("ON",      12, 0)

-- A session flag must never outlive the session: every boot starts OFF until the
-- laptop sets it again (runtime value only; the laptop's own set is what is saved).
param:set(PARAM_PREFIX .. "ON", 0)

---------------------------------------------------------------------------
-- Helpers
---------------------------------------------------------------------------
local function say(sev, text)
  gcs:send_text(sev, TAG .. text)
end

local function now_ms()
  return millis():tofloat()
end

local function mode_name(m)
  return MODE_NAME[m] or tostring(m)
end

-- Dataflash log entry on every state change, for post-run analysis. Never fatal.
local STATE_CODE = {idle = 0, watch = 1, arming = 2, stage1 = 3, stage2 = 4, held = 5}
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
    mavlink:init(10, 1)
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
        say(SEV_INFO, string.format("laptop heartbeat seen (sys %d comp %d)", sysid, compid))
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

-- Try each mode in order; return the one that was accepted, or nil.
local function enter_first(modes)
  for _, m in ipairs(modes) do
    if vehicle:set_mode(m) then return m end
  end
  return nil
end

---------------------------------------------------------------------------
-- State machine
---------------------------------------------------------------------------
local state = "idle"         -- idle | watch | arming | stage1 | stage2 | held
local expected_mode = nil    -- mode the guardian put the vehicle in
local last_link_loc = nil    -- last position with a live laptop link
local stage1_start_ms = nil
local arrived_ms = nil
local link_was_ok = true
local last_reassert_ms = 0
local arm_start_ms = nil
local last_arm_try_ms = 0
local last_arm_report_ms = 0

local function set_state(s, age)
  state = s
  log_state(s, age)
end

local function start_rtl(age)
  -- Mode first, then thrusters: the autopilot must already be steering when the
  -- outputs are handed over.
  if not ahrs:home_is_set() then
    say(SEV_CRITICAL, "no HOME set - RTL impossible, holding position")
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

local function start_stage1(age)
  if last_link_loc and vehicle:set_mode(MODE_GUIDED)
     and vehicle:set_target_location(last_link_loc) then
    thrusters_to_autopilot()
    expected_mode = MODE_GUIDED
    stage1_start_ms = now_ms()
    arrived_ms = nil
    set_state("stage1", age)
    say(SEV_CRITICAL, "going back to the last point with a laptop link")
    return
  end
  say(SEV_WARNING, "cannot go to the last-link point, returning HOME instead")
  start_rtl(age)
end

-- Armed: start the return proper.
local function go(age)
  if P_STAGE1:get() >= 1 then
    start_stage1(age)
  else
    start_rtl(age)
  end
end

-- Disarmed: hold, hand the thrusters over (so pre-arm can pass) and arm.
local function start_arming(age)
  thrusters_to_autopilot()
  expected_mode = enter_first({MODE_HOLD})
  arm_start_ms = now_ms()
  last_arm_try_ms = 0
  last_arm_report_ms = now_ms()
  set_state("arming", age)
  say(SEV_CRITICAL, "autopilot disarmed - arming it")
end

local function takeover(age)
  say(SEV_CRITICAL, string.format("laptop link lost for %.0f s - taking over", age / 1000))
  if arming:is_armed() then
    thrusters_to_autopilot()
    go(age)
  else
    start_arming(age)
  end
end

-- While the link is down, something else (ArduPilot's own GCS/RC failsafe) may switch
-- the mode; put ours back, at most every 2 s.
local function reassert(age)
  if vehicle:get_mode() == expected_mode then return end
  local t = now_ms()
  if t - last_reassert_ms < 2000 then return end
  last_reassert_ms = t
  if state == "stage1" then
    if not (vehicle:set_mode(MODE_GUIDED) and vehicle:set_target_location(last_link_loc)) then
      start_rtl(age)
    end
  elseif state == "arming" then
    local m = enter_first({MODE_HOLD})
    if m then expected_mode = m end
  else
    local m = enter_first({MODE_RTL, MODE_LOITER, MODE_HOLD})
    if m then expected_mode = m end
  end
end

local function update()
  drain_heartbeats()

  if P_ENABLE:get() < 1 or P_ON:get() < 1 then
    if state ~= "idle" then
      say(SEV_WARNING, P_ENABLE:get() < 1 and "disabled (LGRD_ENABLE=0), standing down"
                                          or "guardian OFF (LGRD_ON=0)")
    end
    set_state("idle")
    return
  end

  local armed = arming:is_armed()
  local age = laptop_age_ms()
  local link_ok = age ~= nil and age < P_TIMEOUT:get() * 1000

  -- Flag on: become active once the laptop is heard.
  if state == "idle" then
    if link_ok then
      set_state("watch", age)
      link_was_ok = true
      say(SEV_NOTICE, string.format("ON - return HOME after %.0f s without laptop%s",
          P_TIMEOUT:get(), armed and "" or " (autopilot disarmed: will arm itself)"))
    end
    return
  end

  if link_ok and not link_was_ok then
    say(SEV_NOTICE, "laptop link back - " .. state .. ", vehicle in " .. mode_name(vehicle:get_mode()))
  end
  link_was_ok = link_ok

  if state == "watch" then
    -- Armed or not (an E-STOP disarms): the guardian stays on and arms itself if needed.
    if link_ok then
      local loc = ahrs:get_location()
      if loc then last_link_loc = loc end
    elseif age ~= nil then
      takeover(age)
    end
    return
  end

  -- From here on the guardian is in charge (arming / stage1 / stage2 / held).
  if not armed and state ~= "arming" then
    if link_ok then
      -- Only someone with a working link can have disarmed it: the operator stood it down.
      say(SEV_NOTICE, "disarmed by the operator - watching again")
      set_state("watch", age)
      return
    end
    start_arming(age)
    return
  end

  if state == "arming" then
    if link_ok then
      -- The link came back before the boat could arm: it stays disarmed in HOLD and the
      -- operator takes over (a later loss starts again from "watch").
      set_state("watch", age)
      say(SEV_NOTICE, "link back before arming - boat stopped in HOLD, take back control")
      return
    end
    reassert(age)
    if armed then
      say(SEV_NOTICE, "armed")
      go(age)
      return
    end
    local t = now_ms()
    if t - last_arm_try_ms >= ARM_RETRY_MS then
      last_arm_try_ms = t
      thrusters_to_autopilot()
      arming:arm()
    end
    if t - last_arm_report_ms >= ARM_REPORT_MS then
      last_arm_report_ms = t
      say(SEV_CRITICAL, string.format("still cannot arm after %.0f s (see PreArm messages), retrying",
          (t - arm_start_ms) / 1000))
    end

  elseif state == "stage1" then
    if link_ok then
      -- Stage 1 did its job: stop at the last-link point and wait for the operator.
      local m = enter_first({MODE_LOITER, MODE_HOLD})
      expected_mode = m
      set_state("held", age)
      say(SEV_NOTICE, "holding position, waiting for the operator")
    else
      reassert(age)
      local here = ahrs:get_location()
      if here and last_link_loc and here:get_distance(last_link_loc) <= P_RADIUS:get() then
        arrived_ms = arrived_ms or now_ms()
      end
      local waited = arrived_ms and (now_ms() - arrived_ms) > P_WAIT:get() * 1000
      local too_long = (now_ms() - stage1_start_ms) > P_S1_MAX:get() * 1000
      if waited or too_long then
        say(SEV_WARNING, "no link at the last-link point")
        start_rtl(age)
      end
    end

  elseif state == "stage2" or state == "held" then
    if link_ok then
      -- Any mode change while the laptop is back = the operator took control.
      if vehicle:get_mode() ~= expected_mode then
        say(SEV_NOTICE, "operator took control (" .. mode_name(vehicle:get_mode()) .. ") - watching again")
        set_state("watch", age)
      end
    elseif state == "held" then
      -- Link lost again while waiting for the operator: straight home this time.
      say(SEV_CRITICAL, "laptop link lost again - taking over")
      start_rtl(age)
    else
      reassert(age)
    end
  end
end

---------------------------------------------------------------------------
-- Entry point: a runtime error must not kill the guardian silently.
---------------------------------------------------------------------------
local function protected_update()
  local ok, err = pcall(update)
  if not ok then
    gcs:send_text(SEV_CRITICAL, TAG .. "internal error: " .. tostring(err))
    return protected_update, 1000
  end
  return protected_update, PERIOD_MS
end

if mav_ok then
  say(SEV_INFO, "loaded - watching laptop heartbeat")
else
  say(SEV_WARNING, "loaded - MAVLink rx unavailable, using GCS last-seen (see README)")
end
return protected_update, 1000
