import tempfile
import unittest
from pathlib import Path

from tools.generate_patches import render_patch
from tools.validate_traders import validate


class DltxPatchGenerationTests(unittest.TestCase):
    def test_supply_sections_are_dltx_overrides(self):
        output = render_patch({'supplies_1': {'wpn_ak74'}, 'supplies_generic': {'helm_battle'}})
        headers = [line for line in output.splitlines() if line.startswith('![')]
        self.assertEqual(headers, ['![supplies_1]', '![supplies_generic]'])
        self.assertNotIn('\n[supplies_1]', output)
        self.assertNotIn('\n[supplies_generic]', output)

    def test_item_deletion_uses_empty_value(self):
        output = render_patch({'supplies_2': {'wpn_ak74'}})
        self.assertIn('!wpn_ak74 =\n', output)

    def test_section_deletion_is_never_emitted(self):
        output = render_patch({'supplies_3': {'wpn_ak74'}})
        self.assertNotIn('!![', output)

    def test_non_supply_sections_are_rejected(self):
        with self.assertRaises(ValueError):
            render_patch({'trader': {'wpn_ak74'}})


class DltxPatchValidationTests(unittest.TestCase):
    def _fixture(self, patch_text):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        configs = root / 'configs'
        trade = configs / 'items' / 'trade' / 'trade_demo.ltx'
        weapon = configs / 'items' / 'weapons' / 'demo.ltx'
        trade.parent.mkdir(parents=True)
        weapon.parent.mkdir(parents=True)
        trade.write_text('[supplies_1]\nwpn_demo = 1, 1\nammo_demo = 2, 1\n', encoding='utf-8')
        weapon.write_text('[wpn_demo]\nclass = WP_AK74\n[ammo_demo]\nclass = AMMO\n', encoding='utf-8')
        addon = root / 'addon'
        patch_dir = addon / 'items' / 'trade'
        patch_dir.mkdir(parents=True)
        (patch_dir / 'mod_trade_demo_sto_v1.ltx').write_text(patch_text, encoding='utf-8')
        return temp, configs, addon

    def test_valid_override_and_key_removal_pass(self):
        temp, configs, addon = self._fixture('![supplies_1]\n!wpn_demo =\n')
        with temp:
            errors = validate({'items/trade/trade_demo.ltx': [configs / 'items/trade/trade_demo.ltx']},
                              addon, {'wpn_demo': 'weapon'}, {'supplies_1'})
        self.assertEqual(errors, [])

    def test_plain_or_duplicate_supply_headers_fail(self):
        for text in (
            '[supplies_1]\n!wpn_demo =\n',
            '![supplies_1]\n!wpn_demo =\n![supplies_1]\n!wpn_demo =\n',
        ):
            temp, configs, addon = self._fixture(text)
            with temp:
                errors = validate({'items/trade/trade_demo.ltx': [configs / 'items/trade/trade_demo.ltx']},
                                  addon, {'wpn_demo': 'weapon'}, {'supplies_1'})
            self.assertTrue(errors)

    def test_non_target_deletions_fail(self):
        temp, configs, addon = self._fixture('![supplies_1]\n!wpn_demo =\n!ammo_demo =\n')
        with temp:
            errors = validate({'items/trade/trade_demo.ltx': [configs / 'items/trade/trade_demo.ltx']},
                              addon, {'wpn_demo': 'weapon', 'ammo_demo': 'ammo'}, {'supplies_1'})
        self.assertTrue(any('non-target sale item' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
