"""Regression checks for Library actions using real editor controls and isolated data."""
import copy
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from app import Editor
from backend import ShipProject
from content_library import ContentLibrary, capture_ship


class LibraryWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            raise unittest.SkipTest('Requires verified stock USA ROM')
        cls.stock = ShipProject(source)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        environment = patch.dict(os.environ, LOCALAPPDATA=str(self.folder))
        environment.start()
        self.addCleanup(environment.stop)
        fixture = ContentLibrary(self.stock.rom)
        fixture.clear()  # Explicit blank fixture, not a fresh install.
        fixture._mark_defaults()
        self.root = tk.Tk()
        self.addCleanup(self.close_editor)
        self.app = Editor(self.root)
        self.root.geometry('1200x850+20+20')
        self.app.project = copy.deepcopy(self.stock)
        self.app.project.custom_ships = True
        self.app.selected = 0
        self.app.show(0)
        self.root.update()
        self.app.cancel_auto_edit()
        self.errors = []
        failures = patch.object(self.app, 'fail', side_effect=lambda error: self.errors.append(str(error)))
        failures.start()
        self.addCleanup(failures.stop)

    def close_editor(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def added_ship(self):
        slot = self.app.project.add_ship()
        self.app.selected = slot
        self.app.show(slot)
        self.root.update()
        self.app.cancel_auto_edit()
        return slot

    def library(self):
        self.app.library.refresh()
        return self.app.library.store

    def test_restore_art_full_yard_rejection_keeps_controls_and_project(self):
        p = self.app.project
        port = p.stock_availability[0]['ports'][0]
        p.update(0, dict(ports=[], industry=0))
        for i in range(1, 25):
            if sum(port in o['ports'] for o in p.all_offers()) >= 16:
                break
            if port not in p.original_availability[i]['ports']:
                p.update(i, dict(ports=p.original_availability[i]['ports']+[port], industry=0))
        self.app.show(0)
        self.app.cancel_auto_edit()
        before = p.manifest()
        self.app.restore_button.invoke()
        self.root.update()
        self.assertEqual(p.manifest(), before)
        self.assertEqual(list(self.app.port_list.curselection()), [])
        self.assertTrue(self.errors and '16-ship' in self.errors[0])

    def test_restore_art_add_button_keeps_custom_template_image(self):
        p = self.app.project
        raw = p.portrait_raw(10)
        custom = bytes([raw[0] ^ 1]) + raw[1:]
        p.set_portrait(10, custom)
        self.app.show(10)
        self.app.cancel_auto_edit()
        self.app.add_button.invoke()
        self.root.update()
        self.assertEqual(self.app.selected, 25)
        self.assertEqual(p.portrait_raw(25), custom)
        self.assertEqual(self.errors, [])

    def test_preset_empty_selection_and_locked_values_are_readable(self):
        from tkinter import ttk
        import custom_preset_view
        custom_preset_view.refresh(self.app)
        self.assertTrue(self.app.preset_entries)
        self.assertEqual(self.app.easy_description.cget('text'), 'Select a preset to load its settings.')
        self.assertEqual(int(self.app.preset_loaded_changes.cget('height')), 3)
        style = ttk.Style(self.root)
        for control in ('TEntry', 'TSpinbox'):
            self.assertEqual(style.lookup(control, 'foreground', ('disabled',)), '#65748a')
        from app import CHANGE_ORANGE
        self.assertEqual(style.lookup('Changed.TSpinbox', 'foreground', ('disabled',)), CHANGE_ORANGE)

    def test_duplicate_from_stock_is_visible_and_selected(self):
        panel = self.app.library
        store = self.library()
        store.restore_presets(self.app.project.source)
        panel.collection.set('Stock Ships')
        panel.refresh()
        panel.search.set('Balsa')
        with patch('tkinter.simpledialog.askstring', return_value='Visible variant'):
            panel.duplicate()
        self.assertEqual(panel.collection.get(), 'All entries')
        self.assertEqual(panel.search.get(), '')
        self.assertEqual(panel.selected()[0]['ship']['name'], 'Visible variant')
        self.assertFalse(panel.selected()[0]['id'].startswith('stock-'))
        self.assertEqual(len(store.collections['Stock Ships']), 25)
        self.assertEqual(self.errors, [])

    def test_same_name_stock_ship_duplicate_is_deletable(self):
        panel = self.app.library
        store = self.library()
        store.restore_presets(self.app.project.source)
        panel.collection.set('Stock Ships')
        panel.refresh()
        panel.search.set('Balsa')
        original = copy.deepcopy(panel.selected()[0])
        count = len(store.entries)
        with patch('tkinter.simpledialog.askstring', return_value=original['ship']['name']):
            panel.duplicate_button.invoke()
        duplicate = copy.deepcopy(panel.selected()[0])
        self.assertEqual(duplicate['ship']['name'], original['ship']['name'])
        self.assertNotEqual(duplicate['id'], original['id'])
        self.assertFalse(duplicate['id'].startswith('stock-'))
        self.assertFalse(panel.delete_button.instate(['disabled']))
        self.assertEqual(len(store.entries), count+1)
        with patch('tkinter.messagebox.askyesno', return_value=True):
            panel.delete_button.invoke()
        self.assertEqual(len(store.entries), count)
        self.assertNotIn(duplicate['id'], {e['id'] for e in store.entries})
        self.assertIn(original, store.entries)
        self.assertEqual(len(store.collections['Stock Ships']), 25)
        reopened = ContentLibrary(self.app.project.rom, store.root)
        self.assertEqual(len(reopened.entries), count)
        self.assertIn(original, reopened.entries)
        panel.collection.set('Stock Ships')
        panel.refresh()
        panel.search.set('Balsa')
        self.assertTrue(panel.delete_button.instate(['disabled']))
        self.assertEqual(self.errors, [])

    def test_save_new_variant_reveals_it_outside_filtered_collection(self):
        panel = self.app.library
        store = self.library()
        store.restore_presets(self.app.project.source)
        self.app.project.ships[0]['name'] = 'Saved variant'
        self.app.show(0)
        self.app.cancel_auto_edit()
        panel.collection.set('Stock Ships')
        panel.refresh()
        panel.source.current(0)
        panel.save_ship()
        self.assertEqual(panel.selected()[0]['ship']['name'], 'Saved variant')
        self.assertEqual(panel.collection.get(), 'All entries')
        self.assertEqual(self.errors, [])

    def test_remove_archives_pending_name_edit(self):
        slot = self.added_ship()
        identity = self.app.project.ship_identities[slot]
        self.app.vars['name'].set('Latest Name')
        self.assertIsNotNone(self.app.auto_timer)
        self.app.remove_button.invoke()
        self.assertEqual(len(self.app.project.ships), 25)
        saved = next(e for e in self.library().entries if e['id'] == identity)
        self.assertEqual(saved['ship']['name'], 'Latest Name')
        self.assertIsNone(self.app.auto_timer)
        self.assertEqual(self.errors, [])

    def test_invalid_pending_edit_prevents_removal(self):
        self.added_ship()
        self.app.vars['hull'].set('invalid')
        self.app.remove_button.invoke()
        self.assertEqual(len(self.app.project.ships), 26)
        self.assertTrue(self.errors)
        self.assertEqual(self.library().entries, [])

    def test_remove_keeps_both_library_revisions(self):
        slot = self.added_ship()
        store = self.library()
        entry = capture_ship(self.app.project, slot)
        store.put(entry)
        price = entry['ship']['price_gold']
        self.app.project.ships[slot]['price_gold'] = price + 10000
        self.app.show(slot)
        self.app.cancel_auto_edit()
        self.app.remove_button.invoke()
        self.assertEqual(len(store.entries), 2)
        self.assertEqual({e['ship']['price_gold'] for e in store.entries}, {price, price + 10000})
        self.assertEqual(next(e for e in store.entries if e['id'] == entry['id']), entry)
        self.assertEqual(self.errors, [])

    def test_archive_failure_keeps_ship(self):
        slot = self.added_ship()
        store = self.library()
        self.app.vars['name'].set('Keep Me')
        with patch.object(store, 'save', side_effect=OSError('Disk full')):
            self.app.remove_button.invoke()
        self.assertEqual(len(self.app.project.ships), 26)
        self.assertEqual(self.app.project.ships[slot]['name'], 'Keep Me')
        self.assertEqual(store.entries, [])
        self.assertEqual(self.errors, ['Disk full'])

    def test_archiving_identical_entry_does_not_duplicate_it(self):
        slot = self.added_ship()
        store = self.library()
        entry = capture_ship(self.app.project, slot)
        store.put(entry)
        store.archive(entry)
        self.assertEqual(store.entries, [entry])

    def test_empty_selected_export_does_not_open_picker_or_export_all(self):
        store = self.library()
        store.put(capture_ship(self.app.project, 0))
        self.app.library.refresh()
        self.app.library.search.set('no matching entries')
        with patch('tkinter.filedialog.asksaveasfilename') as picker:
            self.app.library.export_file()
        picker.assert_not_called()
        menu = self.root.nametowidget(str(self.app.library.footer_buttons[1].cget('menu')))
        self.assertEqual(menu.entrycget(0, 'state'), 'disabled')
        self.app.library.populate_actions()
        self.assertEqual(self.app.library.actions_menu.entrycget(1, 'state'), 'disabled')

    def test_selected_export_and_explicit_whole_export_remain_distinct(self):
        store = self.library()
        for slot in (0, 1):
            store.put(capture_ship(self.app.project, slot))
        self.app.library.refresh()
        selected = self.app.library.selected()[0]['id']
        for all_entries, count in ((False, 1), (True, 2)):
            target = self.folder / ('all.nhlib' if all_entries else 'selected.nhlib')
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)):
                self.app.library.export_file(all_entries)
            data = json.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(len(data['entries']), count)
            if not all_entries:
                self.assertEqual(data['entries'][0]['id'], selected)

    def test_initial_library_failure_can_recover_after_file_repair(self):
        path = self.folder / 'New Horizons Editor' / 'Library' / 'library.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{broken', encoding='utf-8')
        self.app.library.refresh()
        self.assertIsNone(self.app.library.store)
        path.unlink()
        repaired = ContentLibrary(self.app.project.rom)
        repaired.put(capture_ship(self.app.project, 0))
        self.app.library.refresh()
        self.assertEqual(len(self.app.library.store.entries), 1)
        self.assertIsNone(self.app.library.error)
        self.assertEqual(str(self.app.library.save_button.cget('state')), 'normal')

    def test_retry_does_not_overwrite_unreadable_library(self):
        path = self.folder / 'New Horizons Editor' / 'Library' / 'library.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{broken')
        for _ in range(2):
            self.app.library.refresh()
        self.assertIsNone(self.app.library.store)
        self.assertEqual(path.read_bytes(), b'{broken')

    def test_library_search_shortcut_focuses_search_entry(self):
        self.app.switch_section('library')
        self.root.update()
        self.root.focus_force()
        self.app.open_search()
        self.root.update()
        self.assertEqual(self.root.focus_get(), self.app.library.search_entry)


if __name__ == '__main__':
    unittest.main()
