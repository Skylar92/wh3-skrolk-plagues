"""Our copy of the active plague tooltip (ui/campaign ui/tooltip_dlc25_active_plague.twui.xml).

The engine builds a plague's tooltip from its composition (the symptoms picked in the window); a script
cannot add the strain rot to it. So two text lines are added after "immunity duration": they show texts
the campaign script publishes (common.set_context_value) and are visible only on infections whose
composition holds our symptoms. Nurgle's tooltips are unchanged.
"""
import uuid

TOOLTIP_PATH = "ui/campaign ui/tooltip_dlc25_active_plague.twui.xml"
# (component id, script object holding its text)
STRAIN_LINES = (("skrolkpl_strain_ours_line", "skrolkpl_strain_ours"),
                ("skrolkpl_strain_enemy_line", "skrolkpl_strain_enemy"))
_HIERARCHY_ANCHOR = '\t\t\t\t<immunity_duration this="6BCBF6A6-065C-496B-9C743C7F79BD3830"/>\n'
_COMPONENT_ANCHOR = "\t\t</immunity_duration>\n"


def _guid(name):
    h = uuid.uuid5(uuid.NAMESPACE_URL, "skrolkpl/" + name).hex.upper()
    return "%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:32])


def _q(text):
    return text.replace('"', "&quot;").replace("&&", "&amp;&amp;")


def _component(comp_id, script_object, n):
    this, state = _guid(comp_id), _guid(comp_id + "/state")
    text = 'ScriptObjectContext("%s").StringValue' % script_object
    visible = 'PlagueCompositionContext.PlagueIngredientList.Any(Key.Contains("skrolkpl_sym_")) && %s != ""' % text
    return f'''\t\t<{comp_id}
\t\t\tthis="{this}"
\t\t\tid="{comp_id}"
\t\t\toffset="0.00,200.00"
\t\t\tallowhorizontalresize="false"
\t\t\ttooltipslocalised="true"
\t\t\tuniqueguid="{this}"
\t\t\tcurrentstate="{state}"
\t\t\tdefaultstate="{state}">
\t\t\t<callbackwithcontextlist>
\t\t\t\t<callback_with_context
\t\t\t\t\tcallback_id="ContextTextLabel"
\t\t\t\t\tcontext_object_id="CcoCampaignPlagueInfection"
\t\t\t\t\tcontext_function_id="{_q(text)}"/>
\t\t\t\t<callback_with_context
\t\t\t\t\tcallback_id="ContextVisibilitySetter"
\t\t\t\t\tcontext_object_id="CcoCampaignPlagueInfection"
\t\t\t\t\tcontext_function_id="{_q(visible)}"/>
\t\t\t\t<callback_with_context
\t\t\t\t\tcallback_id="ContextVisibilitySetter"
\t\t\t\t\tcontext_object_id="CcoCampaignPlagueComposition"
\t\t\t\t\tcontext_function_id="false"/>
\t\t\t</callbackwithcontextlist>
\t\t\t<states>
\t\t\t\t<newstate
\t\t\t\t\tthis="{state}"
\t\t\t\t\tname="NewState"
\t\t\t\t\twidth="440"
\t\t\t\t\theight="26"
\t\t\t\t\tuniqueguid="{state}">
\t\t\t\t\t<component_text
\t\t\t\t\t\ttextvalign="Bottom"
\t\t\t\t\t\ttextxoffset="12.00,8.00"
\t\t\t\t\t\ttextyoffset="2.00,8.00"
\t\t\t\t\t\ttexthbehaviour="Resize"
\t\t\t\t\t\ttextlabel="StateText_skrolkpl_{n}"
\t\t\t\t\t\tfont_m_size="12"
\t\t\t\t\t\tfont_m_colour="#FFF8D7FF"
\t\t\t\t\t\tfont_m_leading="3"
\t\t\t\t\t\tfontcat_name="body_12"/>
\t\t\t\t</newstate>
\t\t\t</states>
\t\t</{comp_id}>
'''


def make_plague_tooltip(vanilla):
    if "\r\n" in vanilla:  # the vanilla file has Windows line ends; keep them
        return _make(vanilla.replace("\r\n", "\n")).replace("\n", "\r\n")
    return _make(vanilla)


def _make(vanilla):
    for anchor in (_HIERARCHY_ANCHOR, _COMPONENT_ANCHOR):
        if vanilla.count(anchor) != 1:
            raise ValueError("unexpected tooltip layout: anchor not found once: " + anchor.strip())
    hierarchy = "".join('\t\t\t\t<%s this="%s"/>\n' % (comp_id, _guid(comp_id)) for comp_id, _ in STRAIN_LINES)
    components = "".join(_component(comp_id, obj, n) for n, (comp_id, obj) in enumerate(STRAIN_LINES))
    out = vanilla.replace(_HIERARCHY_ANCHOR, _HIERARCHY_ANCHOR + hierarchy)
    return out.replace(_COMPONENT_ANCHOR, _COMPONENT_ANCHOR + components)
