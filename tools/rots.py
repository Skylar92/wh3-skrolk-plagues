"""Strain rot: the random twists a new plague of Skrolk's picks up (spec goal 7).

A new plague rolls 0-3 rots (COUNT_WEIGHTS). The rolled set is the current strain: every army and
settlement infected by Skrolk's plagues carries its bundles until the next plague rolls a new one.
Three kinds; gifts (good for us) weigh as much as rot and reverse (bad for us) together:
- gift: a plus to Pestilens, a minus to the enemy ("Gift of the Horned Rat");
- rot: a minus to Pestilens only ("Rot in our ranks");
- reverse: a minus to Pestilens and a different plus to the enemy ("Reverse strain").
Each rot has army (force scope) and settlement (region/province scope) effects. A target carries one
"strain rot" bundle: the script builds it from TARGET_BUNDLES with the strain's effects summed (custom
bundle), army effects on armies and settlement effects on settlements.
"""
from dataclasses import dataclass

from tools.rows import find, row, table_with

COUNT_WEIGHTS = (50, 30, 15, 5)  # chance in % of 0, 1, 2, 3 rots
# bases of the scripted bundles the strain message shows, one plate per side, effects summed
STRAIN_BUNDLES = {"ours": "skrolkpl_strain_ours", "enemy": "skrolkpl_strain_enemy"}
INCIDENT_STRAIN = "skrolkpl_incident_strain_changed"
INCIDENT_STABLE = "skrolkpl_incident_strain_stable"
INCIDENT_TEMPLATE = "wh3_main_minor_cult_sartosan_vault"  # an incident launched with a scripted payload
INCIDENT_IMAGE = "nur/plague_infected"

F = "force_to_force_own"
R = "region_to_region_own"
P = "province_to_province_own_unseen"
RP = "region_to_province_own_unseen"
_TEMPLATES = {"force": "wh3_dlc25_nur_battle_1_positive", "region": "wh3_dlc25_nur_settlement_1_positive"}
TARGET_BUNDLES = {(side, target): "skrolkpl_strain_%s_%s" % (target, side)
                  for side in ("ours", "enemy") for target in ("force", "region")}


@dataclass(frozen=True)
class Rot:
    id: str
    kind: str          # gift | rot | reverse
    weight: int
    ours: tuple        # ((effect, scope, value), ...) on Pestilens' infected armies and settlements
    enemy: tuple       # the same on everyone else's
    names: dict        # lang -> name


def _rot(rid, kind, ours, enemy=(), weight=None, ru="", en=""):
    if weight is None:
        weight = 8 if kind == "gift" else 4
    return Rot(rid, kind, weight, tuple(ours), tuple(enemy), {"ru": ru, "en": en})


ROTS = [
    # gifts: a plus to us, a minus to them
    _rot("swift_paws", "gift", [("wh_main_effect_force_all_campaign_movement_range", F, 10.0)],
         [("wh_main_effect_force_all_campaign_movement_range", F, -10.0)], ru="Резвые лапы", en="Swift Paws"),
    _rot("rat_fury", "gift", [("wh_main_effect_force_stat_melee_attack", F, 6.0)],
         [("wh_main_effect_force_stat_melee_attack", F, -6.0)], ru="Крысиная ярость", en="Rat Fury"),
    _rot("thick_hide", "gift", [("wh_main_effect_force_stat_armour", F, 10.0)],
         [("wh_main_effect_force_stat_armour", F, -10.0)], ru="Толстая шкура", en="Thick Hide"),
    _rot("venom_spit", "gift", [("wh_main_effect_force_stat_weapon_strength", F, 8.0)],
         [("wh_main_effect_force_stat_weapon_strength", F, -8.0)], ru="Ядовитая слюна", en="Venom Spit"),
    _rot("fecundity", "gift", [("wh3_main_effect_province_growth_plague", P, 15.0)],
         [("wh3_main_effect_province_growth_plague", P, -15.0)], ru="Плодовитость", en="Fecundity"),
    _rot("plague_tithe", "gift", [("wh_main_effect_economy_gdp_mod_all", R, 8.0)],
         [("wh_main_effect_economy_gdp_mod_all", R, -8.0)], ru="Чумная десятина", en="Plague Tithe"),
    _rot("horned_blessing", "gift",
         [("wh_main_effect_force_stat_leadership", F, 10.0), ("wh_main_effect_force_stat_melee_defence", F, 6.0)],
         [("wh_main_effect_force_stat_leadership", F, -10.0), ("wh_main_effect_force_stat_melee_defence", F, -6.0)],
         weight=2, ru="Благословение Рогатой Крысы", en="Blessing of the Horned Rat"),
    # rot in our ranks: a minus to us only
    _rot("brittle_bones", "rot", [("wh_main_effect_force_stat_armour", F, -10.0)], ru="Ломкие кости", en="Brittle Bones"),
    _rot("the_shakes", "rot", [("wh_main_effect_force_stat_melee_defence", F, -5.0)], ru="Трясучка", en="The Shakes"),
    _rot("burrow_panic", "rot", [("wh_main_effect_force_stat_leadership", F, -6.0)], ru="Паника в норах", en="Burrow Panic"),
    _rot("sluggish", "rot", [("wh_main_effect_force_all_campaign_movement_range", F, -10.0)], ru="Тяжёлые лапы", en="Sluggishness"),
    _rot("hunger_blight", "rot", [("wh3_main_effect_province_growth_plague", P, -15.0)], ru="Голодный мор", en="Hunger Blight"),
    _rot("gluttony", "rot", [("wh_main_effect_force_all_campaign_upkeep", F, 10.0)], ru="Прожорливость", en="Gluttony"),
    # reverse strain: a minus to us, a different plus to them
    _rot("limp_and_hardy", "reverse", [("wh_main_effect_force_all_campaign_movement_range", F, -10.0)],
         [("wh_main_effect_force_stat_armour", F, 8.0)], ru="Хромота и закалка", en="Limp and Hardy"),
    _rot("blunt_fangs", "reverse", [("wh_main_effect_force_stat_weapon_strength", F, -8.0)],
         [("wh_main_effect_force_stat_leadership", F, 6.0)], ru="Тупые резцы", en="Blunt Fangs"),
    _rot("feverish_foes", "reverse", [("wh_main_effect_force_stat_melee_attack", F, -5.0)],
         [("wh_main_effect_force_all_campaign_replenishment_rate", F, 10.0)], ru="Лихорадка врага", en="Feverish Foes"),
    _rot("empty_purses", "reverse", [("wh_main_effect_economy_gdp_mod_all", R, -8.0)],
         [("wh_main_effect_public_order_events", RP, 3.0)], ru="Пустые кошели", en="Empty Purses"),
    _rot("barren_nests", "reverse", [("wh3_main_effect_province_growth_plague", P, -10.0)],
         [("wh_main_effect_building_construction_cost_mod_all", R, -10.0)], ru="Пустые гнёзда", en="Barren Nests"),
    _rot("cowed_and_steeled", "reverse", [("wh_main_effect_force_stat_leadership", F, -5.0)],
         [("wh_main_effect_force_stat_melee_defence", F, 4.0)], ru="Робость и стойкость", en="Cowed and Steeled"),
]

KIND_NAMES = {
    "ru": {"gift": "Дар Рогатой Крысы", "rot": "Гниль в своих рядах", "reverse": "Обратный штамм"},
    "en": {"gift": "Gift of the Horned Rat", "rot": "Rot in Our Ranks", "reverse": "Reverse Strain"},
}
TEXTS = {
    "ru": {"rot_title": "Порча штамма",
           "rot_desc_ours": "Порча штамма той чумы Скролка, что здесь засела, всё вместе. Длится столько же, сколько чума.",
           "rot_desc_enemy": "Порча штамма той чумы Скролка, что здесь засела, всё вместе. Длится столько же, сколько чума.",
           "strain_title": "Штамм изменился",
           "strain_desc": "Новая чума Скролка испортилась. Её порча действует на всех, кого заразит эта чума, "
                          "столько же, сколько сама чума. У каждой чумы Скролка своя порча.",
           "stable_title": "Штамм устоял",
           "stable_desc": "Новая чума Скролка не испортилась: порчи нет.",
           "ours_title": "Штамм: Клан Пестиленс",
           "ours_desc": "Эффекты порчи на заражённых армиях и поселениях Клана Пестиленс.",
           "enemy_title": "Штамм: враги",
           "enemy_desc": "Эффекты порчи на заражённых армиях и поселениях всех остальных фракций."},
    "en": {"rot_title": "Strain Rot",
           "rot_desc_ours": "The rot of the strain of Skrolk's plague festering here, summed. Lasts as long as the plague.",
           "rot_desc_enemy": "The rot of the strain of Skrolk's plague festering here, summed. Lasts as long as the plague.",
           "strain_title": "The Strain Has Changed",
           "strain_desc": "Skrolk's new plague has rotted. Its rot holds on everyone this plague infects, for as "
                          "long as the plague itself. Each of Skrolk's plagues carries its own rot.",
           "stable_title": "The Strain Holds",
           "stable_desc": "Skrolk's new plague came out clean: no rot.",
           "ours_title": "Strain: Clan Pestilens",
           "ours_desc": "Rot effects on Clan Pestilens' infected armies and settlements.",
           "enemy_title": "Strain: Enemies",
           "enemy_desc": "Rot effects on every other faction's infected armies and settlements."},
}


def make_rot_tables(table):
    bundles, incidents = table("effect_bundles_tables"), table("incidents_tables")
    new_bundles = [row(bundles, find(bundles, "key", _TEMPLATES[target]), key=key)
                   for (side, target), key in TARGET_BUNDLES.items()]
    faction_template = find(bundles, "key", "wh3_dlc20_payload_eye_of_the_gods_features_nur")
    new_bundles += [row(bundles, faction_template, key=key) for key in STRAIN_BUNDLES.values()]
    template = find(incidents, "key", INCIDENT_TEMPLATE)
    return [table_with(bundles, *new_bundles),
            table_with(incidents, row(incidents, template, key=INCIDENT_STRAIN, ui_image=INCIDENT_IMAGE),
                       row(incidents, template, key=INCIDENT_STABLE, ui_image=INCIDENT_IMAGE))]


def make_rot_loc(lang):
    t = TEXTS[lang]
    out = [("incidents_localised_title_" + INCIDENT_STRAIN, t["strain_title"]),
           ("incidents_localised_description_" + INCIDENT_STRAIN, t["strain_desc"]),
           ("incidents_localised_title_" + INCIDENT_STABLE, t["stable_title"]),
           ("incidents_localised_description_" + INCIDENT_STABLE, t["stable_desc"]),
           ("effect_bundles_localised_title_" + STRAIN_BUNDLES["ours"], t["ours_title"]),
           ("effect_bundles_localised_description_" + STRAIN_BUNDLES["ours"], t["ours_desc"]),
           ("effect_bundles_localised_title_" + STRAIN_BUNDLES["enemy"], t["enemy_title"]),
           ("effect_bundles_localised_description_" + STRAIN_BUNDLES["enemy"], t["enemy_desc"])]
    for (side, target), key in TARGET_BUNDLES.items():
        out += [("effect_bundles_localised_title_" + key, t["rot_title"]),
                ("effect_bundles_localised_description_" + key, t["rot_desc_" + side])]
    return out
