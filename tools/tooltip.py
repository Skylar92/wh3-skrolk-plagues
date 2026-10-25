"""Our copy of the active plague tooltip (ui/campaign ui/tooltip_dlc25_active_plague.twui.xml).

The engine builds a plague's tooltip from its composition (the symptoms picked in the window); a script
cannot add the strain rot to it. The tooltip lists one section per faction set ("Plague effects on
Pestilens / Non-Pestilens forces and settlements"), each a list of effect lines. We add rot lines to that
section template, after its effects. Each plague has its own rot: line i shows the script value
"skrolkpl_strain_<plague id>_ours_i" in the Pestilens section and "..._enemy_i" in the Non-Pestilens one,
the plague id being its symptoms joined with "+" (the campaign script publishes them with
common.set_context_value, for every order of the symptoms). The effect list stores the plague's
composition so the lines can read its symptoms. Other sections (Nurgle's sets) never show them.
"""
import uuid

TOOLTIP_PATH = "ui/campaign ui/tooltip_dlc25_active_plague.twui.xml"
LINE_COUNT = 6  # rots per strain (3) x effects per rot (up to 2)
STRAIN_LINES = tuple("skrolkpl_strain_line_%d" % i for i in range(1, LINE_COUNT + 1))
_HIERARCHY_ANCHOR = "\t\t\t\t\t\t</template_effect_bundle>\n"
_COMPONENT_ANCHOR = "\t\t</immunity_duration>\n"
# the effect list's propagator: its composition is stored after it for the rot lines
_STORE_ANCHOR = (
    '\t\t\t\t\tcontext_function_id="CombinedEffectsAndTypeList(true, PlayersFaction).Filter('
    'EffectListWithSourceList.Transform(EffectList).IsEmpty == false)"/>\n'
    '\t\t\t\t<callback_with_context\n'
    '\t\t\t\t\tcallback_id="ContextPropagator"\n'
    '\t\t\t\t\tcontext_object_id="CcoCampaignPlagueInfection"\n'
    '\t\t\t\t\tcontext_function_id="PlagueCompositionContext"/>\n')
_STORE = ('\t\t\t\t<callback_with_context\n'
          '\t\t\t\t\tcallback_id="ContextObjectStore"\n'
          '\t\t\t\t\tcontext_object_id="CcoCampaignPlagueComposition"/>\n')
PLAGUE_ID = ('StoredContextFromParent("CcoCampaignPlagueComposition").PlagueIngredientList'
             '.Filter(Key.Contains("skrolkpl_sym_")).JoinString(Key, "+")')


def _guid(name):
    h = uuid.uuid5(uuid.NAMESPACE_URL, "skrolkpl/" + name).hex.upper()
    return "%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:32])


def _q(text):
    return text.replace("&&", "&amp;&amp;").replace('"', "&quot;").replace(">", "&gt;")


def _component(comp_id, n):
    this, state = _guid(comp_id), _guid(comp_id + "/state")
    ours = 'ScriptObjectContext("skrolkpl_strain_" + id + "_ours_%d").StringValue' % n
    enemy = 'ScriptObjectContext("skrolkpl_strain_" + id + "_enemy_%d").StringValue' % n
    is_ours = 'FactionSetList[0] == CcoFactionSetRecord("skrolkpl_positive")'
    is_enemy = 'FactionSetList[0] == CcoFactionSetRecord("skrolkpl_negative")'
    plague = "(id = %s) => " % PLAGUE_ID
    label = plague + 'GetIfElse(%s, %s, GetIfElse(%s, %s, ""))' % (is_ours, ours, is_enemy, enemy)
    visible = plague + '(%s && %s != "") || (%s && %s != "")' % (is_ours, ours, is_enemy, enemy)
    return f'''\t\t<{comp_id}
\t\t\tthis="{this}"
\t\t\tid="{comp_id}"
\t\t\tallowhorizontalresize="false"
\t\t\ttooltipslocalised="true"
\t\t\tuniqueguid="{this}"
\t\t\tcurrentstate="{state}"
\t\t\tdefaultstate="{state}">
\t\t\t<callbackwithcontextlist>
\t\t\t\t<callback_with_context
\t\t\t\t\tcallback_id="ContextTextLabel"
\t\t\t\t\tcontext_object_id="CcoPlagueEffectList"
\t\t\t\t\tcontext_function_id="{_q(label)}"/>
\t\t\t\t<callback_with_context
\t\t\t\t\tcallback_id="ContextVisibilitySetter"
\t\t\t\t\tcontext_object_id="CcoPlagueEffectList"
\t\t\t\t\tcontext_function_id="{_q(visible)}"/>
\t\t\t</callbackwithcontextlist>
\t\t\t<states>
\t\t\t\t<newstate
\t\t\t\t\tthis="{state}"
\t\t\t\t\tname="NewState"
\t\t\t\t\twidth="439"
\t\t\t\t\theight="26"
\t\t\t\t\tuniqueguid="{state}">
\t\t\t\t\t<component_text
\t\t\t\t\t\ttextxoffset="14.00,6.00"
\t\t\t\t\t\ttextyoffset="4.00,6.00"
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
    for anchor in (_HIERARCHY_ANCHOR, _COMPONENT_ANCHOR, _STORE_ANCHOR):
        if vanilla.count(anchor) != 1:
            raise ValueError("unexpected tooltip layout: anchor not found once: " + anchor.strip())
    hierarchy = "".join('\t\t\t\t\t\t<%s this="%s"/>\n' % (comp_id, _guid(comp_id)) for comp_id in STRAIN_LINES)
    components = "".join(_component(comp_id, n) for n, comp_id in enumerate(STRAIN_LINES, 1))
    out = vanilla.replace(_HIERARCHY_ANCHOR, _HIERARCHY_ANCHOR + hierarchy)
    out = out.replace(_STORE_ANCHOR, _STORE_ANCHOR + _STORE)
    return out.replace(_COMPONENT_ANCHOR, _COMPONENT_ANCHOR + components)
