"""Fill the build-time markers in the campaign script."""


def lua_string_list(values):
    return "{ " + ", ".join('"%s"' % v for v in values) + " }"


def _lua_value(v):
    if v is None:
        return "nil"
    if isinstance(v, str):
        return '"%s"' % v
    return repr(float(v))


def lua_rots(rots):
    """The rot catalogue as a Lua list: id, kind, weight, bundle keys per side/target, effects per side."""
    from tools.rots import rot_bundles
    items = []
    for rot in rots:
        b = rot_bundles(rot)
        def effects(es):
            return ", ".join("{ %s, %s, %s }" % tuple(_lua_value(x) for x in e) for e in es)
        items.append(
            '{ id = "%s", kind = "%s", weight = %d, ours_force = %s, ours_region = %s, enemy_force = %s, '
            'enemy_region = %s, show_ours = { %s }, show_enemy = { %s } }' % (
                rot.id, rot.kind, rot.weight, _lua_value(b["ours"]["force"]), _lua_value(b["ours"]["region"]),
                _lua_value(b["enemy"]["force"]), _lua_value(b["enemy"]["region"]), effects(rot.ours),
                effects(rot.enemy)))
    return "{\n\t" + ",\n\t".join(items) + ",\n}"


def render_core(template, symptom_keys, start_symptom, rots):
    if start_symptom not in symptom_keys:
        raise ValueError("start symptom not in the catalogue: " + start_symptom)
    for marker in ("{} --@@SYMPTOM_KEYS@@", '"" --@@START_SYMPTOM@@', "{} --@@ROTS@@"):
        if marker not in template:
            raise ValueError("marker missing: " + marker)
    return (template.replace("{} --@@SYMPTOM_KEYS@@", lua_string_list(symptom_keys))
            .replace('"" --@@START_SYMPTOM@@', '"%s"' % start_symptom)
            .replace("{} --@@ROTS@@", lua_rots(rots)))
