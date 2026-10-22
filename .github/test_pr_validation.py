import contextlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import call, patch

import pr_validation


class ModValidationTests(unittest.TestCase):
    def setUp(self):
        self.properties = {
            (key, None): (value, line)
            for line, (key, value) in enumerate({
                'id': 'blur',
                'version': '2',
                'github': 'HTTPS://GitHub.COM/RisPNG/',
                'author': 'A',
                'name': 'Blur',
                'description': 'Blur windows',
            }.items(), start=1)
        }
        self.existing = {'id': 'blur', 'github': 'https://github.com/rispng', 'author': 'Old name'}
        self.authors = {'https://github.com/rispng': {'author': 'Old name'}}
        for name, value in [
            ('get_mod_author_data', self.authors),
            ('get_existing_mod_metadata', self.existing),
            ('get_existing_mod_versions', ['1']),
        ]:
            mock = patch.object(pr_validation, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def test_owned_mod_accepts_profile_spelling_and_display_name_changes(self):
        validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), self.properties, 'RisPNG')
        self.assertEqual(validator.validate_all(), 0)

    def test_different_owner_or_repository_url_is_rejected(self):
        for github in ['https://github.com/another-owner', 'https://github.com/RisPNG/repository']:
            with self.subTest(github=github):
                self.properties[('github', None)] = (github, 3)
                validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), self.properties, 'RisPNG')
                self.assertGreater(validator.validate_all(), 0)

    def test_twitter_alias_case_and_trailing_slash_preserve_verified_identity(self):
        self.existing['twitter'] = 'https://twitter.com/example'
        self.authors['https://github.com/rispng']['twitter'] = 'https://twitter.com/example'
        self.properties[('twitter', None)] = ('HTTPS://X.COM/Example/', 7)
        validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), self.properties, 'RisPNG')
        self.assertEqual(validator.validate_all(), 0)
        self.properties[('twitter', None)] = ('https://x.com/another_owner', 7)
        validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), self.properties, 'RisPNG')
        self.assertGreater(validator.validate_all(), 0)

    def test_required_metadata_and_unique_versions_remain_enforced(self):
        for key, value in [('description', ''), ('id', 'wrong-file'), ('version', '1')]:
            with self.subTest(key=key):
                properties = self.properties | {(key, None): (value, 1)}
                validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), properties, 'RisPNG')
                self.assertGreater(validator.validate_all(), 0)

    def test_metadata_can_follow_a_source_comment(self):
        source = '// Source notes\n\n// ==WindhawkMod==\n// @id blur\n// ==/WindhawkMod==\n'
        properties, warnings = pr_validation.get_mod_file_metadata(io.StringIO(source))
        self.assertEqual(warnings, 0)
        self.assertEqual(properties[('id', None)][0], 'blur')

    def test_readme_comment_accepts_inline_content_but_requires_a_complete_block(self):
        path = Path('mods/blur.wh.cpp')
        source = '// ==WindhawkModReadme==\n/*Useful notes*/\n// ==/WindhawkModReadme==\n'
        self.assertEqual(pr_validation.validate_readme(path, source), 0)
        self.assertGreater(pr_validation.validate_readme(path, source.replace('*/', '')), 0)

    def test_supported_architectures_are_accepted_and_unknown_ones_are_rejected(self):
        for architecture, valid in [('amd64', True), ('arm64', True), ('unknown', False)]:
            with self.subTest(architecture=architecture):
                properties = self.properties | {('architecture', None): (architecture, 7)}
                validator = pr_validation.ModMetadataValidator(Path('mods/blur.wh.cpp'), properties, 'RisPNG')
                self.assertEqual(validator.validate_all() == 0, valid)

    def test_comments_are_accepted_and_invalid_callback_signatures_are_rejected(self):
        path = Path('mods/blur.wh.cpp')
        source = '// Do not use Wh_SetFunctionHookT\n/* BOOL Wh_ModInit(int invalid); */\nBOOL Wh_ModInit() { return TRUE; }\n'
        self.assertEqual(pr_validation.validate_source_characters(path, source), 0)
        self.assertEqual(pr_validation.validate_callback_signatures(path, source), 0)
        self.assertGreater(pr_validation.validate_callback_signatures(path, 'BOOL Wh_ModInit(int invalid) {}'), 0)
        self.assertGreater(pr_validation.validate_source_characters(path, 'hidden\u200btext'), 0)

    def test_settings_schema_accepts_values_and_rejects_invalid_types(self):
        path = Path('mods/blur.wh.cpp')
        for value, valid in [('true', True), ('{nested: value}', False)]:
            with self.subTest(value=value):
                source = f'// ==WindhawkModSettings==\n/*\n- enabled: {value}\n*/\n// ==/WindhawkModSettings==\n'
                warnings = pr_validation.validate_settings_yaml(path, source)
                self.assertEqual(warnings == 0, valid)

    def test_pull_request_validates_each_mod_and_ignores_other_files(self):
        paths = ['mods/blur.wh.cpp', 'README.md', 'mods/second.wh.cpp']
        with patch.dict(os.environ, {
            'PR_AUTHOR': 'RisPNG',
            'ALL_CHANGED_AND_MODIFIED_FILES': json.dumps(paths),
        }), patch.object(pr_validation.sys, 'argv', ['pr_validation.py']), patch.object(
            pr_validation, 'validate_mod_file', return_value=0,
        ) as validate, patch.object(pr_validation, 'get_mod_symbols', return_value=[]):
            pr_validation.main()
        self.assertEqual(validate.call_args_list, [
            call(Path('mods/blur.wh.cpp'), 'RisPNG'),
            call(Path('mods/second.wh.cpp'), 'RisPNG'),
        ])


if __name__ == '__main__':
    unittest.main()
