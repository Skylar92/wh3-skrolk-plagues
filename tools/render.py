"""Fill the build-time markers in the campaign script."""


def lua_string_list(values):
    return "{ " + ", ".join('"%s"' % v for v in values) + " }"


def _lua_value(v):
    if v is None:
        return "nil"
    if isinstance(v, str):
        return '"%s"' % v
    return repr(float(v))


def lua_rots(rots, positive_good=None, icons=None):
    """The rot catalogue as a Lua list: id, kind, weight, effects per side.

    Each shown effect is {effect, scope, value, bigger_is_better, icon, icon_negative}: effects_tables'
    is_positive_value_good (`positive_good`: {effect: bool}; missing -> True) and icon paths (`icons`:
    {effect: (icon, icon_negative)}, under ui/campaign ui/effect_bundles/). The script sums a strain's
    effects and picks colour and icon from the sum.
    """
    positive_good = positive_good or {}
    icons = icons or {}
    items = []
    for rot in rots:
        def effects(es):
            out = []
            for effect, scope, value in es:
                bigger_better = positive_good.get(effect, True)
                icon, icon_negative = icons.get(effect, (None, None))
                path = "ui/campaign ui/effect_bundles/" + icon if icon else None
                path_negative = "ui/campaign ui/effect_bundles/" + icon_negative if icon_negative else path
                out.append("{ %s, %s, %s, %s, %s, %s }" % (
                    _lua_value(effect), _lua_value(scope), _lua_value(value),
                    "true" if bigger_better else "false", _lua_value(path), _lua_value(path_negative)))
            return ", ".join(out)
        items.append('{ id = "%s", kind = "%s", weight = %d, show_ours = { %s }, show_enemy = { %s } }' % (
            rot.id, rot.kind, rot.weight, effects(rot.ours), effects(rot.enemy)))
    return "{\n\t" + ",\n\t".join(items) + ",\n}"


def render_core(template, symptom_keys, start_symptom, rots, positive_good=None, icons=None):
    if start_symptom not in symptom_keys:
        raise ValueError("start symptom not in the catalogue: " + start_symptom)
    for marker in ("{} --@@SYMPTOM_KEYS@@", '"" --@@START_SYMPTOM@@', "{} --@@ROTS@@"):
        if marker not in template:
            raise ValueError("marker missing: " + marker)
    return (template.replace("{} --@@SYMPTOM_KEYS@@", lua_string_list(symptom_keys))
            .replace('"" --@@START_SYMPTOM@@', '"%s"' % start_symptom)
            .replace("{} --@@ROTS@@", lua_rots(rots, positive_good, icons)))
