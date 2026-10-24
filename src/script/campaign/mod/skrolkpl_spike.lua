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
-- The plague window's 18-slot symptom grid is filled from this list (via a context value, as
-- nurgle_plagues does); reshuffling it changes which symptoms are linked.
local SYMPTOMS = {
	"skrolkpl_spike_sym_battle_2", "skrolkpl_spike_sym_settlement_4", "skrolkpl_spike_sym_force_2",
	"skrolkpl_spike_sym_battle_7", "skrolkpl_spike_sym_battle_6", "skrolkpl_spike_sym_battle_1",
	"skrolkpl_spike_sym_settlement_5", "skrolkpl_spike_sym_force_3", "skrolkpl_spike_sym_battle_4",
	"skrolkpl_spike_sym_force_1", "skrolkpl_spike_sym_force_6", "skrolkpl_spike_sym_settlement_1",
	"skrolkpl_spike_sym_settlement_2", "skrolkpl_spike_sym_battle_5", "skrolkpl_spike_sym_force_5",
	"skrolkpl_spike_sym_settlement_3", "skrolkpl_spike_sym_force_4", "skrolkpl_spike_sym_battle_3",
}
local SPIKE_RITUAL_PREFIX = "skrolkpl_spike_ritual_"
local NURGLE_RITUAL_PREFIX = "wh3_main_ritual_nur_plague_"
local FREE_RITUALS_BUNDLE = "skrolkpl_spike_free_rituals"
local grid = nil -- current symptom order; nil until first placed
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

-- Names of the methods a script interface offers (CA interfaces keep them in the metatable's __index).
local function methods(obj)
	if obj == nil then return "<nil>" end
	local ok, mt = pcall(getmetatable, obj)
	if not ok or type(mt) ~= "table" then return "<no metatable: " .. type(obj) .. ">" end
	local index = mt.__index
	if type(index) ~= "table" then return "<__index is " .. type(index) .. ">" end
	local names = {}
	for name in pairs(index) do names[#names + 1] = tostring(name) end
	table.sort(names)
	return table.concat(names, " ")
end

local function dump_interface(label, obj)
	log("  methods of " .. label .. ": " .. methods(obj))
end

-- Text of every visible descendant with text, depth-first (to read the plague panel's current values).
local function dump_texts(uic, prefix, depth)
	if depth > 12 then return end
	local n = try(uic, "ChildCount")
	if type(n) ~= "number" then return end
	for i = 0, n - 1 do
		local child = UIComponent(uic:Find(i))
		local id = tostring(try(child, "Id"))
		local text = try(child, "GetStateText")
		if type(text) == "string" and text ~= "" and try(child, "Visible") == true then
			log("  text " .. prefix .. id .. " = " .. text)
		end
		dump_texts(child, prefix .. id .. ">", depth + 1)
	end
end

local function log_purse(faction, label)
	local food = try(try(try(faction, "pooled_resource_manager"), "resource", "skaven_food"), "value")
	log(label .. ": treasury=" .. tostring(try(faction, "treasury")) .. " skaven_food=" .. tostring(food))
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

local function publish_grid()
	common.set_context_value("random_plague_component_list_" .. PESTILENS, grid)
	common.set_context_value("random_plague_creation_count_" .. PESTILENS, 1)
	log("grid: " .. table.concat(grid, ", "))
end

local function shuffle_grid()
	grid = {}
	for i, key in ipairs(SYMPTOMS) do grid[i] = key end
	for i = #grid, 2, -1 do
		local j = cm:random_number(i)
		grid[i], grid[j] = grid[j], grid[i]
	end
	publish_grid()
end

local function on_first_tick()
	local faction = pestilens()
	if not faction then return end
	log("first tick, turn " .. cm:model():turn_number())
	cm:override_ui(PLAGUE_BUTTON_OVERRIDE, false)
	cm:apply_effect_bundle(FREE_RITUALS_BUNDLE, PESTILENS, 0) -- zeroes Nurgle rituals' infection cost
	unlock_all(faction)
	if grid then publish_grid() else shuffle_grid() end
	dump_components(faction)
end

cm:add_saving_game_callback(function(context)
	cm:save_named_value("skrolkpl_spike_grid", grid, context)
end)

cm:add_loading_game_callback(function(context)
	grid = cm:load_named_value("skrolkpl_spike_grid", nil, context)
end)

local function add(name, event, cb)
	core:add_listener("skrolkpl_spike_" .. name, event, true, function(context)
		local ok, err = pcall(cb, context)
		if not ok then log(name .. " failed: " .. tostring(err)) end
	end, true)
end

add("ritual_started", "RitualStartedEvent", function(context)
	local ritual = try(context, "ritual")
	local key = tostring(try(ritual, "ritual_key"))
	local faction = try(context, "performing_faction")
	log("RitualStartedEvent ritual=" .. key .. " faction=" .. name_of(faction) .. " plague=" .. name_of(try(context, "plague")))
	local ours = string.sub(key, 1, #SPIKE_RITUAL_PREFIX) == SPIKE_RITUAL_PREFIX
		or string.sub(key, 1, #NURGLE_RITUAL_PREFIX) == NURGLE_RITUAL_PREFIX
	if ours and type(faction) ~= "string" and is_human_pestilens(faction) then
		log_purse(faction, "  purse at start")
		cm:callback(function() log_purse(cm:get_faction(PESTILENS), "  purse 1s later") end, 1)
		-- after the infection events, like nurgle_plagues does
		cm:callback(function() shuffle_grid() end, 0.5)
	end
end)

add("ritual_completed", "RitualCompletedEvent", function(context)
	local ritual = try(context, "ritual")
	log("RitualCompletedEvent ritual=" .. tostring(try(ritual, "ritual_key")) .. " faction="
		.. name_of(try(context, "performing_faction")) .. " plague=" .. name_of(try(context, "plague")))
	if name_of(try(context, "performing_faction")) == PESTILENS then
		dump_interface("ritual context", context)
		dump_interface("ritual", try(context, "ritual"))
	end
end)

add("force_infected", "MilitaryForceInfectionEvent", function(context)
	local plague = try(context, "plague")
	log("MilitaryForceInfectionEvent plague=" .. name_of(plague) .. " creator=" .. name_of(try(plague, "creator_faction"))
		.. " force_faction=" .. name_of(try(try(context, "target_force"), "faction")))
	if name_of(try(plague, "creator_faction")) == PESTILENS then
		dump_interface("force infection context", context)
		dump_interface("plague", plague)
	end
end)

add("region_infected", "RegionInfectionEvent", function(context)
	local plague = try(context, "plague")
	log("RegionInfectionEvent plague=" .. name_of(plague) .. " creator=" .. name_of(try(plague, "creator_faction"))
		.. " region=" .. name_of(try(context, "region")))
	if name_of(try(plague, "creator_faction")) == PESTILENS then
		dump_interface("region infection context", context)
		dump_interface("plague", plague)
	end
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

-- The cultist that Nurgle's agent ritual spawns crashes Skaven UI (run 5): hide its button.
local function hide_summon_button(panel_name)
	local panel = find_uicomponent(core:get_ui_root(), panel_name)
	local button = panel and find_uicomponent(panel, "button_summon_cultist")
	if button then
		button:SetVisible(false)
	end
	log("summon button hidden: " .. tostring(button ~= nil and button ~= false))
end

add("panel_opened", "PanelOpenedCampaign", function(context)
	log("PanelOpenedCampaign " .. tostring(context.string))
	local faction = pestilens()
	if not faction or not string.find(tostring(context.string), "plague") then return end
	hide_summon_button(context.string)
	cm:callback(function() hide_summon_button(context.string) end, 0.1) -- the panel may build late
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
	if context.string == "button_infect_target" or context.string == "button_summon_cultist" then
		log_purse(pestilens(), "  purse before click")
		local panel = find_uicomponent(core:get_ui_root(), "dlc25_nurgle_plagues")
		if panel then
			local main = find_uicomponent(panel, "panel_main")
			dump_texts(main or panel, "", 0)
		end
	end
end)

cm:add_first_tick_callback(function()
	local ok, err = pcall(on_first_tick)
	if not ok then log("first tick failed: " .. tostring(err)) end
end)
