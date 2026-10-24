"""Fill the build-time markers in the campaign script."""


def lua_string_list(values):
    return "{ " + ", ".join('"%s"' % v for v in values) + " }"


def render_core(template, symptom_keys):
    marker = "{} --@@SYMPTOM_KEYS@@"
    if marker not in template:
        raise ValueError("SYMPTOM_KEYS marker missing")
    return template.replace(marker, lua_string_list(symptom_keys))
