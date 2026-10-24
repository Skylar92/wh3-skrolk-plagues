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

local function make_faction(key)
	local data = FACTIONS[key]
	return {
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
	model = function() return { turn_number = function() return TURN end } end,
	random_number = function(_, max, min)
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
	override_ui = function(_, ...) rec("override_ui", ...) end,
	set_plague_component_state = function(_, faction, ...) rec("set_plague_component_state", faction:name(), ...) end,
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
	get_ui_root = function() return nil end,
}

function find_uicomponent() return nil end

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
