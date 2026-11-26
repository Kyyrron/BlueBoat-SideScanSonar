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
         c'. SAFETY WAY BACK instead of (c), during a run of a GPS-anchored pattern that
            has one (LGRD_SAFE = 2, see below): join the way back at the point closest to
            the boat, follow its points in order to the last one, LOITER there.
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

GUARDIAN HOME (2026-11-26) = the trail's first point: where the retrace ends and the boat
LOITERs. It is where the guardian came ON (usually the session start) until the operator
presses Set Home in the station: the laptop sets LGRD_HOME = 1, the script drops the trail,
records the boat's position as its new first point and answers "home <lat> <lng> set"
(1e-7 deg). The laptop shows that point on its map. LGRD_HOME = 3 asks for the line again.
While the guardian is ON, ArduPilot's own HOME (the RTL fallback's destination) is kept on
the Guardian Home: re-set every 5 s while armed, and once more at a takeover. Nothing else
moves it (the laptop no longer moves HOME at run start / end).
The last point of a route (the Guardian Home, or the end of a safety way back) counts as
reached within WP_RADIUS + 0.5 m (at most LGRD_RADIUS), so the boat drives up to it
before holding there.

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
  LGRD_PT_MAX   60    s to reach one point before skipping to the next (longer for a
                      long leg: 2 x leg / WP_SPEED)
  LGRD_SAFE     0     safety way back: 0 none, 1 requested by the laptop, 2 loaded and
                      checked (set by this script), -1 invalid. Reset to 0 at every boot.
  LGRD_SAFE_N   0     number of points the laptop uploaded
  LGRD_HOME     0     Set Home: 1 = set it here (laptop), 3 = report it (laptop); the script
                      answers 0 (done) or -1 (refused). Reset to 0 at every boot.
(LGRD_STAGE1 / WAIT / S1_MAX, table entries 3-5, existed until 2026-10-28; the retrace
replaced them. Their entries are not reused.)

Safety way back (2026-11-25)
  A GPS-anchored pattern may carry a hand-drawn "safety way back". At START RUN the laptop
  (guardian.py) uploads it as the autopilot's MISSION (item 0 = home, items 1..N =
  NAV_WAYPOINT; we never fly AUTO, so the mission storage is free), sets LGRD_SAFE_N = N
  and LGRD_SAFE = 1. This script then reads and checks the mission (N items, all
  NAV_WAYPOINT) and answers LGRD_SAFE = 2 (ready) or -1 (invalid). At STOP RUN the laptop
  sets LGRD_SAFE = 0. A takeover while LGRD_SAFE = 2 follows the way back; otherwise the
  trail.

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
local SAFE_MAX = 200             -- safety way back points accepted
local SAFE_CHUNK = 25            -- mission items read per tick (VM instruction budget)
local NAV_WAYPOINT = 16          -- MAV_CMD_NAV_WAYPOINT

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

assert(param:add_table(PARAM_TABLE_KEY, PARAM_PREFIX, 20), "LinkGuard: could not add param table")

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
local P_SAFE    = bind_add_param("SAFE",    16, 0)
local P_SAFE_N  = bind_add_param("SAFE_N",  17, 0)
local P_HOME    = bind_add_param("HOME",    18, 0)

-- A session flag must never outlive the session: every boot starts OFF until the
-- laptop sets it again (runtime value only; the laptop's own set is what is saved).
param:set(PARAM_PREFIX .. "ON", 0)
param:set(PARAM_PREFIX .. "SAFE", 0)    -- likewise: a way back belongs to one run
param:set(PARAM_PREFIX .. "HOME", 0)    -- no Set Home request survives a reboot

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

local home_said = false       -- the current Guardian Home was announced to the laptop
local home_src = "on"        -- "on" (where the guardian came ON) | "set" (Set Home)

local function trail_clear()
  trail_lat, trail_lng, trail_n, trail_scale = {}, {}, 0, 1
  home_said, home_src = false, "on"
end

-- A Location from 1e-7 deg integers (a copy of `template` keeps its altitude frame).
local function make_loc(lat, lng, template)
  local loc = template and template:copy() or Location()
  loc:lat(lat)
  loc:lng(lng)
  return loc
end

-- Trail point i as a Location.
local function trail_point(i, template)
  return make_loc(trail_lat[i], trail_lng[i], template)
end

-- Keep every other point, always the newest and the first (the Guardian Home), and
-- double the spacing.
local function trail_spacing()
  return math.max(P_TRAIL_D:get(), 0.5) * trail_scale
end

local function trail_thin()
  local lat, lng, k = {}, {}, 0
  for i = 1, trail_n do
    if i == 1 or (trail_n - i) % 2 == 0 then
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
-- Guardian Home = trail point 1 (2026-11-26, see the header)
---------------------------------------------------------------------------
local HOME_SYNC_MS = 5000
local last_home_sync_ms = 0

local function say_home()
  if trail_n < 1 then
    say(SEV_INFO, "home none")
    return
  end
  say(SEV_NOTICE, string.format("home %d %d %s", math.floor(trail_lat[1]),
      math.floor(trail_lng[1]), home_src))
  home_said = true
end

-- ArduPilot's HOME (the RTL fallback's destination) onto the Guardian Home. Never fatal:
-- an older firmware without the binding keeps its own HOME.
local function home_sync(here)
  if trail_n < 1 or not here then return end
  last_home_sync_ms = now_ms()
  pcall(function()
    local pt = trail_point(1, here)
    local h = ahrs:get_home()
    if h == nil or h:get_distance(pt) > 1.0 then
      ahrs:set_home(pt)
    end
  end)
end

-- Set Home: the trail restarts at the boat's position, which becomes the Guardian Home.
local function set_home(here)
  trail_clear()
  trail_n = 1
  trail_lat[1], trail_lng[1] = here:lat(), here:lng()
  home_src = "set"
  home_sync(here)
  say_home()
end

-- The laptop's LGRD_HOME request (1 = Set Home, 3 = report). Only while watching: the
-- guardian ON and the link up (the only time the laptop can write it anyway).
local function update_home_request(watching, here)
  local want = math.floor(P_HOME:get())
  if want ~= 1 and want ~= 3 then return end
  if want == 3 then
    say_home()
    param:set(PARAM_PREFIX .. "HOME", 0)
    return
  end
  if not watching then
    say(SEV_WARNING, "set home refused: guardian not ON")
    param:set(PARAM_PREFIX .. "HOME", -1)
    return
  end
  if not here then
    say(SEV_WARNING, "set home refused: no position")
    param:set(PARAM_PREFIX .. "HOME", -1)
    return
  end
  set_home(here)
  param:set(PARAM_PREFIX .. "HOME", 0)
end

---------------------------------------------------------------------------
-- Safety way back: read from the autopilot's mission when the laptop asks
---------------------------------------------------------------------------
-- The loaded way back (LGRD_SAFE = 2), nil when there is none: lat/lng (1e-7 deg), and
-- for the closest-point search, north/east metres from point 1 (`origin`) plus each
-- segment's vector and 1/length^2. All of it is computed while the mission is read,
-- SAFE_CHUNK items per tick, so no tick exceeds the VM instruction budget.
local safe = nil
local loading = nil          -- the same while it is being read, plus `i` (next item)

local function safe_fail(why)
  loading = nil
  safe = nil
  param:set(PARAM_PREFIX .. "SAFE", -1)
  say(SEV_WARNING, "way back invalid: " .. why)
end

-- One tick of the loader: called every update, whatever the guardian state.
local function update_safe()
  local want = math.floor(P_SAFE:get())
  if want == 2 and safe == nil then
    -- "ready" without a loaded way back (set from outside): load it properly.
    param:set(PARAM_PREFIX .. "SAFE", 1)
    want = 1
  end
  if want ~= 1 then
    loading = nil
    if want ~= 2 and safe ~= nil then
      safe = nil
      if want == 0 then say(SEV_INFO, "way back cleared") end
    end
    return
  end
  if loading == nil then
    local n = math.floor(P_SAFE_N:get())
    local items = mission:num_commands() - 1        -- item 0 is HOME
    if n < 2 or n > SAFE_MAX then
      safe_fail(string.format("N=%d", n))
      return
    end
    if items ~= n then
      safe_fail(string.format("%d items, want %d", items, n))
      return
    end
    safe = nil
    loading = {lat = {}, lng = {}, n = n, north = {}, east = {}, dn = {}, de = {}, inv2 = {},
               i = 1}
  end
  local L = loading
  local last = math.min(L.n, L.i + SAFE_CHUNK - 1)
  for i = L.i, last do
    local item = mission:get_item(i)
    if item == nil or item:command() ~= NAV_WAYPOINT then
      safe_fail(string.format("item %d", i))
      return
    end
    local lat, lng = item:x(), item:y()
    local loc = make_loc(lat, lng)
    if i == 1 then L.origin = loc end
    local ne = L.origin:get_distance_NE(loc)
    L.lat[i], L.lng[i], L.north[i], L.east[i] = lat, lng, ne:x(), ne:y()
    if i > 1 then
      local dn, de = L.north[i] - L.north[i - 1], L.east[i] - L.east[i - 1]
      local len2 = dn * dn + de * de
      L.dn[i - 1], L.de[i - 1] = dn, de
      L.inv2[i - 1] = len2 > 1e-6 and 1 / len2 or 0
    end
  end
  L.i = last + 1
  if L.i <= L.n then return end
  safe, loading = L, nil
  param:set(PARAM_PREFIX .. "SAFE", 2)
  say(SEV_INFO, string.format("way back %d pts ready", safe.n))
end

-- Closest point of the way back to `here`: returns (index of the end point of its
-- segment, the closest point as a Location).
local function safe_closest(here)
  local p = safe.origin:get_distance_NE(here)
  local pn, pe = p:x(), p:y()
  local N, E, DN, DE, INV2 = safe.north, safe.east, safe.dn, safe.de, safe.inv2
  local best_d2, best_i, best_t = math.huge, 1, 0
  for i = 1, safe.n - 1 do
    local dn, de = DN[i], DE[i]
    local qn, qe = pn - N[i], pe - E[i]
    local t = (qn * dn + qe * de) * INV2[i]
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    qn, qe = qn - t * dn, qe - t * de
    local d2 = qn * qn + qe * qe
    if d2 < best_d2 then
      best_d2, best_i, best_t = d2, i, t
    end
  end
  local join = safe.origin:copy()
  join:offset(N[best_i] + best_t * DN[best_i], E[best_i] + best_t * DE[best_i])
  return best_i + 1, join
end

---------------------------------------------------------------------------
-- Route being driven: the trail (newest -> oldest) or the safety way back (in order)
---------------------------------------------------------------------------
-- {lat, lng, step = -1 | 1, last = index of the end point, trail = true | nil}
local route = nil

local function route_point(i, template)
  return make_loc(route.lat[i], route.lng[i], template)
end

---------------------------------------------------------------------------
-- State machine
---------------------------------------------------------------------------
local state = "idle"         -- idle | watch | arming | retrace | stage2 | held
local expected_mode = nil    -- mode the guardian put the vehicle in
local saved_fn = nil         -- {SERVO1, SERVO3}_FUNCTION before the takeover
local retrace_i = nil        -- route point being driven to
local retrace_pt_ms = nil    -- when the current target was set
local retrace_allow_ms = 0   -- time allowed to reach it
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
  route = nil
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

-- Arm the per-target timer: LGRD_PT_MAX, or longer for a long leg at a slow WP_SPEED.
local function start_target_timer(here)
  retrace_pt_ms = now_ms()
  local speed = param:get("WP_SPEED") or 0.5
  if speed < 0.1 then speed = 0.1 end
  local leg = here:get_distance(route_point(retrace_i, here))
  retrace_allow_ms = math.max(P_PT_MAX:get(), 2 * leg / speed) * 1000
end

-- From point i along the route, skip the points already within LGRD_RADIUS of `here`
-- (never past the route's end point).
local function skip_near(i, here)
  while i ~= route.last and here:get_distance(route_point(i, here)) <= P_RADIUS:get() do
    i = i + route.step
  end
  return i
end

-- GUIDED towards the current route point; RTL if that is refused.
local function drive_route(age, here, text)
  if vehicle:set_mode(MODE_GUIDED) and vehicle:set_target_location(route_point(retrace_i, here)) then
    thrusters_to_autopilot()
    expected_mode = MODE_GUIDED
    start_target_timer(here)
    set_state("retrace", age)
    say(SEV_CRITICAL, text)
    return
  end
  say(SEV_WARNING, "GUIDED refused - RTL instead")
  start_rtl(age)
end

local function start_retrace(age)
  local here = ahrs:get_location()
  if trail_n == 0 or not here then
    say(SEV_WARNING, "no trail - RTL instead")
    start_rtl(age)
    return
  end
  route = {lat = trail_lat, lng = trail_lng, step = -1, last = 1, trail = true}
  retrace_i = skip_near(trail_n, here)
  drive_route(age, here, string.format("retracing the path (%d pts)", retrace_i))
end

-- The safety way back: its closest point to the boat, then its points to the end.
local function start_safe(age)
  local here = ahrs:get_location()
  if not here then
    start_retrace(age)
    return
  end
  local first, join = safe_closest(here)
  local lat, lng, n = {join:lat()}, {join:lng()}, 1
  for k = first, safe.n do
    n = n + 1
    lat[n], lng[n] = safe.lat[k], safe.lng[k]
  end
  route = {lat = lat, lng = lng, step = 1, last = n}
  retrace_i = skip_near(1, here)
  drive_route(age, here, string.format("safety way back from pt %d/%d", first, safe.n))
end

-- Armed: start the return proper (the safety way back if one is loaded).
local function go(age)
  home_sync(ahrs:get_location())   -- the RTL fallback goes to the Guardian Home too
  if safe then
    start_safe(age)
  else
    start_retrace(age)
  end
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
  if route and route.trail then
    if state == "retrace" and retrace_i then
      trail_cut(retrace_i)
    elseif state == "held" then
      trail_cut(1)
    end
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
  route = nil
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
            and vehicle:set_target_location(route_point(retrace_i, ahrs:get_location()))) then
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

-- Arrival distance: LGRD_RADIUS on the way, but at the route's last point (the Guardian
-- Home, or the end of the way back) ArduPilot's own WP_RADIUS + 0.5 m, so the boat drives
-- up to the point before holding (at most LGRD_RADIUS).
local function arrival_radius(i)
  local r = P_RADIUS:get()
  if i ~= route.last then return r end
  local wp = param:get("WP_RADIUS")
  if wp == nil then return r end
  return math.min(r, math.max(wp, 0.2) + 0.5)
end

local function update_retrace()
  local here = ahrs:get_location()
  if not here then return end
  local reached = here:get_distance(route_point(retrace_i, here)) <= arrival_radius(retrace_i)
  local late = now_ms() - retrace_pt_ms > retrace_allow_ms
  if not (reached or late) then return end
  if late and not reached then
    say(SEV_WARNING, string.format("point %d not reached, skipped", retrace_i))
  end
  if retrace_i == route.last then
    expected_mode = enter_first({MODE_LOITER, MODE_HOLD})
    set_state("held")
    say(SEV_CRITICAL, route.trail and "back at path start - holding"
                                   or "end of way back - holding")
    return
  end
  retrace_i = skip_near(retrace_i + route.step, here)
  if not vehicle:set_target_location(route_point(retrace_i, here)) then
    say(SEV_WARNING, "GUIDED target refused - RTL")
    start_rtl()
    return
  end
  start_target_timer(here)
end

local function update()
  drain_heartbeats()
  update_safe()

  local armed = arming:is_armed()
  track_scaling(armed)

  if P_ENABLE:get() < 1 or P_ON:get() < 1 then
    if state ~= "idle" then
      say(SEV_WARNING, P_ENABLE:get() < 1 and "LGRD_ENABLE=0 - standing down"
                                          or "guardian OFF (LGRD_ON=0)")
    end
    neutral_active = false
    set_state("idle")
    update_home_request(false, nil)
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
    else
      update_home_request(false, nil)
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
    update_home_request(true, here)
    if here then trail_record(here) end
    -- The Guardian Home: announced once (the laptop draws it), ArduPilot's HOME kept on
    -- it while armed (disarmed, Rover moves its HOME itself; a takeover re-syncs).
    if trail_n >= 1 and not home_said then say_home() end
    if armed and here and now_ms() - last_home_sync_ms >= HOME_SYNC_MS then
      home_sync(here)
    end
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
  update_home_request(false, nil)
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
