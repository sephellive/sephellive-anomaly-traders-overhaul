# Trader System Analysis — Hotfix V1

## Scope and extraction

V1 targets **vanilla S.T.A.L.K.E.R. Anomaly 1.5.3 weapon and outfit definitions**. Weapon packs and additional outfit packs are out of scope; installed MO2 trade overlays were still inspected for conflicts and extra trade targets.

The original `Anomaly/db/configs/configs.db0` and `scripts.db0` archives were unpacked with the installed `Anomaly/tools/converter.exe`, following the command pattern in `Anomaly/tools/db_unpacker.bat`. Output went to `D:\AnomalyHope\_sto_vanilla_audit`, outside the game's `gamedata`. The archives were read only. The audit inspected 37 LTX files under `configs/items/trade/`, 247 under `configs/items/weapons/`, and 52 under `configs/items/outfits/`; the full path list is in [VANILLA_AUDIT_FILES.txt](VANILLA_AUDIT_FILES.txt). Three relevant runtime scripts were also inspected: `scripts/trade_manager.script`, `scripts/xr_logic.script`, and `scripts/ui_inventory.script`.

## Trade config structure and runtime selection

All standard vanilla `trade_*.ltx` files in the extracted trade directory were examined, along with the trade presets and buy/sell support config. Traders commonly include `presets\\trade_discounts.ltx` and `presets\\trade_presets.ltx`. Supply sections include numbered tiers and `supplies_generic`; tiers can inherit the preceding tier or `common_stock`. The audit followed supply-section inheritance and inspected the referenced definitions. The shared `common_stock` section was empty in the unpacked vanilla preset. Other sections such as `[weapons]` and `[outfits_all]` are trade/buy-side groups, not trader supply rows, and are not modified.

Runtime trade code selects a trader config and calls `npc:buy_supplies(config, section)`; the scripts inspected do not implement a category-based dynamic filter for prohibited gear. Therefore the patches cover the explicit prohibited entries in each discovered supply section and its supply inheritance chain. Configs introduced later by other mods need to be scanned and patches regenerated.

## Active MO2 profile and conflict review

The active profile was `ModOrganizer/profiles/Anomaly Hope`, with active mods read from its `modlist.txt` and config roots under `ModOrganizer/mods`. Existing trade overlays were compared with their matching base configs and generated targets. One active BHSRO overlay for `trade_stalker_cashier` had no corresponding base trader config in the unpacked game or installed mod roots; it only lists medicine in its supply tiers and adds no prohibited gear, so no orphan target patch was invented. The generator reports unmatched overlays and fails if one contains a prohibited sale row. The validation run covered 36 effective trade config paths and detected no conflicting forbidden gear from this orphan overlay.

## DLTX operation

To modify an existing supply section, generated patches use an override header such as `![supplies_1]`, followed by item-key deletion lines such as `!wpn_ak74 =`. A plain `[supplies_1]` creates an unmarked duplicate and caused the reported `CInifile::StashCurrentSection` startup error. Patches remove individual sale rows only; they never delete the entire supply section with `!![section]` and never copy/replace vanilla trade files. Trader buy configuration and all game-wide item definitions remain untouched.

## Classification, preservation, and results

Definitions were classified from the vanilla weapons and outfits configs, including section inheritance and `class` metadata. Weapon sale classes are removed while weapon accessories (scopes, suppressors, binoculars, magazines), ammunition, parts, and repair items are retained. Outfit, armor, and helmet classes/definitions are removed from supplies. The validator checks the generated row deletions against scanned supply sections, validates target paths and section names, rejects duplicate/plain supply headers and malformed operations, and confirms protected categories are not accidentally deleted.

Regeneration produced 28 DLTX overlays with 2,116 unique delete rows. Validation checked 2,145 prohibited sale-row occurrences across 36 trade config paths and reported zero errors. Seven regression tests cover override headers, key-delete syntax, invalid duplicates, and target/protected-item behavior. These are **config-level results only**; they do not demonstrate that the game engine loads the patches or prove the acceptance criterion in-game.

## Remaining runtime verification

No automated game startup harness was available. The new-game startup and trader stock criterion still require manual verification with the final MO2 profile: start a new game, check traders across factions and supply levels, confirm preserved categories, and repeat after restock. Do not treat the textual validator as a successful engine smoke test.

## Re-audit after profile changes

DLTX cannot automatically discover future item definitions or trader configs. When adding/updating trade, weapon, or outfit mods, unpack current game configs, inspect active MO2 trade overlays, regenerate patches, run `tools/validate_traders.py`, and review unmatched overlays before installing the changed profile. V1 does not claim universal weapon-pack compatibility.
