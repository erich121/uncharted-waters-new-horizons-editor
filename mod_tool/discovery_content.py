"""Portable custom discoveries, pool snapshots and private native art dispatch."""
import base64
import copy
from collections import Counter
from functools import lru_cache
from pathlib import Path
from PIL import Image


def stock_id(slot):
    return f'stock-discovery:{slot:02d}'


def decode64(value, size):
    if not isinstance(value, str) or len(value) != ((size + 2) // 3) * 4:
        raise ValueError('Invalid discovery artwork data.')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid discovery artwork encoding.') from error
    if len(raw) != size:
        raise ValueError('Wrong discovery artwork dimensions.')
    return raw


def validate(entry, rom=None):
    from content_library import valid_id
    keys = {'kind', 'id', 'version', 'name', 'description', 'category', 'difficulty', 'tiles', 'palette'}
    if not isinstance(entry, dict) or type(entry.get('version')) is not int or entry['version'] not in (1, 2) or set(entry) != (keys | {'replaces'} if entry['version'] == 2 else keys) or entry['kind'] != 'discovery' or not (valid_id(entry['id']) and not(entry['id'].startswith('stock-')and not entry['id'].startswith('stock-discovery:'))):
        raise ValueError('Unsupported Library discovery.')
    if entry['version'] == 2 and entry['replaces'] not in [stock_id(i) for i in range(98)]:
        raise ValueError('Discovery replacement must identify an original game slot.')
    for key, maximum in [('name', 24), ('description', 226)]:
        text = entry[key]
        if not isinstance(text, str) or not text.strip() or len(text) > maximum or '%' in text or any(not 32 <= ord(c) <= 126 for c in text):
            raise ValueError(f'Discovery {key} needs 1–{maximum} printable English characters, without %.')
    if type(entry['category']) is not int or not 0 <= entry['category'] <= 6 or type(entry['difficulty']) is not int or not 0 <= entry['difficulty'] <= 255:
        raise ValueError('Invalid discovery category or difficulty.')
    decode64(entry['tiles'], 512)
    palette = decode64(entry['palette'], 32)
    if any(palette[i] & 128 for i in range(1, 32, 2)):
        raise ValueError('Discovery palette must use SNES 15-bit colours.')
    return copy.deepcopy(entry)


def target_slot(entry):
    entry = validate(entry)
    identity = entry.get('replaces', entry['id'] if entry['id'].startswith('stock-discovery:') else None)
    return int(identity.rsplit(':', 1)[1]) if identity is not None else None


def bind(entry, slot):
    entry = validate(entry)
    if type(slot) is not int or not 0 <= slot < 98:
        raise ValueError('Choose an original discovery location.')
    existing = target_slot(entry)
    if existing is not None and existing != slot:
        raise ValueError('This discovery is tied to another original game location.')
    return validate(dict(entry, version=2, replaces=stock_id(slot)))


def prepare_replacements(project, entries):
    """Build one atomic replacement set; distinct alternatives may share Library slots."""
    trial = copy.deepcopy(project)
    targets = set()
    for entry in entries:
        slot = target_slot(entry)
        if slot is None:
            raise ValueError('Choose a location for this older discovery before loading it.')
        if slot in targets:
            raise ValueError('Select only one alternative for each original discovery location.')
        targets.add(slot)
        trial.discovery_entries[slot] = bind(entry, slot)
        trial.discovery_identities[slot] = entry['id']
    state(trial)
    return trial


def capture(project, slot):
    from discoveries import catalogue, picture_data, BASE
    if slot in project.discovery_entries:
        entry = project.discovery_entries[slot]
        return validate(dict(entry, version=2, replaces=stock_id(slot))) if entry['version'] == 1 else bind(entry, slot)
    row = catalogue(project.rom)[slot]
    row['description'] = __import__('discovery_rewrites').overrides(project).get(slot, row['description'])
    raw, palette = picture_data(project.rom, slot)
    return validate(dict(kind='discovery', id=project.discovery_identities[slot], version=2, replaces=stock_id(slot),
                         name=row['name'], description=row['description'],
                         category=project.rom[BASE+slot*7+6] & 7, difficulty=row['difficulty'],
                         tiles=base64.b64encode(raw).decode('ascii'), palette=base64.b64encode(palette).decode('ascii')))


@lru_cache(maxsize=256)
def opaque_art(raw, palette):
    """Reserve transparent index zero, including artwork from older projects.

    Keep already-safe stock art byte-identical. Reuse an unused colour slot
    losslessly where possible; otherwise merge the least costly colour into
    its nearest existing colour before moving zero into the freed slot.
    Library/project source artwork is never modified.
    """
    indices = []
    for tile in range(16):
        for y in range(8):
            for x in range(8):
                indices.append(sum(((raw[tile*32+p//2*16+y*2+p%2] >> (7-x)) & 1) << p for p in range(4)))
    counts = Counter(indices)
    if not counts[0]:
        return raw, palette
    colours = [int.from_bytes(palette[i*2:i*2+2], 'little') for i in range(16)]
    free = next((i for i in range(1, 16) if not counts[i]), None)
    mapping = list(range(16))
    if free is None:
        def cost(a, b):
            return counts[a]*sum((((colours[a] >> s) & 31)-((colours[b] >> s) & 31))**2 for s in (0, 5, 10))
        # Never merge into zero: it must be unused in the final native tiles.
        a, b = min(((a, b) for a in range(16) for b in range(1, 16) if a != b), key=lambda pair: (cost(*pair), pair))
        mapping[a] = b
        free = a
    if free:
        mapping[0] = free
        colours[free] = colours[0]
    output = bytearray(512)
    for n, old in enumerate(indices):
        tile, pos = divmod(n, 64)
        y, x = divmod(pos, 8)
        for p in range(4):
            output[tile*32+p//2*16+y*2+p%2] |= ((mapping[old] >> p) & 1) << (7-x)
    return bytes(output), b''.join(c.to_bytes(2, 'little') for c in colours)


def artwork(entry):
    return opaque_art(decode64(entry['tiles'], 512), decode64(entry['palette'], 32))


def picture(entry, scale=4):
    raw, palette = artwork(entry)
    colors = [tuple(((int.from_bytes(palette[i*2:i*2+2], 'little') >> shift) & 31)*255//31 for shift in (0, 5, 10)) for i in range(16)]
    pixels = [None]*1024
    for tile in range(16):
        for y in range(8):
            for x in range(8):
                value = sum(((raw[tile*32+p//2*16+y*2+p%2] >> (7-x)) & 1) << p for p in range(4))
                pixels[(tile//4*8+y)*32+tile%4*8+x] = colors[value]
    image = Image.new('RGB', (32, 32))
    image.putdata(pixels)
    return image.resize((32*scale, 32*scale), Image.Resampling.NEAREST)


def convert_png(path):
    path = Path(path)
    if path.stat().st_size > 32*1024*1024:
        raise ValueError('Choose a PNG smaller than 32 MB.')
    with Image.open(path) as source:
        if source.format != 'PNG' or source.width*source.height > 16_000_000:
            raise ValueError('Choose a PNG with at most 16 million pixels.')
        rgba = source.convert('RGBA').resize((32, 32), Image.Resampling.LANCZOS)
        base = Image.new('RGBA', (32, 32), (255, 255, 255, 255))
        image = Image.alpha_composite(base, rgba).convert('RGB').quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal = image.getpalette()
    palette = bytearray(b'\0\0')  # SNES index zero is transparent.
    for i in range(15):
        rgb = pal[i*3:i*3+3]
        if len(rgb) != 3:
            rgb = [0, 0, 0]
        value = sum((round(c*31/255) & 31) << shift for c, shift in zip(rgb, (0, 5, 10)))
        palette += value.to_bytes(2, 'little')
    indices = list(image.tobytes())
    raw = bytearray(512)
    for tile in range(16):
        for y in range(8):
            for x in range(8):
                value = indices[(tile//4*8+y)*32+tile%4*8+x]+1
                for plane in range(4):
                    raw[tile*32+plane//2*16+y*2+plane%2] |= ((value >> plane) & 1) << (7-x)
    return dict(tiles=base64.b64encode(raw).decode('ascii'), palette=base64.b64encode(palette).decode('ascii'))


def state(project):
    ids = project.discovery_identities
    from content_library import valid_id
    if len(ids) != 98 or len(set(ids)) != 98 or any(not valid_id(i) or i.startswith('stock-ship:') for i in ids):
        raise ValueError('Discovery pool needs 98 distinct content identities.')
    entries = []
    for slot, entry in sorted(project.discovery_entries.items()):
        if type(slot) is not int or not 0 <= slot < 98 or validate(entry)['id'] != ids[slot]:
            raise ValueError('Discovery identity does not match its pool slot.')
        if entry['version'] == 2 and target_slot(entry) != slot:
            raise ValueError('Discovery is assigned outside its original replacement location.')
        entries.append(dict(slot=slot, entry=copy.deepcopy(entry)))
    return dict(identities=list(ids), entries=entries)


def read_state(raw):
    if raw is None:
        return [stock_id(i) for i in range(98)], {}
    if not isinstance(raw, dict) or set(raw) != {'identities', 'entries'} or not isinstance(raw['entries'], list):
        raise ValueError('Invalid discovery pool state.')
    entries = {}
    for item in raw['entries']:
        if not isinstance(item, dict) or set(item) != {'slot', 'entry'} or type(item['slot']) is not int or not 0 <= item['slot'] < 98 or item['slot'] in entries:
            raise ValueError('Invalid or duplicate discovery pool slot.')
        entry = validate(item['entry'])
        entries[item['slot']] = validate(dict(entry, version=2, replaces=stock_id(item['slot']))) if entry['version'] == 1 else bind(entry, item['slot'])
    class Probe:
        pass
    probe = Probe()
    probe.discovery_identities, probe.discovery_entries = raw['identities'], entries
    if not isinstance(raw['identities'], list):
        raise ValueError('Invalid discovery identities.')
    state(probe)
    return list(raw['identities']), entries


def load(project, entry, slot):
    entry = validate(entry)
    if type(slot) is not int or not 0 <= slot < 98:
        raise ValueError('Choose a discovery slot from the 98-entry pool.')
    if entry['version'] == 2:
        if target_slot(entry) != slot:
            raise ValueError('This discovery is tied to another original game location.')
        trial = prepare_replacements(project, [entry])
        project.discovery_entries, project.discovery_identities = trial.discovery_entries, trial.discovery_identities
        return
    existing = next((i for i, identity in enumerate(project.discovery_identities) if identity == entry['id']), None)
    entries = copy.deepcopy(project.discovery_entries)
    ids = list(project.discovery_identities)
    if existing is not None and existing != slot:
        entries[existing] = capture(project, slot)
        ids[existing] = ids[slot]
    entries[slot] = entry
    ids[slot] = entry['id']
    project.discovery_entries, project.discovery_identities = entries, ids
    state(project)


def rows(project):
    from discoveries import catalogue, read_text
    result = catalogue(project.rom)
    for slot, entry in project.discovery_entries.items():
        result[slot].update(name=entry['name'], description=entry['description'], difficulty=entry['difficulty'], required_score=entry['difficulty']+1,
                            category=read_text(project.rom, 0xb0cf7, entry['category']))
    for slot, text in __import__('discovery_rewrites').overrides(project).items():
        result[slot]['description'] = text
    if getattr(project,'discovery_easy',False):
        for row in result:row.update(difficulty=10,required_score=11)
    return result


def install(data, project):
    """Keep the stock 50+10 selector; isolate art, palettes and text per pool slot."""
    entries = project.discovery_entries
    state(project)
    if not entries:
        return
    from expansion import Code, far_jump
    from discoveries import BASE, NAME_POINTERS
    if len(data) == 0x200000:
        data.extend(b'\xff'*0x200000)
        data[0xffd7] = 12
    def write(at, raw):
        if data[at:at+len(raw)] != b'\xff'*len(raw):
            raise ValueError('Discovery storage overlaps another ROM modification.')
        data[at:at+len(raw)] = raw
    flags, pointers = bytearray(98), bytearray(98*3)
    for slot, entry in sorted(entries.items()):
        raw, palette = artwork(entry)
        stream = b'\xfc\x01' + b''.join(b'\xff'+raw[n:n+8] for n in range(0, 512, 8)) + b'\0'
        at = 0x300000+slot*0x400
        write(at, stream)
        pointers[slot*3:slot*3+3] = (0xc00000+at).to_bytes(3, 'little')
        write(0x2f1000+slot*32, palette)
        text = entry['name'].encode('ascii')+b'\0'+entry['description'].encode('ascii')+b'\0'
        at = 0x320000+slot*512
        write(at, text)
        data[NAME_POINTERS+slot*3:NAME_POINTERS+slot*3+3] = (0xc00000+at).to_bytes(3, 'little')
        data[0xebe62+slot*3:0xebe65+slot*3] = (0xc00000+at+len(entry['name'])+1).to_bytes(3, 'little')
        data[BASE+slot*7+5] = entry['difficulty']
        data[BASE+slot*7+6] = (data[BASE+slot*7+6] & 0xf8) | entry['category']
        flags[slot] = 1
    write(0x2f0000, pointers)
    write(0x2f0200, flags)
    # Discovery-only branch: use private graphic/palette IDs for overridden slots.
    native = bytes.fromhex('a3 0e 85 0c 64 0e')
    if data[0x13d95:0x13d9b] != native:
        raise ValueError('Unsupported discovery render branch.')
    c = Code().emit('da a3 10 c9 62 00').branch(0xb0, 'original')
    c.emit('aa bf 00 02 ef 29 ff 00').branch(0xf0, 'original')
    c.emit('a3 10 18 69 e7 7d 83 03 a3 10 18 69 fe 7d 83 05 fa').emit(far_jump(0x5c, 0x13e28))
    c.mark('original').emit('fa').emit(native).emit(far_jump(0x5c, 0x13d9b))
    write(0x2f2000, c.finish())
    data[0x13d95:0x13d9b] = far_jump(0x5c, 0x2f2000)+b'\xea'*2
    # Chain the already-installed extra-ship loader rather than replacing it.
    previous = bytes(data[0x13c0c:0x13c10])
    if previous[0] == 0x5c:
        fallback = previous
    elif previous == bytes.fromhex('a3 72 85 00'):
        fallback = previous+far_jump(0x5c, 0x13c10)
    else:
        raise ValueError('Unsupported shared artwork loader.')
    c = Code().emit('a3 72 c9 00 7e').branch(0x90, 'original').emit('c9 62 7e').branch(0xb0, 'original')
    c.emit('da 38 e9 00 7e 85 00 0a 18 65 00 aa bf 00 00 ef 85 00 bf 02 00 ef 29 ff 00 85 02 fa').emit(far_jump(0x5c, 0x13c4b))
    c.mark('original').emit(fallback)
    write(0x2f2100, c.finish())
    data[0x13c0c:0x13c10] = far_jump(0x5c, 0x2f2100)
    # Private palette pointer; all stock/item/ship palette requests replay native code.
    if data[0x13bd5:0x13bd9] != bytes.fromhex('a3 76 85 00'):
        raise ValueError('Unsupported palette loader.')
    c = Code().emit('a3 76 c9 00 7e').branch(0x90, 'original').emit('c9 62 7e').branch(0xb0, 'original')
    c.emit('38 e9 00 7e 0a 0a 0a 0a 0a 18 69 00 10 85 00 a9 ef 00 85 02').emit(far_jump(0x5c, 0x13bec))
    c.mark('original').emit('a3 76 85 00').emit(far_jump(0x5c, 0x13bd9))
    write(0x2f2200, c.finish())
    data[0x13bd5:0x13bd9] = far_jump(0x5c, 0x2f2200)


def changed_slots(project):
    """Compare effective content, ignoring Library IDs and capture metadata."""
    from discoveries import catalogue, picture_data
    originals=catalogue(project.rom); current=rows(project); changed=set()
    for slot,(old,new) in enumerate(zip(originals,current)):
        if any(old[key]!=new[key] for key in ('name','description','category','difficulty')):
            changed.add(slot);continue
        entry=project.discovery_entries.get(slot)
        if entry:
            raw,palette=picture_data(project.rom,slot)
            if decode64(entry['tiles'],512)!=raw or decode64(entry['palette'],32)!=palette:changed.add(slot)
    return changed
