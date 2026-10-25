"""Our copy of the plague window's layout (ui/campaign ui/dlc25_nurgle_plagues.twui.xml).

One change: the counter under the grid. Vanilla reads "Plagues until new Blessed Symptoms and Symptom
locations: N" from the script value random_plague_creation_count_<faction>; Skrolk's layout changes every
turn instead, so for Pestilens the counter shows our own text (ui_texts "skrolkpl_layout"). The label is
updated constantly by the window, so a script cannot overwrite it; Nurgle keeps the vanilla text.
"""
from tools.keys import PESTILENS

WINDOW_PATH = "ui/campaign ui/dlc25_nurgle_plagues.twui.xml"
VANILLA_COUNTER = (
    'context_function_id="(turns = RoundFloat(ScriptObjectContext(&quot;random_plague_creation_count_&quot; '
    '+ PlayersFaction.FactionRecordContext.Key).NumericValue)) =&gt; {&#10;  '
    'Loc(&quot;wh3_dlc25_plagues_instability_turn&quot; + GetIf(turns != 1, &quot;s&quot;), turns)&#10;}"')
OUR_COUNTER = (
    'context_function_id="(turns = RoundFloat(ScriptObjectContext(&quot;random_plague_creation_count_&quot; '
    '+ PlayersFaction.FactionRecordContext.Key).NumericValue)) =&gt; {&#10;  '
    'GetIfElse(PlayersFaction.FactionRecordContext.Key == &quot;%s&quot;, Loc(&quot;skrolkpl_layout&quot;, 1), '
    'Loc(&quot;wh3_dlc25_plagues_instability_turn&quot; + GetIf(turns != 1, &quot;s&quot;), turns))&#10;}"' % PESTILENS)


def make_plague_window(vanilla):
    if vanilla.count(VANILLA_COUNTER) != 1:
        raise ValueError("unexpected plague window layout: the counter label was not found once")
    return vanilla.replace(VANILLA_COUNTER, OUR_COUNTER)
