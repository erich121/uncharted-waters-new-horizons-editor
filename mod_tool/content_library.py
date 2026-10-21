"""Managed local content storage. Entries are self-contained, never ROM paths."""
import copy
import json
import os
import uuid
from pathlib import Path

FORMAT = 'new-horizons-library'
MAX_BYTES = 16 * 1024 * 1024


def protected_collection(name):
    return isinstance(name, str) and name.strip().casefold() in ('stock game', 'stock ships', 'stock discoveries')


def new_id():
    return str(uuid.uuid4())


def stock_id(slot):
    return f'stock-ship:{slot:02d}'


def valid_id(value):
    if not isinstance(value, str):
        return False
    if value in [stock_id(i) for i in range(25)]+[f'stock-discovery:{i:02d}'for i in range(98)]+[f'stock-item:{i:02d}'for i in range(100)]:
        return True
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def validate_ship(entry, rom):
    from backend import decode, validate, ports
    from portraits import unpack
    keys = {'kind', 'id', 'version', 'ship', 'family', 'portrait'}
    if not isinstance(entry, dict) or type(entry.get('version')) is not int or entry['version'] not in (1, 2, 3) or set(entry) != (keys | {'availability','description'} if entry['version'] == 3 else keys | {'availability'} if entry['version'] == 2 else keys) or entry['kind'] != 'ship' or not valid_id(entry['id']) or (entry['id'].startswith('stock-')and not entry['id'].startswith('stock-ship:')):
        raise ValueError('Unsupported Library ship entry.')
    family = entry['family']
    if type(family) is not int or not 0 <= family < 25:
        raise ValueError('Library ship needs an original visual family.')
    row = entry['ship']
    original = decode(rom)[family]
    if not isinstance(row, dict) or set(row) != set(original) - {'id'}:
        raise ValueError('Incomplete Library ship specifications.')
    row = dict(row, id=family)
    validate(row, row)
    for key, low, high in [('industry', 0, 1000), ('factory_guns', 0, 200), ('factory_crew', 1, 500)]:
        if type(row[key]) is not int or not low <= row[key] <= high:
            raise ValueError('Invalid Library ship starting equipment or industry.')
    if row['industry'] % 10 or row['factory_guns'] > row['max_guns'] or row['factory_crew'] < row['min_crew']:
        raise ValueError('Invalid Library ship industry or starting guns.')
    # Preserve the stock game's few over-capacity factory crew allocations.
    if row['factory_crew'] > row['max_crew'] and (row['factory_crew'], row['max_crew']) != (original['factory_crew'], original['max_crew']):
        raise ValueError('Starting crew exceeds the ship limit.')
    unpack([dict(id=0, tiles=entry['portrait'])], 1)
    if entry['version'] == 3:
        __import__('ship_descriptions').validate(entry['description'])
    if entry['version'] >= 2:
        offer = entry['availability']
        if not isinstance(offer, dict) or set(offer) != {'ports', 'industry'}:
            raise ValueError('Invalid Library ship availability.')
        ps, industry = offer['ports'], offer['industry']
        if not isinstance(ps, list) or any(type(p) is not int or not 0 <= p < 100 for p in ps) or len(set(ps)) != len(ps):
            raise ValueError('Choose valid Library build ports without duplicates.')
        if type(industry) is not int or not 0 <= industry <= 1000 or industry % 10 or industry != row['industry']:
            raise ValueError('Invalid Library ship industry requirement.')
        if any(ports(rom)[p]['group'] >= 11 for p in ps):
            raise ValueError('Library build port has no supported shipyard.')
    return copy.deepcopy(entry)


def capture_ship(project, slot, variant=True):
    from backend import decode
    from portraits import pack
    row = project.ships[slot]
    family = project.library_bases.get(slot, slot if slot < 25 else row['base_hull'])
    data = {key: row[key] for key in decode(project.rom)[0] if key != 'id'}
    offer = project.all_offers()[slot]
    data['industry'] = offer['industry']
    identity = project.ship_identities[slot]
    # A user-created variant of a stock model is a separate reusable ship.
    if variant and identity.startswith('stock-ship:'):
        origin = int(identity.split(':')[1])
        from portraits import original_raw
        altered = family != origin or any(data[key] != project.original[origin][key] for key in data if key != 'industry')
        if altered or slot in project.ship_descriptions or project.portrait_raw(slot) != original_raw(project.rom, origin):
            identity = new_id()
    return validate_ship(dict(kind='ship', version=3, id=identity, ship=data, family=family, availability=offer, description=__import__('ship_descriptions').text(project,slot),
                              portrait=pack({0: project.portrait_raw(slot)})[0]['tiles']), project.rom)


class ContentLibrary:
    def __init__(self, rom, root=None):
        self.rom = rom
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
        self.root = Path(root) if root is not None else base / 'New Horizons Editor' / 'Library'
        self.path = self.root / 'library.json'
        self.entries = []
        self.collections = {}
        if self.path.exists():
            self.entries, self.collections = self.read(self.path)
        self._base = copy.deepcopy(self.document())

    def read(self, path):
        path = Path(path)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('Library file exceeds 16 MB.')
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or set(data) != {'format', 'version', 'entries', 'collections'} or data['format'] != FORMAT or type(data['version']) is not int or data['version'] != 1:
            raise ValueError('Unsupported Library file.')
        if not isinstance(data['entries'], list) or len(data['entries']) > 2000:
            raise ValueError('A Library supports up to 2,000 entries.')
        entries = [validate_entry(e, self.rom) for e in data['entries']]
        ids = [e['id'] for e in entries]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate Library content identities.')
        collections = data['collections']
        if not isinstance(collections, dict) or any(not isinstance(k, str) or not k.strip() or len(k) > 80 or not isinstance(v, list) or any(not isinstance(i, str) or i not in ids for i in v) or len(set(v)) != len(v) for k, v in collections.items()):
            raise ValueError('Invalid Library collection.')
        return entries, collections

    def initialize_presets(self, source):
        """Seed only a missing Library; an existing empty Library stays empty."""
        if self.path.exists():
            return False
        from app_defaults import library_document
        from file_safety import atomic_write, file_lock
        document = library_document(source)
        entries = [validate_entry(entry, self.rom) for entry in document['entries']]
        document['entries'] = entries
        payload = (json.dumps(document, indent=2, ensure_ascii=False)+'\n').encode('utf-8')
        if len(payload) > MAX_BYTES:
            raise ValueError('Bundled Library exceeds 16 MB.')
        with file_lock(self.root / '.library.lock'):
            if self.path.exists():
                self.entries, self.collections = self.read(self.path)
                self._base = copy.deepcopy(self.document())
                return False
            atomic_write(self.path, payload)
            self.entries, self.collections = entries, document['collections']
            self._base = copy.deepcopy(self.document())
        self._mark_defaults()
        return True

    def _mark_defaults(self):
        from file_safety import atomic_write
        try:
            atomic_write(self.root / '.bundled-content-version', b'6\n')
        except OSError:
            pass  # Cache only: a later open can safely repeat the migration.

    def migrate_bundled_defaults(self, source):
        """Remove recognizable old defaults and supply protected originals safely."""
        marker = self.root / '.bundled-content-version'
        try:
            if marker.read_text(encoding='utf-8').strip() == '6':
                return False
        except (OSError, UnicodeError):
            pass
        from app_defaults import library_document, previous_library_document
        shipped_previous = previous_library_document()
        old_documents = [library_document(source, _legacy=True), library_document(source, _previous=True), shipped_previous]
        new = library_document(source)
        generated = {name for old in old_documents for name, ids in old['collections'].items()
                     if self.collections.get(name) == ids}
        generated_ids = {i for name in generated for i in self.collections[name]}
        known = {}
        for old in old_documents:
            for entry in old['entries']:
                known.setdefault(entry['id'], []).append(entry)
        retained = {e['id'] for e in new['entries']}
        user_references = {i for name, ids in self.collections.items() if name not in generated for i in ids}
        previous_custom = {e['id']: e for e in shipped_previous['entries'] if not e['id'].startswith('stock-')}
        upgrade_catalogue = any(e == previous_custom.get(e['id']) for e in self.entries)
        recognized_ids = generated_ids | (set(previous_custom) if upgrade_catalogue else set())
        remove = {e['id'] for e in self.entries if e['id'] in recognized_ids and e['id'] not in retained
                  and e['id'] not in user_references and e in known.get(e['id'], [])}
        previous = copy.deepcopy((self.entries, self.collections))
        self.entries = [e for e in self.entries if e['id'] not in remove]
        # Refresh unchanged shipped entries by identity. User-edited versions
        # and their collection references always remain under user control.
        approved = {e['id']: e for e in new['entries']}
        if upgrade_catalogue:
            self.entries = [copy.deepcopy(approved[e['id']])
                            if e['id'] in approved and e in known.get(e['id'], [])
                            else e for e in self.entries]
        self.collections = {name: [i for i in ids if i not in remove] for name, ids in self.collections.items()}
        self.collections = {name: ids for name, ids in self.collections.items() if name not in generated}
        originals = {e['id']: e for e in new['entries'] if e['id'].startswith('stock-')}
        # Older files may have edited an original in place. Keep that edition as
        # a user variant, including its memberships, before restoring the original.
        remapped = {}
        for entry in self.entries:
            identity = entry['id']
            if identity in originals and entry != originals[identity]:
                entry['id'] = new_id()
                remapped[identity] = entry['id']
        if remapped:
            self.collections = {name: [remapped.get(i, i) for i in ids] for name, ids in self.collections.items()}
        for name, stock_ids in new['collections'].items():
            if name in self.collections and self.collections[name] != stock_ids:
                renamed = name + ' (saved collection)'
                suffix = 2
                while renamed in self.collections:
                    renamed = f'{name} (saved collection {suffix})'
                    suffix += 1
                self.collections[renamed] = self.collections.pop(name)
        present = {e['id'] for e in self.entries}
        additions = approved if upgrade_catalogue else originals
        self.entries.extend(copy.deepcopy(entry) for identity, entry in additions.items() if identity not in present)
        self.collections.update(copy.deepcopy(new['collections']))
        if (self.entries, self.collections) == previous:
            self._mark_defaults()
            return False
        try:
            self.save(require_unchanged=True)
        except Exception:
            self.entries, self.collections = previous
            raise
        self._mark_defaults()
        return True

    def restore_presets(self, source):
        """Replace Library content with defaults, preserving the previous backup."""
        from app_defaults import library_document
        document = library_document(source)
        entries = [validate_entry(entry, self.rom) for entry in document['entries']]
        previous = copy.deepcopy((self.entries, self.collections))
        self.entries, self.collections = entries, document['collections']
        try:
            self.save(require_unchanged=True)
        except Exception:
            self.entries, self.collections = previous
            raise
        self._mark_defaults()

    def document(self):
        return dict(format=FORMAT, version=1, entries=self.entries, collections=self.collections)

    def _disk_document(self):
        entries, collections = self.read(self.path) if self.path.exists() else ([], {})
        return dict(format=FORMAT, version=1, entries=entries, collections=collections)

    def reload_if_changed(self):
        # UI refreshes must not discard an in-progress local transaction.
        if self.document() != self._base:
            return False
        current = self._disk_document()
        if current == self._base:
            return False
        self.entries, self.collections = current['entries'], current['collections']
        self._base = copy.deepcopy(current)
        return True

    @staticmethod
    def _merge(base, local, current):
        missing = object()
        result = copy.deepcopy(current)
        for key in dict.fromkeys((*base, *local)):
            before, mine, theirs = base.get(key, missing), local.get(key, missing), current.get(key, missing)
            if mine == before:
                continue
            if theirs != before and theirs != mine:
                raise ValueError('The Library changed in another editor window. Refresh Library and review your change before trying again.')
            if mine is missing:
                result.pop(key, None)
            else:
                result[key] = copy.deepcopy(mine)
        return result

    def save(self, require_unchanged=False):
        from file_safety import atomic_write, file_lock
        with file_lock(self.root / '.library.lock'):
            current = self._disk_document()
            if require_unchanged and current != self._base:
                raise ValueError('The Library changed in another editor window. Refresh Library before deleting it.')
            entries = self._merge({e['id']: e for e in self._base['entries']},
                                  {e['id']: e for e in self.entries},
                                  {e['id']: e for e in current['entries']})
            collections = self._merge(self._base['collections'], self.collections, current['collections'])
            if len(entries) > 2000:
                raise ValueError('A Library supports up to 2,000 entries.')
            if any(identity not in entries for ids in collections.values() for identity in ids):
                raise ValueError('A Library collection changed in another editor window. Refresh Library and review your change.')
            merged = dict(format=FORMAT, version=1, entries=list(entries.values()), collections=collections)
            data = (json.dumps(merged, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
            if len(data) > MAX_BYTES:
                raise ValueError('Library exceeds 16 MB.')
            if self.path.exists():
                atomic_write(self.path.with_suffix('.json.bak'), self.path.read_bytes())
            atomic_write(self.path, data)
            self.entries, self.collections = merged['entries'], merged['collections']
            self._base = copy.deepcopy(merged)

    def clear(self):
        previous=copy.deepcopy((self.entries,self.collections))
        self.entries=[];self.collections={}
        try:self.save(require_unchanged=True)
        except Exception:
            self.entries,self.collections=previous
            raise

    def put(self, entry):
        entry = validate_entry(entry, self.rom)
        previous_entry = next((e for e in self.entries if e['id'] == entry['id']), None)
        if previous_entry is not None and entry['id'].startswith('stock-') and entry != previous_entry:
            raise ValueError('Stock content is read-only. Save your changes as a new variant.')
        entry = keep_discovery_location(previous_entry, entry)
        previous = copy.deepcopy(self.entries)
        self.entries = [e for e in self.entries if e['id'] != entry['id']] + [entry]
        try:
            if len(self.entries) > 2000:
                raise ValueError('A Library supports up to 2,000 entries.')
            self.save()
        except Exception:
            self.entries = previous
            raise

    def archive(self, entry):
        """Preserve an outgoing project copy without replacing a stored revision."""
        entry = validate_entry(entry, self.rom)
        if any(same_archived_discovery(e, entry) for e in self.entries):
            return
        previous = next((e for e in self.entries if e['id'] == entry['id']), None)
        if previous is not None and previous != entry:
            entry['id'] = new_id()
        self.put(entry)

    def import_file(self, path, replace=False):
        entries, collections = self.read(path)
        old_entries, old_collections = copy.deepcopy((self.entries, self.collections))
        known = {e['id']: e for e in self.entries}
        if any(e['id'].startswith('stock-') and e['id'] in known and e != known[e['id']] for e in entries):
            raise ValueError('Import cannot overwrite read-only stock content. Use a new variant identity.')
        collections = dict(collections)
        for name, ids in list(collections.items()):
            if name == 'Stock Game' and name not in self.collections:
                from items import catalogue
                legacy_ids = ([f'stock-ship:{i:02d}' for i in range(25)] +
                              [f'stock-discovery:{i:02d}' for i in range(98)] +
                              [f"stock-item:{row['id']:02d}" for row in catalogue(self.rom)])
                if ids == legacy_ids:
                    del collections[name]  # An older export's redundant default grouping.
                    continue
            if not protected_collection(name):
                continue
            existing = self.collections.get(name)
            if existing is None:
                expected = ([f'stock-ship:{i:02d}' for i in range(25)] if name == 'Stock Ships' else
                            [f'stock-discovery:{i:02d}' for i in range(98)] if name == 'Stock Discoveries' else None)
            else:
                expected = existing
            if ids != expected:
                raise ValueError('Stock collections are read-only.')
        entries = [keep_discovery_location(known.get(e['id']), e) for e in entries]
        if not replace and any(e['id'] in known and e != known[e['id']] for e in entries):
            raise ValueError('This import contains an updated entry. Explicitly allow replacing Library versions; existing projects remain unchanged.')
        known.update({e['id']: e for e in entries})
        if len(known) > 2000:
            raise ValueError('A Library supports up to 2,000 entries.')
        for name, ids in collections.items():
            if name in self.collections and self.collections[name] != ids and not replace:
                raise ValueError('A collection with this name already exists.')
        self.entries = list(known.values())
        self.collections.update(collections)
        try:
            self.save()
        except Exception:
            self.entries, self.collections = old_entries, old_collections
            raise

    def archive_many(self, entries):
        """Preserve a replacement set in one validated, atomic Library save."""
        previous=copy.deepcopy(self.entries)
        known={e['id']:e for e in self.entries}
        for item in entries:
            entry=validate_entry(item,self.rom)
            if any(same_archived_discovery(e,entry)for e in known.values()):
                continue
            if entry['id'] in known and known[entry['id']] != entry:
                entry['id']=new_id()
            known[entry['id']]=entry
        if len(known)>2000:raise ValueError('A Library supports up to 2,000 entries.')
        try:
            self.entries=list(known.values());self.save()
        except Exception:
            self.entries=previous
            raise

    def export_file(self, path, identities=None):
        path = Path(path)
        if path.suffix.lower() != '.nhlib':
            raise ValueError('Export Library content as .nhlib.')
        if path.exists():
            raise ValueError('Choose a new Library filename to preserve previous versions.')
        data = self.document()
        if identities is not None:
            selected = set(identities)
            data = dict(data, entries=[e for e in self.entries if e['id'] in selected],
                        collections={k: v for k, v in self.collections.items() if set(v) <= selected})
        from file_safety import publish_files
        publish_files([(path, (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))])


def validate_entry(entry, rom):
    if isinstance(entry,dict)and entry.get('kind')=='item':
        return __import__('item_library').validate(entry,rom)
    if isinstance(entry, dict) and entry.get('kind') == 'discovery':
        from discovery_content import validate
        return validate(entry, rom)
    return validate_ship(entry, rom)


def keep_discovery_location(previous, entry):
    """An update may revise content, but cannot move an already bound identity."""
    if previous and previous.get('kind')=='item'and (entry.get('kind')!='item'or entry.get('item_id')!=previous['item_id']):raise ValueError('A stored item must keep its original item identity.')
    if previous and previous.get('kind') == 'discovery' and previous.get('version') == 2:
        from discovery_content import bind, target_slot
        if entry.get('kind') != 'discovery':
            raise ValueError('A discovery identity cannot become a ship.')
        return bind(entry, target_slot(previous))
    return entry


def same_archived_discovery(left, right):
    """Legacy format upgrades and archive UUIDs do not create new content."""
    if left.get('kind')!='discovery' or right.get('kind')!='discovery':return False
    from discovery_content import target_slot
    return target_slot(left)==target_slot(right) and all(left[k]==right[k] for k in
        ('name','description','category','difficulty','tiles','palette'))
