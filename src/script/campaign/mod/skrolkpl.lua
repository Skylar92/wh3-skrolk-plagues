------------------------------------------------------------------------------
--
--	Skrolk's Plagues ("Чумы Скролка")
--
--	A human Clan Pestilens gets Nurgle's plague window. The window's 18-slot
--	symptom grid is filled from our catalogue, 18 symptoms at random, and is
--	reshuffled after every plague, so the links between symptoms change. The
--	engine charges nothing for a plague, so this script does: a flat price in
--	food and gold, plus food for every level of the duration / spread /
--	immunity slots, read from the window when the player presses Infect. There
--	is no cooldown: the price is the limit. While the faction cannot pay, the
--	Infect button is hidden and the window says why. The window's Nurgle
--	wording is replaced for Skrolk.
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

local TEXT = {
	ru = {
		ours = "Клан Пестиленс", others = "Прочие фракции",
		price = "%d еды, %d зол.", level_note = "Каждый уровень слота: +2 еды",
		food = "Нужно %d еды", gold = "Нужно %d золота",
	},
	en = {
		ours = "Clan Pestilens", others = "Other factions",
		price = "%d food, %d gold", level_note = "Each slot level: +2 food",
		food = "Needs %d food", gold = "Needs %d gold",
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

-- The window reads the symptom grid only when it opens, so show a new grid by reopening it:
-- its own close button, then the HUD button (clicking the HUD button while open did nothing).
local function reopen_panel()
	local panel = find_uicomponent(core:get_ui_root(), PANEL)
	local close = panel and find_uicomponent(panel, "holder_footer", "button_close_holder", "button_close")
	log("reopen: window " .. tostring(panel ~= nil) .. ", close button " .. tostring(close ~= nil))
	if not close then return end
	close:SimulateLClick()
	cm:callback(function()
		local open = find_uicomponent(core:get_ui_root(), "hud_campaign", "faction_buttons_docker",
			"button_group_management", "button_nurgle_plagues")
		log("reopen: plague button " .. tostring(open ~= nil))
		if open then open:SimulateLClick() end
	end, 0.2)
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

local function on_plague_ritual(faction)
	charge(faction)
	refresh_panel() -- switch Infect off at once if the next plague is now unaffordable
	-- after the infection events this ritual triggers, as nurgle_plagues does
	cm:callback(function()
		reshuffle()
		reopen_panel()
	end, 0.5)
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
	end)

listen("panel_click", "ComponentLClickUp",
	function() return human_pestilens() ~= nil and find_uicomponent(core:get_ui_root(), PANEL) ~= nil end,
	function(context)
		if context.string == "button_infect_target" then
			skrolkpl.pending_levels = read_levels()
		end
		cm:callback(refresh_panel, 0.1) -- after the window applied the click
	end)

listen("turn_start", "FactionTurnStart",
	function(context) return context:faction():name() == PESTILENS and context:faction():is_human() end,
	function() refresh_panel() end)

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
