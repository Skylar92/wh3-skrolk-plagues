------------------------------------------------------------------------------
--
--	Skrolk's Plagues: SPIKE (throwaway diagnostics, plan Task 2)
--
--	Gives a human Clan Pestilens the Nurgle plague button, unlocks the spike
--	symptoms and Nurgle's parameter slots, and logs what the game tells us:
--	plague rituals, infections, the faction's plague components and the UI
--	paths the player clicks. Everything is written both to the script log
--	(out) and to skrolkpl_spike_log.txt next to the game executable.
--
------------------------------------------------------------------------------

local PESTILENS = "wh2_main_skv_clan_pestilens"
local PLAGUE_BUTTON_OVERRIDE = "disable_nurgle_plagues_button"
local SYMPTOMS = { "skrolkpl_spike_sym_battle_1", "skrolkpl_spike_sym_force_4", "skrolkpl_spike_sym_settlement_1" }
local LOCK_PROBE = "skrolkpl_spike_sym_settlement_1" -- G6: locked while the panel is open
local PARAMS = { "duration", "immunity", "spread" }

local function log(msg)
	msg = "skrolkpl: " .. tostring(msg)
	out(msg)
	local ok, file = pcall(io.open, "skrolkpl_spike_log.txt", "a")
	if ok and file then
		file:write(msg .. "\n")
		file:close()
	end
end

-- obj:method() or "<err: ...>" without ever throwing
local function try(obj, method, ...)
	if obj == nil then return "<nil>" end
	local ok, f = pcall(function() return obj[method] end)
	if not ok or type(f) ~= "function" then return "<no " .. method .. ">" end
	local ok2, value = pcall(f, obj, ...)
	if not ok2 then return "<err " .. method .. ": " .. tostring(value) .. ">" end
	return value
end

local function name_of(obj)
	local n = try(obj, "name")
	if type(n) ~= "string" then n = try(obj, "key") end
	return tostring(n)
end

local function is_human_pestilens(faction)
	return faction and not faction:is_null_interface() and faction:name() == PESTILENS and faction:is_human()
end

local function pestilens()
	local f = cm:get_faction(PESTILENS)
	if is_human_pestilens(f) then return f end
end

local function dump_components(faction)
	local plagues = try(faction, "plagues")
	local list = try(plagues, "plague_component_list")
	local n = try(list, "num_items")
	log("components: " .. tostring(n))
	if type(n) ~= "number" then return end
	for i = 0, n - 1 do
		local c = list:item_at(i)
		log("  " .. tostring(try(c, "key")) .. " unlocked=" .. tostring(try(c, "has_state", "UNLOCKED"))
			.. " locked=" .. tostring(try(c, "has_state", "LOCKED")))
	end
end

local function unlock_all(faction)
	for _, key in ipairs(SYMPTOMS) do
		cm:set_plague_component_state(faction, key, "UNLOCKED", true)
	end
	for _, p in ipairs(PARAMS) do
		for level = 0, 3 do
			cm:set_plague_component_state(faction, "wh3_dlc25_nur_mutation_" .. p .. "_" .. level, "UNLOCKED", true)
		end
	end
end

local function uic_path(uic)
	local parts = {}
	while uic do
		local id = try(uic, "Id")
		table.insert(parts, 1, tostring(id) .. "[" .. tostring(try(uic, "CurrentState")) .. "]")
		local parent = try(uic, "Parent")
		if type(parent) ~= "userdata" then break end
		uic = UIComponent(parent)
	end
	return table.concat(parts, " > ")
end

local function dump_tree(uic, depth, max_depth)
	if depth > max_depth then return end
	local n = try(uic, "ChildCount")
	if type(n) ~= "number" then return end
	for i = 0, n - 1 do
		local child = UIComponent(uic:Find(i))
		log(string.rep("  ", depth) .. tostring(try(child, "Id")) .. " [" .. tostring(try(child, "CurrentState"))
			.. "] visible=" .. tostring(try(child, "Visible")))
		dump_tree(child, depth + 1, max_depth)
	end
end

local function on_first_tick()
	local faction = pestilens()
	if not faction then return end
	log("first tick, turn " .. cm:model():turn_number())
	cm:override_ui(PLAGUE_BUTTON_OVERRIDE, false)
	unlock_all(faction)
	dump_components(faction)
end

local function add(name, event, cb)
	core:add_listener("skrolkpl_spike_" .. name, event, true, function(context)
		local ok, err = pcall(cb, context)
		if not ok then log(name .. " failed: " .. tostring(err)) end
	end, true)
end

add("ritual_started", "RitualStartedEvent", function(context)
	local ritual = try(context, "ritual")
	log("RitualStartedEvent ritual=" .. tostring(try(ritual, "ritual_key")) .. " faction="
		.. name_of(try(context, "performing_faction")) .. " plague=" .. name_of(try(context, "plague")))
end)

add("ritual_completed", "RitualCompletedEvent", function(context)
	local ritual = try(context, "ritual")
	log("RitualCompletedEvent ritual=" .. tostring(try(ritual, "ritual_key")) .. " faction="
		.. name_of(try(context, "performing_faction")) .. " plague=" .. name_of(try(context, "plague")))
end)

add("force_infected", "MilitaryForceInfectionEvent", function(context)
	local plague = try(context, "plague")
	log("MilitaryForceInfectionEvent plague=" .. name_of(plague) .. " creator=" .. name_of(try(plague, "creator_faction"))
		.. " force_faction=" .. name_of(try(try(context, "target_force"), "faction")))
end)

add("region_infected", "RegionInfectionEvent", function(context)
	local plague = try(context, "plague")
	log("RegionInfectionEvent plague=" .. name_of(plague) .. " creator=" .. name_of(try(plague, "creator_faction"))
		.. " region=" .. name_of(try(context, "region")))
end)

add("region_state", "RegionPlagueStateChanged", function(context)
	log("RegionPlagueStateChanged region=" .. name_of(try(context, "region")) .. " infected="
		.. tostring(try(context, "is_infected")))
end)

add("agent_plague", "AgentPlagueDataCreatedEvent", function(context)
	log("AgentPlagueDataCreatedEvent plague=" .. name_of(try(context, "plague")))
end)

add("turn_start", "FactionTurnStart", function(context)
	local faction = context:faction()
	if not is_human_pestilens(faction) then return end
	log("FactionTurnStart turn " .. cm:model():turn_number())
	dump_components(faction)
end)

add("panel_opened", "PanelOpenedCampaign", function(context)
	log("PanelOpenedCampaign " .. tostring(context.string))
	local faction = pestilens()
	if not faction or not string.find(tostring(context.string), "plague") then return end
	cm:set_plague_component_state(faction, LOCK_PROBE, "LOCKED", true) -- G6
	log("G6: locked " .. LOCK_PROBE .. " while the panel is open")
	cm:callback(function()
		local panel = find_uicomponent(core:get_ui_root(), context.string)
		if panel then
			log("tree of " .. context.string .. ":")
			dump_tree(panel, 1, 8)
		end
	end, 0.5)
end)

add("panel_closed", "PanelClosedCampaign", function(context)
	local faction = pestilens()
	if faction and string.find(tostring(context.string), "plague") then
		cm:set_plague_component_state(faction, LOCK_PROBE, "UNLOCKED", true)
	end
end)

add("click", "ComponentLClickUp", function(context)
	if not pestilens() then return end
	log("click " .. uic_path(UIComponent(context.component)))
end)

cm:add_first_tick_callback(function()
	local ok, err = pcall(on_first_tick)
	if not ok then log("first tick failed: " .. tostring(err)) end
end)
