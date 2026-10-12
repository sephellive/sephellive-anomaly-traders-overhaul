# Changelog

## Hotfix V1

- Fixed every generated supply patch to use DLTX override section headers (`![supplies_*]`) and individual delete-key rows.
- Regenerated patches against unpacked Anomaly 1.5.3 configs and the active MO2 profile.
- Added strict config-level checks and regression tests for override syntax, duplicates, target coverage, protected stock, and accidental deletions.
- Documented the vanilla-only V1 scope, extraction method, trader audit, and in-game verification limitation.

## V1

- Added DLTX patches removing finished weapons, armor/outfits, and helmets from detected trader supply rows.
- Added patch generation and validation tools for installed config roots.
