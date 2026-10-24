"""Skrolk's symptom catalogue and its db rows.

Every symptom is a plague component of type SYMPTOM in our component set. Its effects go
component setup -> plague_effect_setups (force/region) -> plague_effects -> faction set bundles,
split by our faction sets: Pestilens takes the positive bundle, everyone else the negative one.
Nurgle's symptoms reuse their vanilla bundles; the rest get bundles of their own.
"""
from dataclasses import dataclass, field

from tools.rows import empty_like as _empty_like, find as _find, row as _row
from tools.effects import ATTRITION_IMMUNITY
from tools.keys import COMPONENT_SET, NEGATIVE_SET, POSITIVE_SET, SYMPTOM_COST

SKILLS = "UI/Campaign UI/Skills/"
FORCE, REGION = "force", "region"
F = "force_to_force_own"
R = "region_to_region_own"
P = "province_to_province_own_unseen"
RP = "region_to_province_own_unseen"


@dataclass(frozen=True)
class Symptom:
    id: str
    kind: str                              # FORCE or REGION
    icon: str
    nurgle: str | None = None              # wh3_dlc25_nur_<id> this clones, reusing its bundles
    ours: tuple = ()                       # ((effect, scope, value), ...) for Pestilens
    enemy: tuple = ()                      # the same for everyone else
    # lang -> (name, body part): the window names a plague from these, like Nurgle's "Sweating Eyes"
    names: dict = field(default_factory=dict)


def _nurgle(sid, kind, icon):
    return Symptom(sid, kind, SKILLS + icon, nurgle=sid)


SYMPTOMS = [
    # Nurgle's symptoms without a Nurgle-only effect (battle_7 spell, force_5 recruits, settlement_2 corruption)
    _nurgle("battle_1", FORCE, "battle_defence.png"),
    _nurgle("battle_2", FORCE, "battle_armour.png"),
    _nurgle("battle_3", FORCE, "battle_ammo.png"),
    _nurgle("battle_4", FORCE, "battle_attack.png"),
    _nurgle("battle_5", FORCE, "battle_damage.png"),
    _nurgle("battle_6", FORCE, "battle_speed.png"),
    _nurgle("force_1", FORCE, "campaign_magic.png"),
    _nurgle("force_2", FORCE, "battle_magic.png"),
    _nurgle("force_3", FORCE, "campaign_disaster.png"),
    _nurgle("force_4", FORCE, "campaign_movement.png"),
    _nurgle("force_6", FORCE, "battle_military_spending.png"),
    _nurgle("settlement_1", REGION, "campaign_growth.png"),
    _nurgle("settlement_3", REGION, "campaign_turns.png"),
    _nurgle("settlement_4", REGION, "campaign_construction.png"),
    _nurgle("settlement_5", REGION, "campaign_military_spending.png"),
    # Skrolk's vanilla plague, one symptom per component, vanilla values
    Symptom("sk_frenzy", FORCE, SKILLS + "wh_main_unit_passive_frenzy.png",
            ours=(("wh_dlc08_effect_ability_enable_frenzy", F, 1.0), ("wh_main_effect_force_stat_leadership", F, 8.0)),
            enemy=(("wh_main_effect_force_stat_leadership", F, -9.0),),
            names={"ru": ("Неистовство Пестиленса", "Резцы"),
                   "en": ("Pestilent Frenzy", "Fangs")}),
    Symptom("sk_vigour", FORCE, SKILLS + "wh2_dlc11_deathly_vigour.png",
            ours=(("wh2_twa03_effect_vigour_loss_reduction_pestilens_units", F, -50.0),
                  ("wh_main_effect_force_all_campaign_replenishment_rate", F, 5.0)),
            enemy=(("wh2_main_effect_force_all_campaign_enable_disease_attrition", F, 1.0),),
            names={"ru": ("Гнилая стойкость", "Хвост"),
                   "en": ("Rotten Stamina", "Tail")}),
    Symptom("sk_growth", REGION, SKILLS + "campaign_growth.png",
            ours=(("wh3_main_effect_province_growth_plague", P, 25.0),),
            enemy=(("wh3_main_effect_province_growth_plague", P, -30.0),),
            names={"ru": ("Крысиный выводок", "Брюхо"),
                   "en": ("Ratspawn Brood", "Belly")}),
    Symptom("sk_income", REGION, SKILLS + "campaign_military_spending.png",
            ours=(("wh_main_effect_economy_gdp_mod_all", R, 15.0),),
            enemy=(("wh_main_effect_economy_gdp_mod_all", R, -50.0),),
            names={"ru": ("Мор на рынках", "Лапы"),
                   "en": ("Market Blight", "Paws")}),
    Symptom("sk_construction", REGION, SKILLS + "campaign_construction.png",
            ours=(("wh2_main_effect_building_construction_time_mod_all", R, -33.0),),
            enemy=(("wh2_main_effect_building_construction_time_mod_all", R, 50.0),),
            names={"ru": ("Рабы до последнего вздоха", "Хребет"),
                   "en": ("Slaves to the Last Breath", "Spine")}),
    # Skaven symptoms
    Symptom("black_death", FORCE, SKILLS + "character_plague.png",
            # ours roam anywhere without attrition; infected enemies waste away
            ours=((ATTRITION_IMMUNITY, F, 1.0),),
            enemy=(("wh2_main_effect_force_all_campaign_enable_disease_attrition", F, 1.0),),
            names={"ru": ("Чёрная смерть", "Шерсть"),
                   "en": ("Black Death", "Fur")}),
    Symptom("red_pox", REGION, SKILLS + "campaign_public_order.png",
            ours=(("wh_main_effect_public_order_events", RP, 4.0),),
            enemy=(("wh_main_effect_public_order_events", RP, -6.0),),
            names={"ru": ("Красная оспа", "Шкура"),
                   "en": ("Red Pox", "Hide")}),
    Symptom("tainted_warp", FORCE, SKILLS + "wh_main_unit_contact_poison.png",
            ours=(("wh3_dlc29_effect_force_stat_enable_poison_contact_effect", F, 1.0),),
            enemy=(("wh_main_effect_force_stat_melee_defence", F, -3.0),),
            names={"ru": ("Порченый варп", "Когти"),
                   "en": ("Tainted Warp", "Claws")}),
    Symptom("thirteen", FORCE, SKILLS + "wh2_skv_plague_lord.png",
            ours=(("wh_main_effect_force_stat_weapon_strength", F, 13.0),),
            enemy=(("wh_main_effect_force_stat_weapon_strength", F, -13.0),),
            names={"ru": ("Число Тринадцати", "Рога"),
                   "en": ("The Thirteenth", "Horns")}),
    Symptom("horned_rat", REGION, SKILLS + "campaign_skaven_corruption.png",
            ours=(("wh3_main_effect_corruption_skaven_events_bad", RP, 4.0),),
            enemy=(("wh3_main_effect_corruption_skaven_events_bad", RP, 4.0),),
            names={"ru": ("Скверна Рогатой Крысы", "Усы"),
                   "en": ("Horned Rat's Taint", "Whiskers")}),
]

START_SYMPTOM = "skrolkpl_sym_sk_frenzy"  # the one symptom open at the start: Skrolk's own plague

BUNDLE_TEMPLATES = {FORCE: "wh3_dlc25_nur_battle_1_positive", REGION: "wh3_dlc25_nur_settlement_1_positive"}


def blessed_value(effect, value):
    """Blessed symptoms double their effects; on/off effects (enable..., immunity...) stay on."""
    if abs(value) == 1.0 and ("enable" in effect or "immunity" in effect):
        return value
    return value * 2


def symptom_key(sid):
    return "skrolkpl_sym_" + sid


def symptom_keys():
    return [symptom_key(s.id) for s in SYMPTOMS]


def make_symptom_tables(table):
    """Return the catalogue's db tables; `table(name)` gives a vanilla table."""
    comps, setups = table("plague_components_tables"), table("plague_component_setups_tables")
    effect_setups, effects = table("plague_effect_setups_tables"), table("plague_effects_tables")
    fseb, bundles = table("faction_set_effect_bundles_tables"), table("effect_bundles_tables")
    junctions = table("effect_bundles_to_effects_junctions_tables")
    out = {t.name: _empty_like(t) for t in (comps, setups, effect_setups, effects, fseb, bundles, junctions)}
    comp_template = _find(comps, "key", "wh3_dlc25_nur_battle_1")
    for s in SYMPTOMS:
        key = symptom_key(s.id)
        out[comps.name].rows.append(_row(comps, comp_template, key=key, cost=SYMPTOM_COST, image_path=s.icon))
        out[setups.name].rows.append(_row(setups, component=key, set=COMPONENT_SET, effects=key))
        if s.nurgle:  # vanilla's force/region/garrison shape
            source = "wh3_dlc25_nur_" + s.nurgle
            out[effect_setups.name].rows.append([key if v == source else v
                                                 for v in _find(effect_setups, "key", source)])
        elif s.kind == FORCE:  # like Nurgle's battle symptoms: the army and settlement garrisons
            out[effect_setups.name].rows.append(_row(effect_setups, key=key, force_effects=key,
                                                     region_effects=None, garrison_effects=key))
        else:
            out[effect_setups.name].rows.append(_row(effect_setups, key=key, force_effects=None,
                                                     region_effects=key, garrison_effects=None))
        out[effects.name].rows.append(_row(effects, key=key, positive_effect_for_factions=key + "_pos",
                                           negative_effect_for_factions=key + "_neg",
                                           positive_blessed_effect_for_factions=key + "_pos_blessed",
                                           negative_blessed_effect_for_factions=key + "_neg_blessed"))
        for side, fset, effs, word in (("_pos", POSITIVE_SET, s.ours, "positive"),
                                       ("_neg", NEGATIVE_SET, s.enemy, "negative")):
            for blessed in (False, True):
                suffix = side + ("_blessed" if blessed else "")
                if s.nurgle:
                    bundle = "wh3_dlc25_nur_%s_%s%s" % (s.nurgle, word, "_blessed" if blessed else "")
                else:
                    bundle = key + suffix
                    out[bundles.name].rows.append(_row(bundles, _find(bundles, "key", BUNDLE_TEMPLATES[s.kind]),
                                                       key=bundle))
                    for effect, scope, value in effs:
                        out[junctions.name].rows.append(_row(
                            junctions, junctions.rows[0], effect_bundle_key=bundle, effect_key=effect,
                            effect_scope=scope, value=blessed_value(effect, value) if blessed else value,
                            advancement_stage="start_turn_completed"))
                out[fseb.name].rows.append(_row(fseb, effect_bundle=bundle, faction_set=fset, key=key + suffix))
    return list(out.values())


def make_symptom_loc(lang, vanilla):
    """Names and descriptions: our own for new symptoms, vanilla's for Nurgle's clones."""
    entries = []
    for s in SYMPTOMS:
        key = symptom_key(s.id)
        if s.nurgle:
            for prefix in ("plague_components_localised_name_", "plague_components_description_"):
                text = vanilla.get(prefix + "wh3_dlc25_nur_" + s.nurgle)
                if text is not None:
                    entries.append((prefix + key, text))
        else:
            name, desc = s.names[lang]
            entries += [("plague_components_localised_name_" + key, name),
                        ("plague_components_description_" + key, desc)]
    return entries
