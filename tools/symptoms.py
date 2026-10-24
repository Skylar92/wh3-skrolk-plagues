"""Skrolk's symptom catalogue and its db rows.

Every symptom is a plague component of type SYMPTOM in our component set. Its effects go
component setup -> plague_effect_setups (force/region) -> plague_effects -> faction set bundles,
split by our faction sets: Pestilens takes the positive bundle, everyone else the negative one.
Nurgle's symptoms reuse their vanilla bundles; the rest get bundles of their own.
"""
from dataclasses import dataclass, field

from tools.rows import empty_like as _empty_like, find as _find, row as _row
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
    names: dict = field(default_factory=dict)  # lang -> (name, description)


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
            names={"ru": ("Неистовство Пестиленса", "Чумные проповеди доводят крыс до исступления."),
                   "en": ("Pestilent Frenzy", "Plague sermons drive the rats into a frenzy.")}),
    Symptom("sk_vigour", FORCE, SKILLS + "wh2_dlc11_deathly_vigour.png",
            ours=(("wh2_twa03_effect_vigour_loss_reduction_pestilens_units", F, -50.0),
                  ("wh_main_effect_force_all_campaign_replenishment_rate", F, 5.0)),
            enemy=(("wh2_main_effect_force_all_campaign_enable_disease_attrition", F, 1.0),),
            names={"ru": ("Гнилая стойкость", "Больные не устают, а здоровые гниют на ходу."),
                   "en": ("Rotten Stamina", "The sick never tire; the healthy rot as they march.")}),
    Symptom("sk_growth", REGION, SKILLS + "campaign_growth.png",
            ours=(("wh3_main_effect_province_growth_plague", P, 25.0),),
            enemy=(("wh3_main_effect_province_growth_plague", P, -30.0),),
            names={"ru": ("Крысиный выводок", "Чума косит чужих и плодит своих."),
                   "en": ("Ratspawn Brood", "The plague culls theirs and breeds ours.")}),
    Symptom("sk_income", REGION, SKILLS + "campaign_military_spending.png",
            ours=(("wh_main_effect_economy_gdp_mod_all", R, 15.0),),
            enemy=(("wh_main_effect_economy_gdp_mod_all", R, -50.0),),
            names={"ru": ("Мор на рынках", "Торговля в заражённых городах замирает."),
                   "en": ("Market Blight", "Trade in infected towns grinds to a halt.")}),
    Symptom("sk_construction", REGION, SKILLS + "campaign_construction.png",
            ours=(("wh2_main_effect_building_construction_time_mod_all", R, -33.0),),
            enemy=(("wh2_main_effect_building_construction_time_mod_all", R, 50.0),),
            names={"ru": ("Рабы до последнего вздоха", "Больные рабы работают, пока не упадут."),
                   "en": ("Slaves to the Last Breath", "Sick slaves work until they drop.")}),
    # Skaven symptoms
    Symptom("black_death", FORCE, SKILLS + "character_plague.png",
            ours=(("wh2_dlc16_effect_attrition_immunity_plague", F, 1.0),),
            enemy=(("wh2_main_effect_force_all_campaign_enable_disease_attrition", F, 1.0),),
            names={"ru": ("Чёрная смерть", "Свои давно переболели; чужие мрут в походе."),
                   "en": ("Black Death", "Ours have long survived it; theirs die on the march.")}),
    Symptom("red_pox", REGION, SKILLS + "campaign_public_order.png",
            ours=(("wh_main_effect_public_order_events", RP, 4.0),),
            enemy=(("wh_main_effect_public_order_events", RP, -6.0),),
            names={"ru": ("Красная оспа", "Язвы и страх ломают порядок в чужих городах."),
                   "en": ("Red Pox", "Sores and fear break order in enemy towns.")}),
    Symptom("tainted_warp", FORCE, SKILLS + "wh_main_unit_contact_poison.png",
            ours=(("wh3_dlc29_effect_force_stat_enable_poison_contact_effect", F, 1.0),),
            enemy=(("wh_main_effect_force_stat_melee_defence", F, -3.0),),
            names={"ru": ("Порченый варп", "Клинки в варп-гнили отравляют каждую рану."),
                   "en": ("Tainted Warp", "Warp-rotted blades poison every wound.")}),
    Symptom("thirteen", FORCE, SKILLS + "wh2_skv_plague_lord.png",
            ours=(("wh_main_effect_force_stat_weapon_strength", F, 13.0),),
            enemy=(("wh_main_effect_force_stat_weapon_strength", F, -13.0),),
            names={"ru": ("Число Тринадцати", "Тринадцать язв во славу Рогатой Крысы."),
                   "en": ("The Thirteenth", "Thirteen sores for the glory of the Horned Rat.")}),
    Symptom("horned_rat", REGION, SKILLS + "campaign_skaven_corruption.png",
            ours=(("wh3_main_effect_corruption_skaven_events_bad", RP, 4.0),),
            enemy=(("wh3_main_effect_corruption_skaven_events_bad", RP, 4.0),),
            names={"ru": ("Скверна Рогатой Крысы", "Где прошла чума, Рогатая Крыса пускает корни."),
                   "en": ("Horned Rat's Taint", "Where the plague passes, the Horned Rat takes root.")}),
]

BUNDLE_TEMPLATES = {FORCE: "wh3_dlc25_nur_battle_1_positive", REGION: "wh3_dlc25_nur_settlement_1_positive"}


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
        force = key if s.kind == FORCE else None
        out[effect_setups.name].rows.append(_row(effect_setups, key=key, force_effects=force,
                                                 region_effects=None if force else key, garrison_effects=None))
        out[effects.name].rows.append(_row(effects, key=key, positive_effect_for_factions=key + "_pos",
                                           negative_effect_for_factions=key + "_neg"))
        for side, fset, effs in (("_pos", POSITIVE_SET, s.ours), ("_neg", NEGATIVE_SET, s.enemy)):
            if s.nurgle:
                bundle = "wh3_dlc25_nur_%s_%s" % (s.nurgle, "positive" if side == "_pos" else "negative")
            else:
                bundle = key + side
                out[bundles.name].rows.append(_row(bundles, _find(bundles, "key", BUNDLE_TEMPLATES[s.kind]),
                                                   key=bundle))
                for effect, scope, value in effs:
                    out[junctions.name].rows.append(_row(junctions, junctions.rows[0], effect_bundle_key=bundle,
                                                         effect_key=effect, effect_scope=scope, value=value,
                                                         advancement_stage="start_turn_completed"))
            out[fseb.name].rows.append(_row(fseb, effect_bundle=bundle, faction_set=fset, key=key + side))
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
