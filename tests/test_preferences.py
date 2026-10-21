import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from preferences import last_rom, remember_rom, preferences_path


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, LOCALAPPDATA=self.folder.name)
        self.environment.start()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.environment.stop)

    def test_missing_and_malformed_preferences(self):
        self.assertIsNone(last_rom())
        target = preferences_path(); target.parent.mkdir(parents=True)
        for content in ('broken', '[]', 'null', '{"last_rom": 4}', '{"last_rom":"relative.sfc"}'):
            target.write_text(content,encoding='utf-8')
            self.assertIsNone(last_rom())

    def test_remembers_absolute_unicode_path(self):
        path = Path(self.folder.name)/'My games é'/'Original USA.zip'
        self.assertTrue(remember_rom(path))
        self.assertEqual(last_rom(),str(path.resolve()))

    def test_preserves_other_preferences(self):
        target=preferences_path();target.parent.mkdir(parents=True)
        target.write_text('{"other":true}',encoding='utf-8')
        remember_rom(Path(self.folder.name)/'game.sfc')
        self.assertTrue(json.loads(target.read_text())['other'])

    def test_failed_atomic_write_preserves_previous_path(self):
        first=Path(self.folder.name)/'first.sfc'
        remember_rom(first)
        with patch('preferences.os.replace',side_effect=PermissionError('locked')):
            self.assertFalse(remember_rom(Path(self.folder.name)/'second.sfc'))
        self.assertEqual(last_rom(),str(first.resolve()))
        self.assertEqual(list(preferences_path().parent.iterdir()),[preferences_path()])
