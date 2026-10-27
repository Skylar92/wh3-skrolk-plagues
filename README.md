# Skrolk's Plagues

*"Thirteen sores, thirteen fevers, one gift for the Great Horned Rat!"*

[MIT License](LICENSE)

**Lord Skrolk finally brews his own plagues.** This Total War: WARHAMMER III mod gives a human Clan Pestilens a plague crafting window modelled on Nurgle's: pick three linked symptoms from a grid that reshuffles every turn, set duration, spread and immunity, pay in Skaven food and gold, and release the plague on your own armies and settlements. Your infected forces get the upside, everyone else's get the downside. Every new plague is unstable and may rot in ways nobody, not even Skrolk, can predict.

| | |
|---|---|
| **Game** | Total War: WARHAMMER III, update 9.0 (Lords of the End Times) |
| **Faction** | Clan Pestilens (Lord Skrolk), human player only; the AI keeps the vanilla Skaven plague |
| **Mode** | single player |
| **Languages** | English (main pack), Russian (translation pack) |
| **Save-game** | can be added to a running campaign |
| **Tests** | 218 automated tests (game tables, campaign script, window and tooltip files, packs) |

## Crafting a plague

The **Plagues** button opens Nurgle's window, reworded for Skrolk.

- **Symptoms:** 23 in the catalogue, 18 on the grid at a time. 13 come from Nurgle (those without a Nurgle-only effect), 5 are Skrolk's vanilla plague split into its parts with their vanilla values, and 5 are new Skaven ones.
- **Links:** a plague takes exactly 3 different symptoms. The first must be an open symptom that is not resting; each next one must be linked to one already picked. At the start only *Pestilent Frenzy* is open; every symptom used in a plague opens up as a new starting point.
- **New layout every turn:** at the start of each Clan Pestilens turn the 18 symptoms are drawn again from the catalogue and placed at random, so the links change and the same plague cannot be farmed. One symptom per layout is **blessed** (its effects doubled). Every layout can make at least one plague.
- **Resting:** a used symptom rests for 3 turns (Nurgle's rule). There is no other cooldown: make as many plagues per turn as you can pay for.
- **Slots:** Nurgle's duration (3-6 turns), spread chance (25-55%) and immunity (5-2 turns) slots, levels 0-3.
- **Price:** 20 Skaven food and 2500 gold, plus 2 food per slot level. While the faction cannot pay, the Infect button is hidden and the window says what is missing.
- **Targets:** Nurgle's two direct rites, infecting one of your own armies or settlements. From there the plague spreads like any plague: army to army, army to settlement, settlement to settlement, and through battle.

### Symptoms

| Symptom | Clan Pestilens | Everyone else |
|---|---|---|
| Bleeding | +4 melee defence | -4 melee defence |
| Weeping | +15 armour | -15 armour |
| Violent | +10% missile resistance | -20% ammunition |
| Necrotising | +4 melee attack | -4 melee attack |
| Sweating | +10% weapon strength | -10% weapon strength |
| Rotting | vanguard deployment | -15% speed |
| Feverish | +5 winds of magic | -5 winds of magic |
| Acrid | -10% spell cost | +10% spell cost |
| Liquifying | +10% replenishment | plague attrition |
| Inflamed | +15% campaign movement | -15% campaign movement |
| Flaccid | -15% upkeep | +15% upkeep |
| Dripping | -1 turn on basic military buildings | +50% construction time |
| Swelling | -15% construction cost | +15% construction cost |
| Pestilent Frenzy | frenzy, +8 leadership | -9 leadership |
| Rotten Stamina | -50% vigour loss, +5% replenishment | disease attrition |
| Ratspawn Brood | +25 growth | -30 growth |
| Market Blight | +15% income | -50% income |
| Slaves to the Last Breath | -33% construction time | +50% construction time |
| Black Death | immune to attrition | disease attrition |
| Red Pox | +4 public order | -6 public order |
| Tainted Warp | poison contact effect | -3 melee defence |
| The Thirteenth | +13% weapon strength | -13% weapon strength |
| Horned Rat's Taint | +4 Skaven corruption | +4 Skaven corruption |

Army symptoms also act on settlement garrisons. A target holds one plague at a time; no infection, no effect.

### Strain rot

Each new plague rolls 0 to 3 rots (50 / 30 / 15 / 5%). The rot rides on everything that plague infects for as long as the plague lasts, and each plague keeps its own. An event message lists the rot for both sides; the plague tooltip marks rot lines with "(rot)".

- **Gift of the Horned Rat:** a plus for us, a minus for them (Swift Paws, Rat Fury, Thick Hide, Venom Spit, Fecundity, Plague Tithe, and the rare Blessing of the Horned Rat).
- **Rot in Our Ranks:** a minus for us only (Brittle Bones, The Shakes, Burrow Panic, Sluggishness, Hunger Blight, Gluttony).
- **Reverse Strain:** a minus for us and a different plus for them (Limp and Hardy, Blunt Fangs, Feverish Foes, Empty Purses, Barren Nests, Cowed and Steeled).

Gifts weigh as much as both bad kinds together.

## The Under-Empire

- **Plague Burrows:** a settlement with Clan Pestilens' undercity beneath it spreads plague more easily (+20% infectivity) and catches it again a turn sooner. Updated every turn, and at once when an undercity is dug or lost.
- **Great Cauldron Pox:** for the human Clan Pestilens the Grand Plague Cauldron no longer spills the vanilla Skaven plague but a strengthened one: Skrolk's vanilla plague at about x1.5, plus +10% weapon strength for us and -6 melee defence and -6 public order for the others. The city above the cauldron is re-infected whenever it is free, until it is razed; elsewhere the pox passes like any plague. Plague Priests of every Clan Pestilens faction spread the same pox.

## Install

Copy **`skrolk_plagues.pack`** into the game's `data` folder and enable it in the launcher. For Russian, also add **`!skrolk_plagues_ru.pack`**.

Safe to add to a running campaign: vanilla Skaven plagues already on the map run out on their own.

## Known behaviour

- The mod ships its own copy of the plague window's data file (`ui/cco/dlc25plagues.cco`) and the active plague tooltip. Other mods that replace the same files will conflict.
- No plague carrier agent: Nurgle's cultist rites are not available to Skrolk (Nurgle's cultist crashes the Skaven UI).
- The script writes `skrolkpl_log.txt` next to the game executable.

## Building from source

Requires Python 3.14 and the game installed (the build and the tests read the vanilla `db.pack` and loc packs).

```bash
python -m pip install pytest lupa
python -m pytest
python -m tools.build
```

`python -m tools.build` writes `dist/skrolk_plagues.pack` and `dist/!skrolk_plagues_ru.pack`; `--install` also copies them into the game's `data` folder (close the game first). Game path: `tools/paths.py`.

### How it works

- `tools/feature.py` puts Clan Pestilens in a campaign group with Nurgle's plague UI feature, its own symptom set, faction sets for the positive and negative effects, and Nurgle's direct infection rites at zero infection cost.
- `tools/symptoms.py`, `tools/rots.py`, `tools/under.py` and `tools/cauldron.py` hold the catalogues and build their db rows from vanilla templates; tests check every effect key against the game's tables.
- `src/script/campaign/mod/skrolkpl.lua` reshuffles the grid each turn (the 18 slot links are hard-wired in the engine and recorded in the script), charges food and gold, rolls the strain and puts its rot on every target as a custom effect bundle, keeps the Under-Empire bonus and the cauldron city's pox. Its state is saved with the campaign. Tested through `lupa` against a mock of the campaign API (`tests/lua/mock_game.lua`).
- The translation pack holds only the loc file at the main pack's path; its name sorts first, so the game takes its file.

## Credits

- [RPFM](https://github.com/Frodo45127/rpfm) and its [schemas](https://github.com/Frodo45127/rpfm-schemas) by Frodo45127. The table layouts in `schemas/` come from there.

## License

The mod's code, scripts and texts are released under the [MIT License](LICENSE) © 2026 Skylar92. Total War: WARHAMMER III and its game data, art and mechanics belong to Creative Assembly and Games Workshop; this is an unofficial fan mod and is not endorsed by them.
