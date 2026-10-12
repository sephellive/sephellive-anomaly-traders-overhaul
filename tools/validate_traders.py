#!/usr/bin/env python3
"""Strictly validate generated DLTX trader-sale patches against config roots."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

HEADER = re.compile(r'^\s*(!{0,2})\[([^\]]+)\]\s*$')
NORMAL_HEADER = re.compile(r'^\s*\[([^\]]+)\]')
ENTRY = re.compile(r'^\s*([^;!#][^=]*?)\s*=')
DELETE = re.compile(r'^\s*!\s*([^=\s]+)\s*=\s*(.*?)\s*(?:;.*)?$')
SUPPLY = re.compile(r'^supplies_.+$', re.I)
ACCESSORY_CLASSES = {'WP_SCOPE', 'WP_SILEN', 'WP_BINOC', 'WP_MAGAZ'}
OUTFIT_CLASSES = {'EQU_STLK', 'E_STLK', 'E_HLMET'}


def config_roots(roots: list[Path], profile: Path | None, mods: Path | None) -> list[Path]:
    result = []
    for root in roots:
        if (root / 'configs').is_dir():
            result.append(root / 'configs')
        else:
            result.append(root)
    if profile:
        if not mods:
            raise ValueError('--mo2-mods is required with --mo2-profile')
        modlist = profile / 'modlist.txt'
        if not modlist.is_file():
            raise ValueError(f'MO2 profile has no modlist.txt: {profile}')
        for line in modlist.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('+'):
                path = mods / line[1:].strip() / 'gamedata' / 'configs'
                if path.is_dir():
                    result.append(path)
    return list(dict.fromkeys(p.resolve() for p in result))


def parse_ltx(path: Path):
    """Yield (section, parent sections, class name, key/value rows)."""
    section = None
    parents: list[str] = []
    cls = None
    entries: list[tuple[str, str]] = []

    def emit():
        if section is not None:
            return (section, parents, cls, entries)
        return None

    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        match = re.match(r'^\s*!{0,2}\[([^\]]+)\]\s*(?::([^;]*))?\s*(?:;.*)?$', line)
        if match:
            previous = emit()
            if previous:
                yield previous
            section = match.group(1).strip()
            parents = [x.split(';', 1)[0].strip() for x in (match.group(2) or '').split(',')]
            parents = [x for x in parents if x]
            cls = None
            entries = []
            continue
        if section is None:
            continue
        cls_match = re.match(r'^\s*class\s*=\s*([^;\s]+)', line, re.I)
        if cls_match:
            cls = cls_match.group(1).upper()
        entry = ENTRY.match(line)
        if entry:
            key = entry.group(1).strip()
            value = line.split('=', 1)[1].split(';', 1)[0].strip()
            entries.append((key, value))
    previous = emit()
    if previous:
        yield previous


def build_item_categories(roots: list[Path]) -> dict[str, str]:
    definitions: dict[str, tuple[str | None, list[str]]] = {}
    for root in roots:
        items = root / 'items'
        if not items.is_dir():
            continue
        for path in items.rglob('*.ltx'):
            rel = path.relative_to(root).as_posix().casefold()
            for section, parents, cls, _ in parse_ltx(path):
                kind = None
                if '/outfits/' in f'/{rel}' and cls in OUTFIT_CLASSES:
                    kind = 'outfit'
                elif '/weapons/' in f'/{rel}' and cls and cls.startswith('WP_') and cls not in ACCESSORY_CLASSES:
                    kind = 'weapon'
                key = section.casefold()
                old_kind, old_parents = definitions.get(key, (None, []))
                definitions[key] = (kind or old_kind, [p.casefold() for p in parents] or old_parents)

    categories: dict[str, str] = {}

    def resolve(key: str, seen: set[str] | None = None) -> str | None:
        seen = set() if seen is None else seen
        if key in seen or key not in definitions:
            return None
        seen.add(key)
        kind, parents = definitions[key]
        if kind:
            return kind
        for parent in parents:
            inherited = resolve(parent, seen)
            if inherited:
                return inherited
        return None

    for key in definitions:
        kind = resolve(key)
        if kind:
            categories[key] = kind
        elif key.startswith('helm_') or key.endswith('_outfit'):
            categories[key] = 'outfit'
    return categories


def trade_files(roots: list[Path]):
    base: dict[str, list[Path]] = defaultdict(list)
    overlays: list[tuple[str, Path]] = []
    for root in roots:
        trade_dir = root / 'items' / 'trade'
        if not trade_dir.is_dir():
            continue
        for path in trade_dir.rglob('*.ltx'):
            name = path.name.casefold()
            rel = path.relative_to(root).as_posix().casefold()
            if name.startswith('trade_'):
                base[rel].append(path)
            elif name.startswith('mod_trade_'):
                overlays.append((rel, path))
    found = {rel: list(paths) for rel, paths in base.items()}
    unmatched = []
    for rel, path in overlays:
        stem = path.stem.casefold()[len('mod_'):]
        parent = Path(rel).parent
        candidates = [Path(base_rel) for base_rel in base
                      if Path(base_rel).parent == parent
                      and (stem == Path(base_rel).stem.casefold()
                           or stem.startswith(Path(base_rel).stem.casefold() + '_'))]
        if not candidates:
            unmatched.append(rel)
            continue
        target = max(candidates, key=lambda item: len(item.stem)).as_posix().casefold()
        found.setdefault(target, []).append(path)
    return found, unmatched


def is_forbidden(item: str, categories: dict[str, str]) -> bool:
    if item.casefold().startswith('helm_') or item.casefold().endswith('_outfit'):
        return True
    return categories.get(item.casefold()) in {'weapon', 'outfit'}


def validate(configs: dict[str, list[Path]], addon_configs: Path,
             categories: dict[str, str], eligible_sections: set[str]) -> list[str]:
    errors: list[str] = []
    patched: dict[str, dict[str, set[str]]] = {}
    patch_files = sorted(addon_configs.rglob('mod_*_sto_v1.ltx'))
    if not patch_files:
        errors.append(f'No generated patch files found under {addon_configs}')

    for patch in patch_files:
        rel_patch = patch.relative_to(addon_configs).as_posix().casefold()
        if '_sto_v1.ltx' not in patch.name.casefold():
            errors.append(f'{patch}: invalid generated patch filename')
            continue
        original_stem = patch.stem[len('mod_'):-len('_sto_v1')]
        target_rel = (Path(rel_patch).parent / f'{original_stem}.ltx').as_posix().casefold()
        targets = configs.get(target_rel, [])
        if not targets:
            errors.append(f'{patch}: target config does not exist: {target_rel}')

        sections_seen: set[str] = set()
        current = None
        for number, line in enumerate(patch.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not line.strip() or line.lstrip().startswith(';'):
                continue
            header = HEADER.match(line)
            ordinary_header = NORMAL_HEADER.match(line)
            if header:
                marker, section = header.groups()
                sec_key = section.casefold()
                if sec_key not in eligible_sections:
                    errors.append(f'{patch}:{number}: patch section is not a supply section or inherited supply source: {section}')
                if marker != '!':
                    errors.append(f'{patch}:{number}: expected DLTX override header ![{section}]')
                if sec_key in sections_seen:
                    errors.append(f'{patch}:{number}: duplicate DLTX section [{section}]')
                sections_seen.add(sec_key)
                current = sec_key
                if targets and not any(sec_key in {s.casefold() for s, _, _, _ in parse_ltx(t)} for t in targets):
                    errors.append(f'{patch}:{number}: target section does not exist: [{section}]')
                patched.setdefault(target_rel, {}).setdefault(sec_key, set())
                continue
            if ordinary_header:
                errors.append(f'{patch}:{number}: ordinary section header is invalid; use ![{ordinary_header.group(1)}]')
                current = ordinary_header.group(1).casefold()
                continue
            deletion = DELETE.match(line)
            if not deletion or current is None:
                errors.append(f'{patch}:{number}: invalid DLTX delete-line syntax')
                continue
            key, value = deletion.groups()
            if value:
                errors.append(f'{patch}:{number}: deleted key must use an empty value: !{key} =')
            if key.casefold() in patched.setdefault(target_rel, {}).setdefault(current, set()):
                errors.append(f'{patch}:{number}: duplicate deletion for [{current}] {key}')
            patched[target_rel][current].add(key.casefold())

    forbidden_rows = 0
    scanned_supply_rows: set[tuple[str, str, str]] = set()
    for rel, paths in configs.items():
        for path in paths:
            for section, _, _, entries in parse_ltx(path):
                if section.casefold() not in eligible_sections:
                    continue
                for key, _ in entries:
                    row = (rel, section.casefold(), key.casefold())
                    scanned_supply_rows.add(row)
                    if is_forbidden(key, categories):
                        forbidden_rows += 1
                        if key.casefold() not in patched.get(rel, {}).get(section.casefold(), set()):
                            errors.append(f'{path}: [{section}] {key} remains without a DLTX delete')

    deleted_rows = {(rel, sec, key) for rel, sections in patched.items() for sec, keys in sections.items() for key in keys}
    for rel, sec, key in deleted_rows:
        if (rel, sec, key) not in scanned_supply_rows:
            errors.append(f'{rel}: [{sec}] {key} does not exist in the target supply configs')
        elif not is_forbidden(key, categories):
            errors.append(f'{rel}: [{sec}] {key} is a non-target sale item and must not be removed')

    print('Trader DLTX validation')
    print('-----------------------')
    print(f'Trade config paths scanned: {len(configs)}')
    print(f'Generated patch files checked: {len(patch_files)}')
    print(f'Forbidden supply rows checked: {forbidden_rows}')
    print(f'DLTX rows deleted: {len(deleted_rows)}')
    print(f'Validation errors: {len(errors)}')
    if errors:
        print('FAIL')
        print('\n'.join(errors))
        return errors
    print('PASS (config-level only; in-engine smoke test is still required)')
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-root', action='append', required=True, type=Path,
                        help='Unpacked Anomaly config root or an addon configs root; repeat as needed')
    parser.add_argument('--mo2-profile', type=Path)
    parser.add_argument('--mo2-mods', type=Path)
    parser.add_argument('--addon-configs', required=True, type=Path)
    args = parser.parse_args()
    try:
        roots = config_roots(args.config_root, args.mo2_profile, args.mo2_mods)
        configs, unmatched = trade_files(roots)
        if not configs:
            raise ValueError('No trade_*.ltx or mod_trade_*.ltx files were found')
        categories = build_item_categories(roots)
        section_parents: dict[str, set[str]] = defaultdict(set)
        for paths in configs.values():
            for path in paths:
                for section, parents, _, _ in parse_ltx(path):
                    section_parents[section.casefold()].update(p.casefold() for p in parents)
        eligible_sections = {section for section in section_parents if section.startswith('supplies_')}
        pending = list(eligible_sections)
        while pending:
            for parent in section_parents.get(pending.pop(), set()):
                if parent not in eligible_sections:
                    eligible_sections.add(parent)
                    pending.append(parent)
        orphaned_forbidden = []
        for rel in unmatched:
            for root in roots:
                path = root / rel
                if not path.is_file():
                    continue
                for section, _, _, entries in parse_ltx(path):
                    if section.casefold() in eligible_sections:
                        for key, _ in entries:
                            if is_forbidden(key, categories):
                                orphaned_forbidden.append(f'{rel}: [{section}] {key}')
        if orphaned_forbidden:
            raise ValueError('Unmatched active DLTX overlays contain forbidden sale rows: ' + '; '.join(orphaned_forbidden))
        if unmatched:
            print(f'Checked {len(unmatched)} unmatched active overlay(s); none add forbidden gear.')
        return 1 if validate(configs, args.addon_configs, categories, eligible_sections) else 0
    except (OSError, ValueError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
