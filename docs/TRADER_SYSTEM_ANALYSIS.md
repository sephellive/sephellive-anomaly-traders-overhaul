# Trader System Analysis

## Scope and sources

The target is Anomaly 1.5.3 trader sale inventories. The audit unpacked the installed `Anomaly/db/configs/configs.db0` to a temporary audit directory and inspected the bundled `configs/items/trade/trade_*.ltx` files. The MO2 `mods` directory contains additional trade overlays, including BHSRO supply sections and a melee trade rework. The generated overlays were based on those installed config roots at generation time.

## Relevant config model

Trader goods are declared in supply sections (for example `[supplies_1]`, `[supplies_3]`, and `[supplies_generic]`) in the trader trade LTX files. Each item is a key in a supply section; a line such as `!akvatab = 1, 0.75` removes that sale row. Other trade settings and buy lists are separate keys/sections and are left untouched. Multiple supply levels therefore need individual entry removals.

The installed inventory includes named traders and generic/faction supply templates (35 vanilla trade files found in the unpacked database) plus installed-mod trade LTX files. This static scope does not assert runtime-generated/future mod configs are covered.

## DLTX support and operation

Anomaly's DLTX-capable modded executable supports delete-line operations using `!<key> =` in an overlay section. The installed BHSRO config uses this same syntax (`!akvatab = ...`) in a trade LTX overlay; the configured engine executable must still be DLTX-capable. A distinct `!![section]` operation deletes an entire section, and is intentionally not used here. The addon deletes individual supply item rows only.

Patch filenames use `mod_<target-basename>_sto_v1.ltx` and reside at the target LTX's relative config path. They contain only supply sections and removal directives. Source files are never copied or replaced by the addon.

## Classification and limits

The generator follows item section inheritance and the engine `class` field. It treats weapon classes as saleable weapons while excluding `WP_SCOPE`, `WP_SILEN`, and `WP_BINOC`; outfits and helmets use the `EQU_STLK`, `E_STLK`, and `E_HLMET` classes. Helmet and `_outfit` section names are also handled when a definition is missing. It deliberately does not treat every `wpn_*` key as a finished weapon: ammunition, magazines, scopes, suppressors, parts, and repair supplies must remain. Gear-like unresolved entries are listed by the validator for review, because DLTX has no category-aware wildcard deletion or future-mod runtime filter.

For the analyzed profile, generation produced 2,116 unique DLTX sale-row deletions in 28 overlays. Validation scanned 52 vanilla/active-mod trade config paths and checked 2,145 prohibited sale-row occurrences across supply tiers; it found zero missing deletes and zero unresolved gear-like keys after classification. The validation also rejects patches that delete non-target or unclassified item types.

New/changed trade config roots must be scanned again after adding mods. The generator should be run against the Anomaly unpacked config root and each active mod's `gamedata/configs` root in MO2 priority order. Review unresolved entries, regenerate overlays, and run the validator before considering the new mod set covered.

## Preserved behavior

Only NPC sale supply rows are targeted. The addon does not change trader buy configuration, prices, item definitions, NPC equipment, loot, restock behavior, or any Lua scripts. It cannot perform the requested in-game smoke test in this workspace, so the manual checks are listed in the README.
