-- Minimal stand-ins for the campaign API used by skrolkpl.lua.
-- Every cm call that changes the game is recorded in CALLS as {name, args...}.
SKROLKPL_NO_FILE_LOG = true
CALLS = {}
LISTENERS = {}
FIRST_TICK = {}
SAVE_CALLBACKS = {}
LOAD_CALLBACKS = {}
CONTEXT_VALUES = {}
LOG = {}
TURN = 1
RANDOM = {}          -- queue of values random_number returns; empty -> 1
FACTIONS = {
	wh2_main_skv_clan_pestilens = { human = true, treasury = 5000, food = 52 },
	wh_main_emp_empire = { human = true, treasury = 3000, food = 0 },
}

local function rec(...) CALLS[#CALLS + 1] = {...} end

-- The game serialises saved values; a copy keeps later edits out of the "save".
function deep_copy(v)
	if type(v) ~= "table" then return v end
	local out = {}
	for k, x in pairs(v) do out[k] = deep_copy(x) end
	return out
end

function out(msg) LOG[#LOG + 1] = msg end

-- Plague components of the human Pestilens: key -> {UNLOCKED=, COOLDOWN=, BLESSED=}.
COMPONENTS = {}

local function component_list()
	local items = {}
	for key, states in pairs(COMPONENTS) do
		items[#items + 1] = {
			key = function() return key end,
			has_state = function(_, st) return states[st] == true end,
		}
	end
	table.sort(items, function(a, b) return a.key() < b.key() end)
	return { num_items = function() return #items end, item_at = function(_, i) return items[i + 1] end }
end

local function make_faction(key)
	local data = FACTIONS[key]
	return {
		plagues = function() return { plague_component_list = function() return component_list() end } end,
		name = function() return key end,
		is_null_interface = function() return data == nil end,
		is_human = function() return data.human end,
		treasury = function() return data.treasury end,
		pooled_resource_manager = function()
			return { resource = function(_, res)
				return { value = function() return res == "skaven_food" and data.food or 0 end,
				         is_null_interface = function() return false end }
			end }
		end,
	}
end

cm = {
	get_faction = function(_, key) return make_faction(key) end,
	model = function() return {
		turn_number = function() return TURN end,
		military_force_for_command_queue_index = function(_, cqi)
			return { command_queue_index = function() return cqi end, is_null_interface = function() return false end }
		end,
	} end,
	random_number = function(_, max, min)
		if RANDOM_FN then return RANDOM_FN(max) end
		local v = table.remove(RANDOM, 1) or 1
		if v > max then v = max end
		return v
	end,
	callback = function(_, f) f() end,
	treasury_mod = function(_, faction, amount)
		rec("treasury_mod", faction, amount)
		FACTIONS[faction].treasury = FACTIONS[faction].treasury + amount
	end,
	faction_add_pooled_resource = function(_, faction, res, factor, amount)
		rec("faction_add_pooled_resource", faction, res, factor, amount)
		FACTIONS[faction].food = FACTIONS[faction].food + amount
	end,
	apply_effect_bundle = function(_, ...) rec("apply_effect_bundle", ...) end,
	apply_effect_bundle_to_force = function(_, ...) rec("apply_effect_bundle_to_force", ...) end,
	apply_custom_effect_bundle_to_force = function(_, bundle, force)
		rec("apply_custom_force", bundle, force:command_queue_index())
	end,
	apply_custom_effect_bundle_to_region = function(_, bundle, region)
		rec("apply_custom_region", bundle, region:name())
	end,
	get_region = function(_, key) return { name = function() return key end,
	                                       is_null_interface = function() return false end } end,
	remove_effect_bundle_from_force = function(_, ...) rec("remove_effect_bundle_from_force", ...) end,
	apply_effect_bundle_to_region = function(_, ...) rec("apply_effect_bundle_to_region", ...) end,
	remove_effect_bundle_from_region = function(_, ...) rec("remove_effect_bundle_from_region", ...) end,
	trigger_incident = function(_, ...) rec("trigger_incident", ...) end,
	remove_effect_bundle = function(_, ...) rec("remove_effect_bundle", ...) end,
	create_new_custom_effect_bundle = function(_, key)
		local b = { key = key, effects = {} }
		function b:add_effect(effect, scope, value) self.effects[#self.effects + 1] = { effect, scope, value } end
		function b:set_duration(d) self.duration = d end
		return b
	end,
	create_payload = function()
		local p = { bundles = {} }
		function p:effect_bundle_to_faction(b) self.bundle = b; self.bundles[#self.bundles + 1] = b end
		return p
	end,
	create_incident_builder = function(_, key)
		local ib = { key = key }
		function ib:set_payload(p) self.payload = p end
		return ib
	end,
	launch_custom_incident_from_builder = function(_, builder, faction)
		LAUNCHED = builder
		rec("launch_custom_incident", builder.key, faction:name())
	end,
	override_ui = function(_, ...) rec("override_ui", ...) end,
	set_plague_component_state = function(_, faction, key, state, value)
		rec("set_plague_component_state", faction:name(), key, state, value)
		COMPONENTS[key] = COMPONENTS[key] or {}
		COMPONENTS[key][state] = value
	end,
	add_first_tick_callback = function(_, f) FIRST_TICK[#FIRST_TICK + 1] = f end,
	add_saving_game_callback = function(_, f) SAVE_CALLBACKS[#SAVE_CALLBACKS + 1] = f end,
	add_loading_game_callback = function(_, f) LOAD_CALLBACKS[#LOAD_CALLBACKS + 1] = f end,
	save_named_value = function(_, name, value) SAVED = SAVED or {}; SAVED[name] = deep_copy(value) end,
	load_named_value = function(_, name, default) return (SAVED and SAVED[name] ~= nil) and SAVED[name] or default end,
	is_new_game = function() return false end,
}

common = {
	set_context_value = function(name, value) CONTEXT_VALUES[name] = value end,
	get_localised_string = function(key) return LOCALISED and LOCALISED[key] or "" end,
}

core = {
	add_listener = function(_, name, event, cond, cb, persistent)
		LISTENERS[#LISTENERS + 1] = { name = name, event = event, cond = cond, cb = cb }
	end,
	get_ui_root = function() return {} end,
}

-- A fake UI: when PANEL_OPEN, find_uicomponent(parent, ..., id) returns the component named by the
-- last id, creating it on first use. Components record visibility, state, disabled flag and clicks.
UI = {}
PANEL_OPEN = false
UI_TEXT = {}   -- id -> state text the fake component reports

local function make_uic(id)
	local uic = { id = id, visible = true, state = "active", disabled = false, clicks = 0 }
	function uic:SetVisible(v) self.visible = v end
	function uic:SetState(s) self.state = s end
	function uic:SetDisabled(d) self.disabled = d end
	function uic:SetStateText(t) self.text = t end
	function uic:GetStateText() return UI_TEXT[self.id] or "" end
	function uic:SimulateLClick() self.clicks = self.clicks + 1; rec("click", self.id) end
	return uic
end

function find_uicomponent(parent, ...)
	if not PANEL_OPEN then return nil end
	local ids = {...}
	local id = ids[#ids]
	if id == nil then return nil end
	UI[id] = UI[id] or make_uic(id)
	return UI[id]
end

-- Fire an event at every listener registered for it.
function fire(event, context)
	for _, l in ipairs(LISTENERS) do
		if l.event == event then
			local ok = l.cond == true or (type(l.cond) == "function" and l.cond(context))
			if ok then l.cb(context) end
		end
	end
end

function ritual_context(ritual_key, faction_key)
	return {
		ritual = function() return { ritual_key = function() return ritual_key end } end,
		performing_faction = function() return make_faction(faction_key) end,
	}
end

function faction_context(faction_key)
	return { faction = function() return make_faction(faction_key) end }
end

local function make_force(cqi, faction_key)
	return {
		command_queue_index = function() return cqi end,
		faction = function() return make_faction(faction_key) end,
	}
end

function force_infection(cqi, faction_key, creator_key, removed)
	return {
		plague = function() return { creator_faction = function() return make_faction(creator_key) end } end,
		target_force = function() return make_force(cqi, faction_key) end,
		is_removed = function() return removed == true end,
		is_creation = function() return false end,
	}
end

-- The game's RegionInfectionEvent has no region() (in game: "attempt to call method 'region'").
function region_infection(region_key, owner_key, creator_key)
	return {
		plague = function() return { creator_faction = function() return make_faction(creator_key) end } end,
		target_region = function() return { name = function() return region_key end,
		                                    owning_faction = function() return make_faction(owner_key) end } end,
	}
end

function region_plague_state(region_key, infected)
	return {
		region = function() return { name = function() return region_key end } end,
		is_infected = function() return infected end,
	}
end
