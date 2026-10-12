# Sephellive Traders Overhaul

Removes finished weapons, armor, outfits, exoskeletons, and helmets from standard NPC trader sale inventories in **S.T.A.L.K.E.R. Anomaly 1.5.3**. V1 targets vanilla Anomaly weapon and outfit definitions. Additional weapon and outfit packs are outside this release's coverage.

## What changes

- DLTX overlays remove individual prohibited sale rows from every audited supply tier.
- Ammunition, magazines, scopes, suppressors, weapon parts, repair items, and other goods remain available.
- Trader buy lists, prices, item definitions, NPC equipment, loot, restocking, and Lua scripts are unchanged.
- No vanilla or third-party trade config is replaced, and no complete supply section is removed.

## Requirements and installation

- Anomaly 1.5.3 with a DLTX-capable executable.
- Install this repository as a mod in Mod Organizer 2 and enable it after mods that alter trader supply configs.

The included `gamedata` folder is the MO2 install payload. Load the game and inspect traders after installation; config-level validation is not a substitute for an in-game check.

## DLTX and compatibility

Each patch uses a DLTX override header such as `![supplies_1]` and individual delete rows such as `!wpn_example =`. Plain duplicate `[supplies_*]` headers are invalid for this purpose. Whole-section deletion (`!![section]`) is not used. See the [X-Ray Monolith DLTX notes](https://github.com/themrdemonized/xray-monolith) and the [DLTX format guide](https://github.com/robE127/stalker-anomaly-modding-guide/blob/main/docs/config-formats/dltx.md).

DLTX does not automatically filter unknown items or future configs. When adding or updating mods with trader supply files, unpack current Anomaly configs, scan the active MO2 profile, regenerate the patches, then run the validator. Re-generation is required to cover newly added trader configs or sale rows. The complete vanilla audit inventory is in [docs/VANILLA_AUDIT_FILES.txt](docs/VANILLA_AUDIT_FILES.txt); methodology and profile findings are in [docs/TRADER_SYSTEM_ANALYSIS.md](docs/TRADER_SYSTEM_ANALYSIS.md).

## Regeneration and validation

Unpack the game's config database with the installed Anomaly tool (`Anomaly/tools/db_unpacker.bat`, which invokes `converter.exe`) to a directory outside `gamedata`. Then run:

```powershell
python tools/generate_patches.py --config-root PATH_TO_UNPACKED_ANOMALY --mo2-profile PATH_TO_PROFILE --mo2-mods PATH_TO_MO2_MODS --output gamedata/configs
python tools/validate_traders.py --config-root PATH_TO_UNPACKED_ANOMALY --mo2-profile PATH_TO_PROFILE --mo2-mods PATH_TO_MO2_MODS --addon-configs gamedata/configs
python -m unittest discover -s tests -v
```

The validator fails on malformed or duplicate patch sections, missing targets/sections, unpatched prohibited supply entries, deletions of non-target goods, or missing preservation checks. A successful run confirms the scanned config text only; it does not prove the game loads the patch correctly.

## Manual in-game check

Start a new game with the final MO2 profile, open standard traders across factions/ranks and inspect every available tier, then repeat after a restock. Confirm weapons, armor/outfits, and helmets are absent while ammunition, attachments, parts, repair kits, and general goods remain. V1 is not considered runtime-verified until this check completes without DLTX errors.
