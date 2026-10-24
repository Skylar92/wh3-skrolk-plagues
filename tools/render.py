"""Fill the build-time markers in the campaign script."""


def lua_string_list(values):
    return "{ " + ", ".join('"%s"' % v for v in values) + " }"


def render_core(template, symptom_keys, start_symptom):
    if start_symptom not in symptom_keys:
        raise ValueError("start symptom not in the catalogue: " + start_symptom)
    for marker in ("{} --@@SYMPTOM_KEYS@@", '"" --@@START_SYMPTOM@@'):
        if marker not in template:
            raise ValueError("marker missing: " + marker)
    return (template.replace("{} --@@SYMPTOM_KEYS@@", lua_string_list(symptom_keys))
            .replace('"" --@@START_SYMPTOM@@', '"%s"' % start_symptom))
