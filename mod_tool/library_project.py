"""Project-owned ship snapshots and identity-preserving Library transactions."""
import copy
from content_library import capture_ship, validate_ship, new_id, stock_id, valid_id


def fleet_identities(project):
    return [[[None if i < 0 else project.ship_identities[i] for i in role] for role in nation]
            for nation in project.fleet_rules]


def remap_fleets(project, references, replacements=None):
    replacements = replacements or {}
    slots = {identity: i for i, identity in enumerate(project.ship_identities)}
    rules = []
    for nation in references:
        result = []
        for role in nation:
            line = []
            for identity in role:
                identity = replacements.get(identity, identity)
                if identity is not None and identity not in slots:
                    raise ValueError('A Custom Fleet still uses the outgoing ship. Choose an explicit replacement before swapping it.')
                line.append(-1 if identity is None else slots[identity])
            result.append(line)
        rules.append(result)
    project.fleet_rules = rules


def restore_stock_ships(project):
    """Restore stock slots while resolving surviving fleet targets by identity."""
    trial = copy.deepcopy(project)
    references = fleet_identities(trial)
    trial.ships = copy.deepcopy(trial.original)
    trial.ship_identities = [stock_id(i) for i in range(25)]
    removed = {identity: None for identity in project.ship_identities if identity not in trial.ship_identities}
    remap_fleets(trial, references, removed)
    trial.custom_ships = False
    trial.library_bases = {}
    trial.ship_descriptions = {}
    trial.portraits = {}
    trial.original_availability = copy.deepcopy(trial.stock_availability)
    trial.shipbuilding_shuffle = __import__('shipbuilding_shuffle').default()
    trial.validate_offer_counts()
    state(trial)
    for key in ('ships', 'ship_identities', 'fleet_rules', 'custom_ships', 'library_bases',
                'ship_descriptions', 'portraits', 'original_availability', 'shipbuilding_shuffle'):
        setattr(project, key, getattr(trial, key))


def restore_ship(project, slot, archive=None):
    """Validate the complete restored state before archiving or changing anything."""
    if type(slot) is not int or not 0 <= slot < len(project.ships):
        raise ValueError('Choose an existing ship to restore.')
    trial = copy.deepcopy(project)
    if slot in project.library_bases and slot < 25:
        original = copy.deepcopy(project)
        original.ships[slot] = dict(project.original[slot])
        original.ship_identities[slot] = stock_id(slot)
        original.library_bases.pop(slot, None)
        original.portraits.pop(slot, None)
        original.ship_descriptions.pop(slot, None)
        original.original_availability[slot] = copy.deepcopy(project.stock_availability[slot])
        load_ship(trial, capture_ship(original, slot), slot, replace_fleet=True)
        trial.library_bases.pop(slot, None)
    elif slot < 25:
        trial.ships[slot] = dict(trial.original[slot])
        trial.ship_identities[slot] = stock_id(slot)
    else:
        ship = trial.ships[slot]
        base = dict(trial.original[ship['base_hull']])
        base.update(id=slot, name=ship['name'], base_hull=ship['base_hull'],
                    ports=ship['ports'], industry=ship['industry'])
        base['max_crew'] = max(base['max_crew'], ((base['factory_crew'] + 9) // 10) * 10)
        base['capacity'] = base['factory_guns'] + base['factory_crew'] + base['factory_cargo']
        trial.ships[slot] = base
    trial.portraits.pop(slot, None)
    trial.ship_descriptions.pop(slot, None)
    if slot < 25:
        trial.original_availability[slot] = copy.deepcopy(trial.stock_availability[slot])
        trial.shipbuilding_shuffle = __import__('shipbuilding_shuffle').default()
    trial.changes()
    trial.availability_changes()
    trial.validate_offer_counts()
    state(trial)
    if archive is not None:
        archive(capture_ship(project, slot))
    for key in ('ships', 'ship_identities', 'library_bases', 'ship_descriptions',
                'portraits', 'fleet_rules', 'custom_ships', 'original_availability', 'shipbuilding_shuffle'):
        setattr(project, key, getattr(trial, key))


def state(project):
    if len(project.ship_identities) != len(project.ships) or len(set(project.ship_identities)) != len(project.ships) or any(not valid_id(i) or i.startswith('stock-discovery:') for i in project.ship_identities):
        raise ValueError('Invalid project ship identities.')
    return dict(identities=list(project.ship_identities), originals=[dict(slot=i, entry=capture_ship(project, i, variant=False)) for i in sorted(project.library_bases) if i < 25],
                fleet_references=fleet_identities(project), discoveries=__import__('discovery_content').state(project))


def read_state(raw, rom, rows, portraits, rules):
    if raw is None:
        return [stock_id(i) if i < 25 else new_id() for i in range(len(rows))], {}
    if not isinstance(raw, dict) or set(raw) not in ({'identities', 'originals', 'fleet_references'}, {'identities', 'originals', 'fleet_references', 'discoveries'}):
        raise ValueError('Invalid project Library state.')
    ids = raw['identities']
    if not isinstance(ids, list) or len(ids) != len(rows) or any(not valid_id(i) or i.startswith('stock-discovery:') for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Invalid or duplicate project ship identities.')
    bases = {}
    if not isinstance(raw['originals'], list):
        raise ValueError('Invalid Library ship overrides.')
    for item in raw['originals']:
        if not isinstance(item, dict) or set(item) != {'slot', 'entry'} or type(item['slot']) is not int or not 0 <= item['slot'] < 25 or item['slot'] in bases:
            raise ValueError('Invalid Library ship slot.')
        i = item['slot']
        entry = validate_ship(item['entry'], rom)
        if entry['id'] != ids[i]:
            raise ValueError('Library ship identity does not match its project slot.')
        from portraits import unpack
        rows[i] = dict(entry['ship'], id=i)
        portraits[i] = unpack([dict(id=0, tiles=entry['portrait'])], 1)[0]
        bases[i] = entry['family']
    expected = [[[None if i < 0 else ids[i] for i in role] for role in nation] for nation in rules]
    if raw['fleet_references'] != expected:
        raise ValueError('Fleet references do not match the selected ship identities.')
    return list(ids), bases


def _place(project, slot, entry, use_locations=False):
    from portraits import unpack
    row = dict(entry['ship'], id=slot)
    offer = copy.deepcopy(entry['availability'] if use_locations and 'availability' in entry else project.all_offers()[slot])
    if slot >= 25:
        row.update(base_hull=entry['family'], ports=offer['ports'], industry=offer['industry'])
        if use_locations and 'availability' in entry:
            from backend import validate_extra
            retained = project.ships[slot]['ports'] if offer['industry'] == project.ships[slot]['industry'] else []
            # Validate after the stock-fit normalization below.
        # Match the added-ship compiler's stricter stock-fit normalization.
        row['max_crew'] = max(row['max_crew'], ((row['factory_crew'] + 9) // 10) * 10)
        if use_locations and 'availability' in entry:
            validate_extra(row, project.economy_rom(), retained)
    else:
        if use_locations and 'availability' in entry:
            project.validate_availability(slot, offer)
            project.original_availability[slot] = offer
        row['industry'] = project.original[slot]['industry']
        project.library_bases[slot] = entry['family']
    project.ships[slot] = row
    project.ship_descriptions.pop(slot,None)
    if 'description' in entry:__import__('ship_descriptions').set_text(project,slot,entry['description'])
    project.ship_identities[slot] = entry['id']
    project.portraits[slot] = unpack([dict(id=0, tiles=entry['portrait'])], 1)[0]


def load_ship(project, entry, slot=None, replace_fleet=False, use_locations=False):
    """Validate on a clone before committing. Existing identity moves via a swap."""
    entry = validate_ship(entry, project.rom)
    if slot is not None and (type(slot) is not int or not 0 <= slot < len(project.ships)):
        raise ValueError('Choose an existing destination ship.')
    trial = copy.deepcopy(project)
    references = fleet_identities(trial)
    existing = next((i for i, identity in enumerate(trial.ship_identities) if identity == entry['id']), None)
    if slot is None:
        if existing is not None:
            raise ValueError('This ship is already in the project. Select its slot to update it, or duplicate it in the Library.')
        slot = trial.add_ship(entry['family'])
    outgoing = trial.ship_identities[slot]
    if existing is not None and existing != slot:
        old = capture_ship(trial, slot)
        # Preserve the identity already used by project fleet references.
        old['id'] = outgoing
        _place(trial, existing, old, use_locations)
    previous_offers = project.all_offers()
    _place(trial, slot, entry, use_locations)
    if previous_offers[:25] != trial.all_offers()[:25]:
        trial.shipbuilding_shuffle = __import__('shipbuilding_shuffle').default()
    replacement = {outgoing: entry['id']} if replace_fleet and existing is None else {}
    remap_fleets(trial, references, replacement)
    trial.custom_ships = True
    trial.changes()
    trial.validate_offer_counts()
    state(trial)
    for key in ('ships', 'ship_identities', 'library_bases', 'ship_descriptions', 'portraits', 'fleet_rules', 'custom_ships', 'original_availability', 'shipbuilding_shuffle'):
        setattr(project, key, getattr(trial, key))
    return slot


def install_originals(data, stock, project):
    """Reuse the verified stock visual-family tables; no new execution hooks."""
    import struct
    from backend import MODEL_BASE, SPEC_BASE
    for slot, family in sorted(project.library_bases.items()):
        if slot >= 25:
            continue
        row = project.ships[slot]
        template = bytearray(stock[MODEL_BASE + family * 25:MODEL_BASE + (family + 1) * 25])
        template[:18] = row['name'].encode('ascii').ljust(18, b'\0')
        template[18] = slot
        template[20] = row['factory_guns']
        struct.pack_into('<HH', template, 21, row['factory_crew'], row['factory_cargo'])
        data[MODEL_BASE + slot * 25:MODEL_BASE + (slot + 1) * 25] = template
        spec = bytearray(stock[SPEC_BASE + family * 12:SPEC_BASE + (family + 1) * 12])
        spec[:6] = bytes([project.original_availability[slot]['industry'] // 10, row['hull'], row['turning'], row['power'], row['max_crew'] // 10, row['min_crew']])
        struct.pack_into('<H', spec, 6, row['capacity'])
        spec[8] = row['max_guns']
        struct.pack_into('<H', spec, 10, row['price_gold'] // 10)
        data[SPEC_BASE + slot * 12:SPEC_BASE + (slot + 1) * 12] = spec
        # Existing expanded builds relocate these two tables.
        size_table = 0x213400 if len(project.ships) > 25 else 0x2B6C9
        dialog_table = 0x200C00 if len(project.ships) > 25 else 0x8FB3F
        data[size_table + slot] = stock[0x2B6C9 + family]
        data[dialog_table + slot * 2:dialog_table + slot * 2 + 2] = stock[0x8FB3F + family * 2:0x8FB41 + family * 2]
