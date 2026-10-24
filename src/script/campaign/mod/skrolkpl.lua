------------------------------------------------------------------------------
--
--	Skrolk's Plagues ("Чумы Скролка")
--
--	A human Clan Pestilens gets Nurgle's plague window. The window's 18-slot
--	symptom grid is filled from our catalogue, 18 symptoms at random, and is
--	reshuffled at the start of every Pestilens turn, so the links between
--	symptoms change; within a turn several plagues use one layout. The engine charges nothing for a
--	plague, so this script does: a flat price in food and gold, plus food for
--	every level of the duration / spread / immunity slots, read from the window
--	when the player presses Infect. While the faction cannot pay, Infect is
--	switched off and the window says why. The window's Nurgle wording is
--	replaced for Skrolk.
--
------------------------------------------------------------------------------

-- Filled in by tools/build.py: every symptom component key of the catalogue.
local SYMPTOM_KEYS = {} --@@SYMPTOM_KEYS@@

local PESTILENS = "wh2_main_skv_clan_pestilens"
local GRID_SIZE = 18
local BASE_FOOD, BASE_GOLD = 20, 2500
local FOOD_PER_LEVEL = 2
local FOOD_RESOURCE = "skaven_food"
local FOOD_FACTOR = "skrolkpl_plague_food"
local FREE_RITUALS_BUNDLE = "skrolkpl_free_plague_rituals"
local PLAGUE_BUTTON_OVERRIDE = "disable_nurgle_plagues_button"
local PANEL = "dlc25_nurgle_plagues"
local DIRECT_RITUALS = {
	wh3_main_ritual_nur_plague_target_army = true,
	wh3_main_ritual_nur_plague_target_settlement = true,
}
local SLOTS = { "duration", "spread", "immunity" }
local SAVE_KEY = "skrolkpl"

-- Script log plus skrolkpl_log.txt next to the game executable (the script log is often off).
local function log(msg)
	msg = "Skrolk's Plagues: " .. tostring(msg)
	out(msg)
	if SKROLKPL_NO_FILE_LOG then return end
	local ok, file = pcall(io.open, "skrolkpl_log.txt", "a")
	if ok and file then
		file:write(msg .. "\n")
		file:close()
	end
end

skrolkpl = {
	persistent = { grid = nil },
	pending_levels = nil, -- {duration, spread, immunity} read from the window on Infect
}

------------------------------------------------------------------------------
-- pure helpers
------------------------------------------------------------------------------

-- Slot level from the window's text: "+30%" with step 10, "3 х." with step 1. Clamped to 0..3.
function skrolkpl.level_from_text(text, step)
	local n = tonumber(string.match(tostring(text or ""), "%d+") or "0") or 0
	local level = math.floor(n / step)
	if level < 0 then level = 0 end
	if level > 3 then level = 3 end
	return level
end

function skrolkpl.price(duration, spread, immunity)
	return BASE_FOOD + FOOD_PER_LEVEL * (duration + spread + immunity), BASE_GOLD
end

-- `n` distinct keys in random order (Fisher-Yates over a copy).
function skrolkpl.pick_grid(keys, n)
	local pool = {}
	for i, key in ipairs(keys) do pool[i] = key end
	for i = #pool, 2, -1 do
		local j = cm:random_number(i)
		pool[i], pool[j] = pool[j], pool[i]
	end
	local grid = {}
	for i = 1, math.min(n, #pool) do grid[i] = pool[i] end
	return grid
end

-- nil when the plague's full price can be paid, else the missing resource and the price in it.
function skrolkpl.blocked_reason(food, gold, price_food, price_gold)
	if food < price_food then return "food", price_food end
	if gold < price_gold then return "gold", price_gold end
	return nil
end

-- What can actually be taken: never more than the faction has.
function skrolkpl.take(food_have, gold_have, food, gold)
	return math.max(0, math.min(food, food_have)), math.max(0, math.min(gold, gold_have))
end

------------------------------------------------------------------------------
-- game
------------------------------------------------------------------------------

local function human_pestilens()
	local faction = cm:get_faction(PESTILENS)
	if faction and not faction:is_null_interface() and faction:is_human() then
		return faction
	end
end

local function food_of(faction)
	return faction:pooled_resource_manager():resource(FOOD_RESOURCE):value()
end

-- The window's counter ("... until new symptom locations") is always 1: a new layout next turn.
local function publish_grid()
	common.set_context_value("random_plague_component_list_" .. PESTILENS, skrolkpl.persistent.grid)
	common.set_context_value("random_plague_creation_count_" .. PESTILENS, 1)
end

local function reshuffle()
	skrolkpl.persistent.grid = skrolkpl.pick_grid(SYMPTOM_KEYS, GRID_SIZE)
	publish_grid()
end

local function unlock_components(faction)
	for _, key in ipairs(SYMPTOM_KEYS) do
		cm:set_plague_component_state(faction, key, "UNLOCKED", true)
	end
	for _, slot in ipairs(SLOTS) do
		for level = 0, 3 do
			cm:set_plague_component_state(faction, "wh3_dlc25_nur_mutation_" .. slot .. "_" .. level, "UNLOCKED", true)
		end
	end
end

local function russian()
	return common.get_localised_string("cultures_name_wh_main_emp_empire") == "Империя"
end

local FOOD_ICON = "[[img:icon_skaven_food]][[/img]]"
local GOLD_ICON = "[[img:icon_treasury]][[/img]]"

local TEXT = {
	ru = {
		ours = "Клан Пестиленс", others = "Прочие фракции",
		price = "%d " .. FOOD_ICON .. "  %d " .. GOLD_ICON, level_note = "Каждый уровень слота: +2 " .. FOOD_ICON,
		food = "Нужно %d " .. FOOD_ICON, gold = "Нужно %d " .. GOLD_ICON,
	},
	en = {
		ours = "Clan Pestilens", others = "Other factions",
		price = "%d " .. FOOD_ICON .. "  %d " .. GOLD_ICON, level_note = "Each slot level: +2 " .. FOOD_ICON,
		food = "Needs %d " .. FOOD_ICON, gold = "Needs %d " .. GOLD_ICON,
	},
}

local function text()
	return russian() and TEXT.ru or TEXT.en
end

-- Slot levels as the window shows them now; nil when the window is not open.
local function read_levels()
	local panel = find_uicomponent(core:get_ui_root(), PANEL)
	if not panel then return nil end
	local levels = {}
	for i, slot in ipairs(SLOTS) do
		local value = find_uicomponent(panel, "CcoPlagueMutationUiDataRecord" .. slot, "copy_of_dy_value")
		local step = slot == "spread" and 10 or 1
		levels[i] = value and skrolkpl.level_from_text(value:GetStateText(), step) or 0
	end
	return levels
end

local function set_text(parent, path, value)
	local uic = find_uicomponent(parent, unpack(path))
	if uic then uic:SetStateText(value) end
end

-- Skaven wording, the real price, and the Infect button hidden while blocked.
local function refresh_panel()
	local faction = human_pestilens()
	local panel = faction and find_uicomponent(core:get_ui_root(), PANEL)
	if not panel then return end
	local t = text()
	local summon = find_uicomponent(panel, "button_summon_cultist")
	if summon then summon:SetVisible(false) end
	for _, holder in ipairs({ "holder_plague_effects", "holder_plague_effects_large" }) do
		set_text(panel, { holder, "holder_effects_on_you", "header_effects" }, t.ours)
		set_text(panel, { holder, "holder_effects_on_enemies", "header_effects" }, t.others)
	end
	set_text(panel, { "holder_mutations", "holder_description", "tx_mutation_description" }, t.level_note)
	local cost_icon = find_uicomponent(panel, "holder_mutations", "holder_description", "icon")
	if cost_icon then cost_icon:SetVisible(false) end

	local levels = read_levels() or { 0, 0, 0 }
	local food, gold = skrolkpl.price(levels[1], levels[2], levels[3])
	local reason, number = skrolkpl.blocked_reason(food_of(faction), faction:treasury(), food, gold)
	local cost_text = reason and string.format(t[reason], number) or string.format(t.price, food, gold)
	set_text(panel, { "holder_footer", "holder_total_cost", "dy_cost" }, cost_text)
	-- Infect stays on screen; it is only switched off while the plague cannot be paid for.
	local infect = find_uicomponent(panel, "button_infect_target")
	if infect then
		infect:SetVisible(true)
		pcall(infect.SetDisabled, infect, reason ~= nil)
		if reason then pcall(infect.SetState, infect, "inactive") end
	end
end

local function charge(faction)
	local levels = skrolkpl.pending_levels or read_levels() or { 0, 0, 0 }
	skrolkpl.pending_levels = nil
	local food, gold = skrolkpl.price(levels[1], levels[2], levels[3])
	local take_food, take_gold = skrolkpl.take(food_of(faction), faction:treasury(), food, gold)
	if take_food > 0 then cm:faction_add_pooled_resource(PESTILENS, FOOD_RESOURCE, FOOD_FACTOR, -take_food) end
	if take_gold > 0 then cm:treasury_mod(PESTILENS, -take_gold) end
	log("charged " .. take_food .. " food, " .. take_gold .. " gold (price " .. food .. "/" .. gold .. ")")
end

------------------------------------------------------------------------------
-- PROBES (temporary): learn which symptoms are on cooldown and how grid slots link,
-- to guarantee a usable layout every turn later.
------------------------------------------------------------------------------

local function probe_methods(obj)
	local names = {}
	local ok, mt = pcall(getmetatable, obj)
	if ok and type(mt) == "table" then
		for k in pairs(mt) do names[#names + 1] = tostring(k) end
		if type(mt.__index) == "table" then
			for k in pairs(mt.__index) do names[#names + 1] = "." .. tostring(k) end
		end
	end
	table.sort(names)
	return table.concat(names, " ")
end

local function probe_components(label)
	local faction = human_pestilens()
	if not faction then return end
	local list = faction:plagues():plague_component_list()
	log("probe components " .. label .. ": " .. list:num_items())
	for i = 0, list:num_items() - 1 do
		local c = list:item_at(i)
		if i == 0 then log("probe component methods: " .. probe_methods(c)) end
		local states = {}
		for _, st in ipairs({ "UNLOCKED", "LOCKED", "BLESSED", "COOLDOWN", "ON_COOLDOWN", "USED" }) do
			local ok, v = pcall(c.has_state, c, st)
			if ok and v then states[#states + 1] = st end
		end
		local extra = {}
		for _, m in ipairs({ "cooldown", "remaining_cooldown", "cooldown_remaining", "is_on_cooldown" }) do
			local ok, f = pcall(function() return c[m] end)
			if ok and type(f) == "function" then
				local ok2, v = pcall(f, c)
				extra[#extra + 1] = m .. "=" .. tostring(ok2 and v)
			end
		end
		log("  " .. tostring(c:key()) .. " " .. table.concat(states, ",") .. " " .. table.concat(extra, " "))
	end
end

local function probe_grid()
	local parent = find_uicomponent(core:get_ui_root(), PANEL, "holder_symptoms_grid", "slot_parent")
	if not parent then log("probe grid: no slot_parent") return end
	for i = 0, parent:ChildCount() - 1 do
		local slot = UIComponent(parent:Find(i))
		local ok, cco = pcall(slot.GetContextObjectId, slot, "CcoPlagueComponentUiDataRecord")
		local item = find_uicomponent(slot, "slot_item")
		local ok2, ing = pcall(function() return item:GetContextObjectId("CcoCampaignPlagueIngredient") end)
		log("probe slot " .. i .. " " .. tostring(slot:Id()) .. " record=" .. tostring(ok and cco)
			.. " ingredient=" .. tostring(ok2 and ing))
	end
	local segments = find_uicomponent(core:get_ui_root(), PANEL, "holder_symptoms_grid", "node_segment_list")
	if not segments then log("probe grid: no node_segment_list") return end
	for i = 0, segments:ChildCount() - 1 do
		local group = UIComponent(segments:Find(i))
		local ok, cco = pcall(group.GetContextObjectId, group, "CcoPlagueComponentUiDataRecord")
		local links = {}
		for j = 0, group:ChildCount() - 1 do
			local seg = UIComponent(group:Find(j))
			local ok2, to = pcall(seg.GetContextObjectId, seg, "CcoPlagueComponentUiDataRecord")
			links[#links + 1] = tostring(seg:Id()) .. "->" .. tostring(ok2 and to)
		end
		log("probe segments " .. tostring(group:Id()) .. " from=" .. tostring(ok and cco) .. " : " .. table.concat(links, " "))
	end
end

local function on_plague_ritual(faction)
	charge(faction)
	cm:callback(function() pcall(probe_components, "after plague") end, 0.5) -- PROBE
	refresh_panel() -- switch Infect off at once if the next plague is now unaffordable
end

local function on_turn_start()
	pcall(probe_components, "turn start") -- PROBE
	reshuffle()
	log("grid reshuffled, turn " .. cm:model():turn_number())
	refresh_panel()
end

local function on_first_tick()
	local faction = human_pestilens()
	if not faction then return end
	cm:override_ui(PLAGUE_BUTTON_OVERRIDE, false)
	cm:apply_effect_bundle(FREE_RITUALS_BUNDLE, PESTILENS, 0)
	unlock_components(faction)
	if skrolkpl.persistent.grid then publish_grid() else reshuffle() end
	log("ready, turn " .. cm:model():turn_number())
end

local function listen(name, event, condition, callback)
	core:add_listener("skrolkpl_" .. name, event, condition, function(context)
		local ok, err = pcall(callback, context)
		if not ok then log(name .. " failed: " .. tostring(err)) end
	end, true)
end

listen("plague_ritual", "RitualStartedEvent",
	function(context)
		return DIRECT_RITUALS[context:ritual():ritual_key()] == true and context:performing_faction():name() == PESTILENS
			and context:performing_faction():is_human()
	end,
	function(context) on_plague_ritual(context:performing_faction()) end)

listen("panel_opened", "PanelOpenedCampaign",
	function(context) return context.string == PANEL and human_pestilens() ~= nil end,
	function()
		refresh_panel()
		cm:callback(refresh_panel, 0.1) -- the panel may still be building
		cm:callback(function() pcall(probe_grid) end, 0.3) -- PROBE
	end)

-- PROBE (temporary): what the window tells us about the selected symptoms, to fill the effect
-- columns ourselves later. Logs ids, context object ids and states of the selection slots.
local function probe_uic(label, uic)
	local id = tostring(uic:Id())
	local ok, cco = pcall(uic.GetContextObjectId, uic, "CcoPlagueComponentUiDataRecord")
	local ok2, cco2 = pcall(uic.GetContextObjectId, uic, "CcoCampaignPlagueComponent")
	log("probe " .. label .. " " .. id .. " state=" .. tostring(uic:CurrentState())
		.. " cco=" .. tostring(ok and cco) .. " cco2=" .. tostring(ok2 and cco2))
end

local function probe_selection(clicked)
	if clicked then probe_uic("clicked", clicked) end
	local list = find_uicomponent(core:get_ui_root(), PANEL, "holder_symptoms", "symptoms_list")
	if not list then log("probe: no symptoms_list") return end
	for i = 0, list:ChildCount() - 1 do
		probe_uic("slot" .. i, UIComponent(list:Find(i)))
	end
end

listen("panel_click", "ComponentLClickUp",
	function() return human_pestilens() ~= nil and find_uicomponent(core:get_ui_root(), PANEL) ~= nil end,
	function(context)
		if context.string == "button_infect_target" then
			skrolkpl.pending_levels = read_levels()
		end
		cm:callback(refresh_panel, 0.1) -- after the window applied the click
		local clicked = context.component and UIComponent(context.component)
		cm:callback(function() pcall(probe_selection, clicked) end, 0.15) -- PROBE
	end)

listen("turn_start", "FactionTurnStart",
	function(context) return context:faction():name() == PESTILENS and context:faction():is_human() end,
	function() on_turn_start() end)

cm:add_first_tick_callback(function()
	local ok, err = pcall(on_first_tick)
	if not ok then log("first tick failed: " .. tostring(err)) end
end)

cm:add_saving_game_callback(function(context)
	cm:save_named_value(SAVE_KEY, skrolkpl.persistent, context)
end)

cm:add_loading_game_callback(function(context)
	skrolkpl.persistent = cm:load_named_value(SAVE_KEY, { grid = nil }, context)
end)
