#!/usr/bin/env python3
"""Check sale rows in trade configs against generated DLTX removal overlays."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

SECTION = re.compile(r'^\s*\[([^\]]+)\]')
ENTRY = re.compile(r'^\s*([^;!#][^=]*?)\s*=')
DELETE = re.compile(r'^\s*!\s*([^=]+?)\s*=')

def rows(path: Path, pattern):
    sec = None
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        m = re.match(r'^\s*\[([^\]]+)\]\s*(?::(.*))?$', line)
        if m:
            sec = m.group(1).strip()
        elif sec and (m := pattern.match(line)):
            yield sec, m.group(1).strip()

def definitions(path: Path):
    sec = None; parents = []; cls = None
    def emit():
        if sec: yield sec, parents, cls
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        m = re.match(r'^\s*\[([^\]]+)\]\s*(?::(.*))?$', line)
        if m:
            yield from emit()
            sec = m.group(1).strip()
            parents = [x.split(';', 1)[0].strip().casefold() for x in (m.group(2) or '').split(',') if x.split(';', 1)[0].strip()]
            cls = None
        elif sec and (m := re.match(r'^\s*class\s*=\s*([^;\s]+)', line, re.I)):
            cls = m.group(1).upper()
    yield from emit()

def item_kind_map(roots):
    defs = {}
    for configs in roots:
        for p in (configs / 'items').rglob('*.ltx'):
            rel = p.relative_to(configs).as_posix().casefold()
            for sec, parents, cls in definitions(p):
                kind = 'outfit' if '/outfits/' in f'/{rel}' and cls in {'EQU_STLK', 'E_STLK', 'E_HLMET'} else None
                if '/weapons/' in f'/{rel}' and cls and cls.startswith('WP_') and cls not in {'WP_SCOPE','WP_SILEN','WP_BINOC'}:
                    kind = 'weapon'
                key = sec.casefold()
                old_kind, old_parents = defs.get(key, (None, []))
                defs[key] = (kind or old_kind, parents or old_parents)
    result = {}
    def resolve(key, seen=None):
        seen = set() if seen is None else seen
        if key in seen or key not in defs: return None
        seen.add(key); kind, parents = defs[key]
        if kind: return kind
        for parent in parents:
            kind = resolve(parent, seen)
            if kind: return kind
        return None
    for key in defs:
        kind = resolve(key)
        if kind: result[key] = kind
        elif key.startswith('helm_'):
            result[key] = 'outfit'
        elif key.endswith('_outfit'):
            result[key] = 'outfit'
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--trade-root', action='append', required=True, type=Path,
                    help='Root containing configs/ (repeat in MO2 priority order)')
    ap.add_argument('--addon-configs', required=True, type=Path)
    ap.add_argument('--catalog-root', action='append', required=True, type=Path,
                    help='Config root containing item definitions; repeat for active mod roots')
    ap.add_argument('--mo2-profile', type=Path)
    ap.add_argument('--mo2-mods', type=Path)
    args = ap.parse_args()
    if args.mo2_profile:
        if not args.mo2_mods: ap.error('--mo2-mods is required with --mo2-profile')
        active = []
        for line in (args.mo2_profile / 'modlist.txt').read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('+'):
                cfg = args.mo2_mods / line[1:].strip() / 'gamedata' / 'configs'
                if cfg.is_dir(): active.append(cfg)
        args.trade_root.extend(active)
        args.catalog_root.extend(active)
    catalogs = []
    for root in args.catalog_root:
        catalogs.append(root / 'configs' if (root / 'configs').is_dir() else root)
    item_categories = item_kind_map(catalogs)
    violations = []
    scanned = set()
    prohibited = 0
    suspicious_unclassified = set()
    for patch in args.addon_configs.rglob('mod_*_sto_v1.ltx'):
        for sec, key in rows(patch, DELETE):
            kind = item_categories.get(key.casefold())
            if not kind and (key.casefold().startswith('helm_') or key.casefold().endswith('_outfit')):
                kind = 'outfit'
            if kind not in {'weapon', 'outfit'}:
                violations.append(f'{patch}: [{sec}] {key} (patch deletes a non-target or unclassified item)')
    for root in args.trade_root:
        configs = root / 'configs'
        if not configs.is_dir(): configs = root
        for p in configs.rglob('*.ltx'):
            if not p.name.casefold().startswith(('trade_', 'mod_trade_')) or '/trade/' not in p.as_posix().casefold():
                continue
            relstem = p.stem.casefold()
            scanned.add(p.as_posix().casefold())
            for sec, key in rows(p, ENTRY):
                if not sec.casefold().startswith('supplies_'): continue
                category = item_categories.get(key.casefold())
                if not category and (key.casefold().startswith('helm_') or key.casefold().endswith('_outfit')):
                    category = 'outfit'
                if category in {'weapon', 'outfit'}:
                    prohibited += 1
                    expected = f'mod_{p.stem}_sto_v1.ltx'.casefold()
                    patch = args.addon_configs / p.relative_to(configs).parent / expected
                    removed = {(s.casefold(), k.casefold()) for s, k in rows(patch, DELETE)} if patch.exists() else set()
                    if (sec.casefold(), key.casefold()) not in removed:
                        violations.append(f'{p}: [{sec}] {key} (missing DLTX delete line)')
                elif (key.casefold().startswith('wpn_') or key.casefold().endswith(('_suit', '_exoskeleton'))) and not key.casefold().startswith(('wpn_sil_', 'wpn_addon_scope_')) and key.casefold() != 'wpn_binoc_inv':
                    suspicious_unclassified.add(key.casefold())
    print('Trader validation')
    print('-----------------')
    print(f'Trade config files scanned: {len(scanned)}')
    print(f'Prohibited sale entries checked: {prohibited}')
    print(f'Unclassified gear-like item types for review: {len(suspicious_unclassified)}')
    if suspicious_unclassified:
        print('\n'.join(sorted(suspicious_unclassified)))
    print(f'Unpatched entries: {len(violations)}')
    if violations:
        print('FAIL\n' + '\n'.join(violations))
        raise SystemExit(1)
    print('PASS (classified weapon, outfit, and helmet entries all have DLTX removals)')

if __name__ == '__main__':
    main()
