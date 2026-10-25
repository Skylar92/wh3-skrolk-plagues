"""Keys shared by the release pack's generators and its campaign script."""

PESTILENS = "wh2_main_skv_clan_pestilens"
FEATURE = "skrolkpl_feature"                  # campaign group Pestilens joins for the plague window
COMPONENT_SET = "skrolkpl_components"         # plague_component_setup_sets key
POSITIVE_SET = "skrolkpl_positive"            # faction set taking a plague's positive effects
NEGATIVE_SET = "skrolkpl_negative"            # everyone else
# Pestilens' faction plague setup set: the plagues the engine may start for it
PLAGUE_SET = "skrolkpl_plagues"
SYMPTOM_COST = "skrolkpl_symptom"             # resource cost of one symptom (zero: the script charges)
# skaven_food spending factor; also the junction's unique_id, as in vanilla's Throt flesh lab, which
# passes this key to cm:faction_add_pooled_resource
FOOD_FACTOR = "skrolkpl_plague_food"
