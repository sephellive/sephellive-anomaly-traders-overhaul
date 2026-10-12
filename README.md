# Sephellive Traders Overhaul

## V1

Removes finished weapons, outfits, armor, exoskeletons, and helmets from NPC trader sale inventories in **S.T.A.L.K.E.R. Anomaly 1.5.3**.

### Removed from trader sale

- Finished weapons, including melee weapons
- Armor and outfits, including exoskeletons
- Helmets

### Still sold normally

- Ammunition and magazines
- Scopes, suppressors, and other weapon attachments
- Weapon parts and repair items
- Medical items, food, tools, and general supplies

## Requirements

- S.T.A.L.K.E.R. Anomaly 1.5.3
- An Anomaly executable with DLTX support (modded executable)
- Mod Organizer 2 recommended

## Installation

Install the folder as a normal MO2 mod and enable it. Place it after the trader/weapon mods whose supply files were analyzed so its delete-line patches are applied late. Generated patches target the config paths they were built from; regenerate after installing or updating mods that add trader supply files or new sale entries.

## Patching method

This addon uses DLTX `.ltx` delete-line operations (`!item =`) in `mod_*.ltx` overlays. It does not replace vanilla or third-party trade files and does not change trader buy lists, global item definitions, prices, restock, loot, or NPC loadouts. No Lua runtime filtering is used.

Generated patches cover the Anomaly 1.5.3 database configs and trade LTX files found in the analyzed MO2 profile at generation time. To regenerate after changing the profile, unpack the current Anomaly config database to a folder containing `configs/`, then run:

```powershell
python tools/generate_patches.py --config-root PATH_TO_UNPACKED_ANOMALY --mo2-profile PATH_TO_PROFILE --mo2-mods PATH_TO_MO2_MODS --output gamedata/configs
python tools/validate_traders.py --trade-root PATH_TO_UNPACKED_ANOMALY --catalog-root PATH_TO_UNPACKED_ANOMALY --mo2-profile PATH_TO_PROFILE --mo2-mods PATH_TO_MO2_MODS --addon-configs gamedata/configs
```

The validator checks that prohibited entries identified from item definitions have matching removal patches. Review any new mod-specific item definitions that use unconventional config paths or names.

## Known limitations

DLTX does not automatically discover or filter unknown items introduced by future mods. New trade files and new supply entries require a patch regeneration and a validation run. This repository contains generated coverage for the analyzed install; it cannot guarantee coverage of mods not present during that scan. Classification uses item config location and class/inheritance metadata, so mod-specific unconventional item definitions may need a small extension to the generator's classifier.

## Manual smoke test

After enabling the addon, open several traders from different factions and ranks, inspect every available supply tier, and confirm weapons, outfits, and helmets are absent while ammunition, attachments, and repair supplies remain. Repeat after a restock and after reloading a save.
