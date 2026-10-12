#!/usr/bin/env python3
"""Generate DLTX sale-row removals from Anomaly and installed mod config roots."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

SECTION = re.compile(r'^\s*\[([^\]]+)\]')
ENTRY = re.compile(r'^\s*([^;!#][^=]*?)\s*=')

def parse_sections(path: Path):
    section = None
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        m = re.match(r'^\s*\[([^\]]+)\]\s*(?::(.*))?$', line)
        if m:
            section = m.group(1).strip()
        elif section:
            m = ENTRY.match(line)
            if m:
                yield section, m.group(1).strip()

def parse_definitions(path: Path):
    section = None
    parents = []
    cls = None
    def emit():
        if section:
            yield section, parents, cls
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        m = re.match(r'^\s*\[([^\]]+)\]\s*(?::(.*))?$', line)
        if m:
            yield from emit()
            section = m.group(1).strip()
            parents = [x.split(';', 1)[0].strip() for x in (m.group(2) or '').split(',') if x.split(';', 1)[0].strip()]
            cls = None
        elif section and (m := re.match(r'^\s*class\s*=\s*([^;\s]+)', line, re.I)):
            cls = m.group(1).upper()
    yield from emit()

def item_kind_map(config_roots: list[Path]) -> dict[str, str]:
    defs = {}
    for configs in config_roots:
        for p in (configs / 'items').rglob('*.ltx'):
            rel = p.relative_to(configs).as_posix().casefold()
            for sec, parents, cls in parse_definitions(p):
                kind = 'outfit' if '/outfits/' in f'/{rel}' and cls in {'EQU_STLK', 'E_STLK', 'E_HLMET'} else None
                if '/weapons/' in f'/{rel}' and cls and cls.startswith('WP_') and cls not in {'WP_SCOPE','WP_SILEN','WP_BINOC'}:
                    kind = 'weapon'
                key = sec.casefold()
                old_kind, old_parents = defs.get(key, (None, []))
                defs[key] = (kind or old_kind, [x.casefold() for x in parents] or old_parents)
    result = {}
    def resolve(key, seen=None):
        seen = set() if seen is None else seen
        if key in seen or key not in defs: return None
        seen.add(key)
        kind, parents = defs[key]
        if kind: return kind
        for parent in parents:
            found = resolve(parent, seen)
            if found: return found
        return None
    for key in defs:
        kind = resolve(key)
        if kind: result[key] = kind
        elif key.startswith('helm_'):
            result[key] = 'outfit'
        elif key.endswith('_outfit'):
            result[key] = 'outfit'
    return result

def find_config_roots(inputs: list[Path]) -> list[Path]:
    found = []
    for root in inputs:
        if (root / 'configs').is_dir():
            found.append(root / 'configs')
        elif (root / 'gamedata' / 'configs').is_dir():
            found.append(root / 'gamedata' / 'configs')
        elif root.name.casefold() == 'mods':
            found.extend(p for p in root.glob('*/gamedata/configs') if p.is_dir())
        else:
            found.append(root)
    return list(dict.fromkeys(found))

def roots_from_profile(profile: Path, mods_dir: Path) -> list[Path]:
    enabled = []
    for line in (profile / 'modlist.txt').read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('+'):
            folder = mods_dir / line[1:].strip()
            if (folder / 'gamedata' / 'configs').is_dir():
                enabled.append(folder / 'gamedata' / 'configs')
    return enabled

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config-root', action='append', required=True, type=Path,
                    help='Root containing configs/ (repeat in MO2 priority order)')
    ap.add_argument('--output', required=True, type=Path, help='Addon gamedata/configs directory')
    ap.add_argument('--mo2-profile', type=Path, help='MO2 profile folder; scans enabled mods only')
    ap.add_argument('--mo2-mods', type=Path, help='MO2 mods folder used with --mo2-profile')
    args = ap.parse_args()
    for old in args.output.rglob('mod_*_sto_v1.ltx') if args.output.exists() else ():
        old.unlink()
    trade_paths: dict[str, list[Path]] = {}
    roots = find_config_roots(args.config_root)
    if args.mo2_profile:
        if not args.mo2_mods:
            ap.error('--mo2-mods is required with --mo2-profile')
        roots.extend(roots_from_profile(args.mo2_profile, args.mo2_mods))
    for configs in dict.fromkeys(roots):
        for p in configs.rglob('*.ltx'):
            rel = p.relative_to(configs).as_posix().casefold()
            if rel.startswith('items/trade/') and (p.name.casefold().startswith(('trade_', 'mod_trade_'))):
                trade_paths.setdefault(rel, []).append(p)
    classifications = item_kind_map(list(dict.fromkeys(roots)))

    count = 0
    for rel, paths in trade_paths.items():
        # Analyze every installed version of a shared virtual path; emitted deletes
        # are the union so the overlays also remove entries reintroduced upstream.
        deletes: dict[str, set[str]] = {}
        for p in paths:
            for sec, key in parse_sections(p):
                if not sec.casefold().startswith('supplies_'):
                    continue
                category = classifications.get(key.casefold())
                if not category and (key.casefold().startswith('helm_') or key.casefold().endswith('_outfit')):
                    category = 'outfit'
                if category in {'weapon', 'outfit'}:
                    deletes.setdefault(sec, set()).add(key)
        if not deletes:
            continue
        relpath = Path(rel)
        out_dir = args.output / relpath.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f'mod_{relpath.stem}_sto_v1.ltx'
        lines = ['; Generated by Sephellive Traders Overhaul. Do not edit source trade files.']
        for sec in sorted(deletes, key=str.casefold):
            lines.extend(['', f'[{sec}]'])
            lines.extend(f'!{key} =' for key in sorted(deletes[sec], key=str.casefold))
            count += len(deletes[sec])
        out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Generated {count} unique sale-row deletions across {len(trade_paths)} trade config paths.')

if __name__ == '__main__':
    main()
