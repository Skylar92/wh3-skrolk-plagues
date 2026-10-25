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

-- Filled in by tools/build.py: every symptom component key of the catalogue, and the one symptom
-- open at the start (plagues must begin with an open symptom; used symptoms open up later).
local SYMPTOM_KEYS = {} --@@SYMPTOM_KEYS@@
local START_SYMPTOM = "" --@@START_SYMPTOM@@
-- Filled in by tools/build.py from tools/rots.py: the strain rot catalogue.
local ROTS = {} --@@ROTS@@
local ROT_BY_ID = {}
for _, rot in ipairs(ROTS) do ROT_BY_ID[rot.id] = rot end
local STRAIN_BUNDLES = { ours = "skrolkpl_strain_ours", enemy = "skrolkpl_strain_enemy" }
local BASE_DURATION = 3 -- plague duration at duration level 0 (Nurgle's slot: 3/4/5/6 turns)
local INCIDENT_STRAIN = "skrolkpl_incident_strain_changed"
local INCIDENT_STABLE = "skrolkpl_incident_strain_stable"

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
local GRID_TRIES = 20

-- Links between the window's 18 grid slots (slot = CcoPlagueComponentUiDataRecord id, 0-based), read
-- from the open window by a probe on 2026-10-25; the engine keeps them in its own "Jade" data. Grid
-- list entry i (1-based) fills slot i - 1.
local SLOT_LINKS = {
	[0] = { 2, 3, 8 }, [1] = { 2, 4, 11 }, [2] = { 5 }, [3] = { 6, 7 }, [4] = { 5, 9 }, [5] = { 6 },
	[6] = { 10 }, [7] = { 8, 14 }, [8] = { 16 }, [9] = { 11, 12 }, [10] = { 12, 13 }, [11] = { 17 },
	[12] = { 17 }, [13] = { 14, 15 }, [14] = { 16 }, [15] = { 16, 17 }, [16] = {}, [17] = {},
}
local NEIGHBOURS = {}
for slot = 0, 17 do NEIGHBOURS[slot] = {} end
for slot, links in pairs(SLOT_LINKS) do
	for _, other in ipairs(links) do
		table.insert(NEIGHBOURS[slot], other)
		table.insert(NEIGHBOURS[other], slot)
	end
end

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
	-- unlocked: {[symptom key] = true}; strain: rot ids of the current strain;
	-- strain_turns: the plague's duration, which its rot shares;
	-- infected: what Skrolk's plagues hold now, {forces = {[cqi] = ours}, regions = {[key] = ours}}
	persistent = { grid = nil, unlocked = nil, strain = {}, strain_turns = BASE_DURATION,
	               infected = { forces = {}, regions = {} } },
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

function skrolkpl.neighbours(slot)
	return NEIGHBOURS[slot]
end

local function linked(a, b)
	for _, n in ipairs(NEIGHBOURS[a]) do
		if n == b then return true end
	end
	return false
end

-- Can a plague be made on this grid? As the window allows (dlc25plagues.cco, IsIngredientSelectable):
-- the first symptom open and usable, each next one usable and linked to one already picked.
function skrolkpl.has_plague_path(grid, open, usable)
	local function ok(slot) return grid[slot + 1] ~= nil and usable[grid[slot + 1]] end
	for a = 0, GRID_SIZE - 1 do
		if ok(a) and open[grid[a + 1]] then
			for _, b in ipairs(NEIGHBOURS[a]) do
				if ok(b) then
					for c = 0, GRID_SIZE - 1 do
						if c ~= a and c ~= b and ok(c) and (linked(a, c) or linked(b, c)) then
							return true
						end
					end
				end
			end
		end
	end
	return false
end

local function shuffled(list)
	local out = {}
	for i, v in ipairs(list) do out[i] = v end
	for i = #out, 2, -1 do
		local j = cm:random_number(i)
		out[i], out[j] = out[j], out[i]
	end
	return out
end

-- A random grid on which a plague can be made: random tries first, then built around a chain of
-- three linked slots (open usable symptom first). Plain random when no chain is possible at all.
function skrolkpl.build_grid(keys, open, usable)
	for _ = 1, GRID_TRIES do
		local grid = skrolkpl.pick_grid(keys, GRID_SIZE)
		if skrolkpl.has_plague_path(grid, open, usable) then return grid end
	end
	local starts, others = {}, {}
	for _, key in ipairs(shuffled(keys)) do
		if usable[key] and open[key] and #starts == 0 then
			starts[1] = key
		elseif usable[key] then
			others[#others + 1] = key
		end
	end
	if #starts == 0 or #others < 2 then return skrolkpl.pick_grid(keys, GRID_SIZE) end
	local a = cm:random_number(GRID_SIZE) - 1
	local b = NEIGHBOURS[a][cm:random_number(#NEIGHBOURS[a])]
	local around = {}
	for _, n in ipairs(NEIGHBOURS[a]) do if n ~= b then around[#around + 1] = n end end
	for _, n in ipairs(NEIGHBOURS[b]) do if n ~= a then around[#around + 1] = n end end
	local c = around[cm:random_number(#around)]
	local grid, placed = {}, { [starts[1]] = true, [others[1]] = true, [others[2]] = true }
	grid[a + 1], grid[b + 1], grid[c + 1] = starts[1], others[1], others[2]
	local rest = {}
	for _, key in ipairs(shuffled(keys)) do
		if not placed[key] then rest[#rest + 1] = key end
	end
	for slot = 1, GRID_SIZE do
		if grid[slot] == nil then grid[slot] = table.remove(rest, 1) end
	end
	return grid
end

-- The rots a new plague picks up: 0-3 (50/30/15/5 %), distinct, drawn by weight.
function skrolkpl.roll_strain()
	local r = cm:random_number(100)
	local count = (r <= 50 and 0) or (r <= 80 and 1) or (r <= 95 and 2) or 3
	local pool, strain = {}, {}
	for i, rot in ipairs(ROTS) do pool[i] = rot end
	for _ = 1, count do
		local total = 0
		for _, rot in ipairs(pool) do total = total + rot.weight end
		local pick = cm:random_number(total)
		for i, rot in ipairs(pool) do
			pick = pick - rot.weight
			if pick <= 0 then
				strain[#strain + 1] = rot.id
				table.remove(pool, i)
				break
			end
		end
	end
	return strain
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

-- {[key] = true} of our symptoms in the given state, as the engine reports it.
local function symptoms_in_state(faction, state)
	local out, list = {}, faction:plagues():plague_component_list()
	for i = 0, list:num_items() - 1 do
		local c = list:item_at(i)
		if string.sub(c:key(), 1, 13) == "skrolkpl_sym_" and c:has_state(state) then out[c:key()] = true end
	end
	return out
end

local function open_symptom(faction, key)
	skrolkpl.persistent.unlocked[key] = true
	cm:set_plague_component_state(faction, key, "UNLOCKED", true)
end

-- Every symptom open or closed as `unlocked` says; parameter slots always open.
local function apply_unlocked(faction)
	for _, key in ipairs(SYMPTOM_KEYS) do
		cm:set_plague_component_state(faction, key, "UNLOCKED", skrolkpl.persistent.unlocked[key] == true)
	end
	for _, slot in ipairs(SLOTS) do
		for level = 0, 3 do
			cm:set_plague_component_state(faction, "wh3_dlc25_nur_mutation_" .. slot .. "_" .. level, "UNLOCKED", true)
		end
	end
end

-- One blessed symptom per layout, among the usable ones on the grid.
local function bless(faction, usable)
	local candidates = {}
	for _, key in ipairs(SYMPTOM_KEYS) do
		cm:set_plague_component_state(faction, key, "BLESSED", false)
	end
	for _, key in ipairs(skrolkpl.persistent.grid) do
		if usable[key] then candidates[#candidates + 1] = key end
	end
	if #candidates > 0 then
		cm:set_plague_component_state(faction, candidates[cm:random_number(#candidates)], "BLESSED", true)
	end
end

-- New layout: open one more symptom if every open one rests, then a grid that can make a plague.
local function reshuffle(faction)
	local resting = symptoms_in_state(faction, "COOLDOWN")
	local usable, open_free = {}, false
	for _, key in ipairs(SYMPTOM_KEYS) do
		if not resting[key] then
			usable[key] = true
			if skrolkpl.persistent.unlocked[key] then open_free = true end
		end
	end
	if not open_free then
		local free = {}
		for key in pairs(usable) do free[#free + 1] = key end
		table.sort(free)
		if #free > 0 then
			local key = free[cm:random_number(#free)]
			open_symptom(faction, key)
			log("opened " .. key .. ": every open symptom was resting")
		end
	end
	skrolkpl.persistent.grid = skrolkpl.build_grid(SYMPTOM_KEYS, skrolkpl.persistent.unlocked, usable)
	publish_grid()
	bless(faction, usable)
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

-- Self-check (log only): the window should show grid entry i in slot i - 1, as SLOT_LINKS assumes.
local function check_slot_mapping()
	local parent = find_uicomponent(core:get_ui_root(), PANEL, "holder_symptoms_grid", "slot_parent")
	if not parent then return end
	local bad = 0
	for i = 0, parent:ChildCount() - 1 do
		local slot = UIComponent(parent:Find(i))
		local ok, record = pcall(slot.GetContextObjectId, slot, "CcoPlagueComponentUiDataRecord")
		local item = find_uicomponent(slot, "slot_item")
		local ok2, ingredient = pcall(function() return item:GetContextObjectId("CcoCampaignPlagueIngredient") end)
		local n = ok and tonumber(record)
		if n and ok2 and ingredient then
			local expected = skrolkpl.persistent.grid[n + 1]
			if not expected or string.sub(tostring(ingredient), 1, #expected) ~= expected then
				bad = bad + 1
				log("slot " .. n .. " shows " .. tostring(ingredient) .. ", expected " .. tostring(expected))
			end
		end
	end
	log("slot mapping check: " .. (bad == 0 and "ok" or (bad .. " mismatches")))
end

-- After a plague the open symptoms may all be resting: open one more on this turn's grid, placed
-- so a plague can start from it (two free linked neighbours). The grid itself stays for the turn.
local function keep_a_plague_possible(faction)
	local resting = symptoms_in_state(faction, "COOLDOWN")
	local usable = {}
	for _, key in ipairs(SYMPTOM_KEYS) do
		if not resting[key] then usable[key] = true end
	end
	local open = skrolkpl.persistent.unlocked
	local grid = skrolkpl.persistent.grid
	if skrolkpl.has_plague_path(grid, open, usable) then return end
	local candidates = {}
	for _, key in ipairs(grid) do
		if usable[key] and not open[key] then candidates[#candidates + 1] = key end
	end
	for _, key in ipairs(shuffled(candidates)) do
		local trial = { [key] = true }
		if skrolkpl.has_plague_path(grid, trial, usable) then
			open_symptom(faction, key)
			log("opened " .. key .. ": no plague could start on this turn's grid")
			return
		end
	end
end

------------------------------------------------------------------------------
-- strain rot on the targets of Skrolk's plagues
------------------------------------------------------------------------------

local function strain_bundles(strain, ours, target)
	local out = {}
	for _, id in ipairs(strain) do
		local rot = ROT_BY_ID[id]
		local key = rot and rot[(ours and "ours_" or "enemy_") .. target]
		if key then out[#out + 1] = key end
	end
	return out
end

local function set_force_rot(cqi, ours, strain, on)
	for _, key in ipairs(strain_bundles(strain, ours, "force")) do
		if on then cm:apply_effect_bundle_to_force(key, tonumber(cqi), skrolkpl.persistent.strain_turns)
		else cm:remove_effect_bundle_from_force(key, tonumber(cqi)) end
	end
end

local function set_region_rot(region_key, ours, strain, on)
	for _, key in ipairs(strain_bundles(strain, ours, "region")) do
		if on then cm:apply_effect_bundle_to_region(key, region_key, skrolkpl.persistent.strain_turns)
		else cm:remove_effect_bundle_from_region(key, region_key) end
	end
end

-- Swap every infected target from the old strain to the new one.
local function restrain(old, new)
	for cqi, ours in pairs(skrolkpl.persistent.infected.forces) do
		set_force_rot(cqi, ours, old, false)
		set_force_rot(cqi, ours, new, true)
	end
	for key, ours in pairs(skrolkpl.persistent.infected.regions) do
		set_region_rot(key, ours, old, false)
		set_region_rot(key, ours, new, true)
	end
end

-- An event message: what the strain does to Pestilens and to the enemy, or "the strain holds".
local function announce(faction, strain)
	if #strain == 0 then
		cm:trigger_incident(PESTILENS, INCIDENT_STABLE, true)
		return
	end
	local payload = cm:create_payload()
	for _, side in ipairs({ "ours", "enemy" }) do
		local shown = cm:create_new_custom_effect_bundle(STRAIN_BUNDLES[side])
		local any = false
		for _, id in ipairs(strain) do
			for _, e in ipairs(ROT_BY_ID[id]["show_" .. side]) do
				shown:add_effect(e[1], e[2], e[3])
				any = true
			end
		end
		if any then
			shown:set_duration(skrolkpl.persistent.strain_turns)
			payload:effect_bundle_to_faction(shown)
		end
	end
	local incident = cm:create_incident_builder(INCIDENT_STRAIN)
	incident:set_payload(payload)
	cm:launch_custom_incident_from_builder(incident, faction)
end

local function on_force_infection(context)
	local force = context:target_force()
	local cqi = tostring(force:command_queue_index())
	local forces = skrolkpl.persistent.infected.forces
	local strain = skrolkpl.persistent.strain
	if forces[cqi] ~= nil then -- drop the old rot first: plague ended, replaced, or re-applied
		set_force_rot(cqi, forces[cqi], strain, false)
		forces[cqi] = nil
	end
	if context:plague():creator_faction():name() ~= PESTILENS or context:is_removed() then return end
	local ours = force:faction():name() == PESTILENS
	forces[cqi] = ours
	set_force_rot(cqi, ours, strain, true)
end

-- RegionInfectionEvent has no region() (in game: "attempt to call method 'region'"); try the others.
local function region_of(context)
	for _, method in ipairs({ "target_region", "region", "settlement" }) do
		local ok, value = pcall(function() return context[method](context) end)
		if ok and value then
			if method == "settlement" then return value:region() end
			return value
		end
	end
	error("RegionInfectionEvent: no region accessor")
end

local function on_region_infection(context)
	local region = region_of(context)
	local key = region:name()
	local regions = skrolkpl.persistent.infected.regions
	local strain = skrolkpl.persistent.strain
	if regions[key] ~= nil then
		set_region_rot(key, regions[key], strain, false)
		regions[key] = nil
	end
	if context:plague():creator_faction():name() ~= PESTILENS then return end
	local ours = region:owning_faction():name() == PESTILENS
	regions[key] = ours
	set_region_rot(key, ours, strain, true)
end

local function on_region_plague_state(context)
	local key = context:region():name()
	local regions = skrolkpl.persistent.infected.regions
	if regions[key] ~= nil and not context:is_infected() then
		set_region_rot(key, regions[key], skrolkpl.persistent.strain, false)
		regions[key] = nil
	end
end

local function on_plague_ritual(faction)
	local levels = skrolkpl.pending_levels or read_levels() or { 0, 0, 0 }
	charge(faction)
	skrolkpl.persistent.strain_turns = BASE_DURATION + levels[1]
	local old = skrolkpl.persistent.strain
	skrolkpl.persistent.strain = skrolkpl.roll_strain()
	restrain(old, skrolkpl.persistent.strain)
	log("strain: " .. (#skrolkpl.persistent.strain > 0 and table.concat(skrolkpl.persistent.strain, ", ") or "clean"))
	announce(faction, skrolkpl.persistent.strain)
	-- the engine marks the plague's symptoms as resting after the infection events
	cm:callback(function()
		local resting = symptoms_in_state(faction, "COOLDOWN")
		for _, key in ipairs(SYMPTOM_KEYS) do
			if resting[key] and not skrolkpl.persistent.unlocked[key] then
				open_symptom(faction, key)
				log("opened " .. key .. ": used in a plague")
			end
		end
		keep_a_plague_possible(faction)
		refresh_panel()
	end, 0.5)
	refresh_panel() -- switch Infect off at once if the next plague is now unaffordable
end

local function on_turn_start(faction)
	reshuffle(faction)
	log("grid reshuffled, turn " .. cm:model():turn_number())
	refresh_panel()
end

local function on_first_tick()
	local faction = human_pestilens()
	if not faction then return end
	cm:override_ui(PLAGUE_BUTTON_OVERRIDE, false)
	cm:apply_effect_bundle(FREE_RITUALS_BUNDLE, PESTILENS, 0)
	if not skrolkpl.persistent.unlocked then -- new campaign, or a save from before the start symptom
		skrolkpl.persistent.unlocked = { [START_SYMPTOM] = true }
		skrolkpl.persistent.grid = nil
	end
	apply_unlocked(faction)
	if skrolkpl.persistent.grid then publish_grid() else reshuffle(faction) end
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
		cm:callback(function() pcall(check_slot_mapping) end, 0.3)
	end)

listen("panel_click", "ComponentLClickUp",
	function() return human_pestilens() ~= nil and find_uicomponent(core:get_ui_root(), PANEL) ~= nil end,
	function(context)
		if context.string == "button_infect_target" then
			skrolkpl.pending_levels = read_levels()
		end
		cm:callback(refresh_panel, 0.1) -- after the window applied the click
	end)

listen("force_infection", "MilitaryForceInfectionEvent",
	function() return human_pestilens() ~= nil end,
	on_force_infection)

listen("region_infection", "RegionInfectionEvent",
	function() return human_pestilens() ~= nil end,
	on_region_infection)

listen("region_plague_state", "RegionPlagueStateChanged",
	function() return human_pestilens() ~= nil end,
	on_region_plague_state)

listen("turn_start", "FactionTurnStart",
	function(context) return context:faction():name() == PESTILENS and context:faction():is_human() end,
	function(context) on_turn_start(context:faction()) end)

cm:add_first_tick_callback(function()
	local ok, err = pcall(on_first_tick)
	if not ok then log("first tick failed: " .. tostring(err)) end
end)

cm:add_saving_game_callback(function(context)
	cm:save_named_value(SAVE_KEY, skrolkpl.persistent, context)
end)

cm:add_loading_game_callback(function(context)
	skrolkpl.persistent = cm:load_named_value(SAVE_KEY, { grid = nil, unlocked = nil }, context)
	skrolkpl.persistent.strain = skrolkpl.persistent.strain or {}
	skrolkpl.persistent.strain_turns = skrolkpl.persistent.strain_turns or BASE_DURATION
	skrolkpl.persistent.infected = skrolkpl.persistent.infected or { forces = {}, regions = {} }
end)
