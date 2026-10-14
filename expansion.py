"""Ship-only additive compiler for stock USA ROM, adapted from tested ten-hull code.

No item, shop, pricing-curve, battle-control or campaign patches are included.
Existing portraits and icons are shared. IDs25..29 use new templates65..69.
"""
import re,struct,hashlib
def sha(data):return hashlib.sha256(data).hexdigest()
RAM_DEFAULTS=0x0780
RAM_SPECS=0x087A
ROM_RECORDS=0x210000
ROM_NAMES=0x211000
ROM_ART_PTR=0x211200
FIXED_INDUSTRY_PORTS=(0,1,2,8,29,33,77)
TEMPLATE_PTR = 0x200400
SPEC_PTR = 0x200500
ITEM_PROPERTY_PTR = 0x200600
SHIP_NAME = 0x200800
ITEM_NAME = 0x200820
ITEM_DESC = 0x200840
SHIP_PRINT = 0x200A00
TEMPLATE_DIRECT = 0x200A80
SPEC_DIRECT = 0x200AC0
SHIP_STOCK = 0x200B00
SHIP_CONFIRM = 0x200C00
ITEM_STOCK_SHIM = 0x200D00
ITEM_EFFECT_SHIM = 0x200D80
OWNED_VARIANT_SHIM = 0x200E00


def cpu(p):
    return p+0xC00000


def far_jump(op, p):
    return bytes([op])+cpu(p).to_bytes(3, "little")


def make_pack(rom):
    data = bytearray(rom)+bytearray(b"\xFF"*0x200000)
    log = []

    def write(p, content, reason, expected=None):
        if expected is not None and rom[p:p+len(expected)] != expected:
            raise ValueError(f"Unexpected original instructions at {p:06X}")
        data[p:p+len(content)] = content
        log.append({"offset": f"0x{p:06X}", "size": len(content), "reason": reason,
                    "before": rom[p:p+len(content)].hex(), "after": content.hex()})

    write(TEMPLATE_PTR, rom[0xAD0BC:0xAD13E]+rom[0xAD0BC+46*2:0xAD0BC+47*2], "66 template pointers; new variant shares template 46 properties")
    write(SPEC_PTR, rom[0xAD13E:0xAD170]+rom[0xAD13E+6*2:0xAD13E+7*2], "26 ship selection specification pointers; variant shares type 6 properties")
    write(SHIP_NAME, b"Sea Falcon\0", "New ship display name")

    # These compiler patterns build a 24-bit base in direct-page $08/$0A.
    def relocate_base(old_low, old_bank, new, expected_count):
        pattern = bytes([0xA9])+old_low.to_bytes(2, "little")+bytes.fromhex("85 08 a9")+old_bank.to_bytes(2, "little")+bytes.fromhex("85 0a")
        matches = [m.start() for m in re.finditer(re.escape(pattern), rom)]
        if len(matches) != expected_count:
            raise ValueError(f"Unexpected base-reference count: {old_bank:02X}:{old_low:04X}: {matches}")
        replacement = bytes([0xA9])+(cpu(new)&0xFFFF).to_bytes(2, "little")+bytes.fromhex("85 08 a9")+(cpu(new)>>16).to_bytes(2, "little")+bytes.fromhex("85 0a")
        for p in matches:
            write(p, replacement, f"Relocate lookup base {old_bank:02X}:{old_low:04X}", pattern)
        return matches

    refs = {
        "ship_templates": relocate_base(0xD0BC, 0xCA, TEMPLATE_PTR, 1),
        "ship_specs": relocate_base(0xD13E, 0xCA, SPEC_PTR, 1),
    }
    # Printing template 65 reads its new ROM name; normal template indices keep
    # their original RAM name path. JML preserves the caller's stack offsets.
    ship_print = bytes.fromhex("a3 04 c9 41 00 d0 0d f4 e0 00 f4 00 08 22 43 3c c2 68 68 6b a9 19 00 85 04")+bytes.fromhex("5c dc 71 c2")
    write(SHIP_PRINT, ship_print, "Additional ship name printer")
    write(0x271D7, far_jump(0x5C, SHIP_PRINT)+b"\xEA", "Route ship name printer through additional-template case", bytes.fromhex("a9 19 00 85 04"))
    # Two arithmetic consumers bypass the pointer helpers. Their new index
    # must resolve to the matching original hull record for sailing behavior.
    direct_template = bytes.fromhex("a5 00 c9 59 06 d0 03 a9 7e 04 18 69 d7 6b 85 00 6b")
    direct_spec = bytes.fromhex("a5 00 c9 2c 01 d0 03 a9 48 00 18 69 30 72 85 00 6b")
    write(TEMPLATE_DIRECT, direct_template, "Resolve template 65 in arithmetic consumers to shared template 46")
    write(SPEC_DIRECT, direct_spec, "Resolve ship selection 25 in arithmetic consumers to shared type 6")
    for base, shim, count in [(0x6BD7, TEMPLATE_DIRECT, 3), (0x7230, SPEC_DIRECT, 2)]:
        pattern = b"\x18\xA9"+base.to_bytes(2, "little")+bytes.fromhex("65 00 85 00")
        matches = [m.start() for m in re.finditer(re.escape(pattern), rom)]
        # The name-printer's arithmetic occurrence was replaced by the JML.
        for p in matches:
            if 0x271D7 <= p < 0x27208:
                continue
            write(p, far_jump(0x22, shim)+b"\xEA"*4, "Handle extra index in direct table access", pattern)
        if len(matches) != count:
            raise ValueError("Unexpected direct table consumer count")

    # Widen each shipyard list to sixteen slots. Existing eight slots retain
    # their exact order; Lisbon's list gets one additional hull selection.
    stock = bytearray()
    for row in range(11):
        stock.extend(rom[0x8FAE7+row*8:0x8FAE7+(row+1)*8])
        stock.extend(bytes([25 if row == 0 else 255])+b"\xFF"*7)
    write(SHIP_STOCK, stock, "Widen shipyard stocks; append Sea Falcon to stock group zero")
    relocate_base(0xFAE7, 0xC8, SHIP_STOCK, 2)
    for p in (0x82144, 0x8252C):
        write(p, bytes.fromhex("a9 04 00"), "Ship stock stride sixteen", bytes.fromhex("a9 03 00"))
    write(0x82168, bytes.fromhex("a9 10 00"), "Scan all sixteen ship stock slots", bytes.fromhex("a9 08 00"))
    write(SHIP_CONFIRM, rom[0x8FB3F:0x8FB71]+rom[0x8FB3F+12:0x8FB3F+14], "26 ship confirmation IDs; added variant uses original hull description")
    relocate_base(0xFB3F, 0xC8, SHIP_CONFIRM, 2)

    write(0x80218, far_jump(0x22, OWNED_VARIANT_SHIM)+b"\xEA"*4, "Extra allocation hook", bytes.fromhex("a0 01 00 b1 28 29 ff 00"))
    write(0xFFD7,b"\x0C","4 MiB ROM",b"\x0B")
    return bytes(data),dict(changes=log)

class Code:
    def __init__(self):
        self.data = bytearray()
        self.labels = {}
        self.fixups = []

    def emit(self, value):
        self.data.extend(bytes.fromhex(value) if isinstance(value, str) else value)
        return self

    def branch(self, opcode, label):
        self.emit(bytes([opcode, 0]))
        self.fixups.append((len(self.data)-1, label, 1))
        return self

    def branch_far(self, opcode, label):
        self.emit(bytes([opcode ^ 0x20, 3, 0x82, 0, 0]))
        self.fixups.append((len(self.data)-2, label, 2))
        return self

    def mark(self, label):
        self.labels[label] = len(self.data)
        return self

    def finish(self):
        for location, label, width in self.fixups:
            delta = self.labels[label]-location-width
            limit = 1 << (width*8-1)
            if not -limit <= delta < limit:
                raise ValueError("Branch outside signed byte range")
            self.data[location:location+width] = delta.to_bytes(width, 'little', signed=True)
        return bytes(self.data)


def install_used_market(ships, write, Code, far_jump, region_table=0x214400, gate_table=0x214480, town_table=0x214000):
    count=len(ships)
    if not 1<=count<=5:raise ValueError('Expected1..5 models')
    limit=(25+count).to_bytes(2,'little')
    multiply='48 a9 00 00'+(' 18 63 01'*count)
    address=lambda at: (at+0xC00000).to_bytes(3,'little')
    # Explicit region and requirement tables supplement the existing town bitmap.
    write(region_table, bytes(int(group in ship['stock_groups'])
                         for group in range(11) for ship in ships), 'Used-model regional eligibility')
    write(gate_table, b''.join(ship['industry_required'].to_bytes(2, 'little') for ship in ships),
          'Used-model industry requirements')
    eligible = Code().emit('da 5a c9 19 00').branch_far(0x90, 'deny')
    eligible.emit('c9').emit(limit).branch_far(0xB0, 'deny')
    eligible.emit('38 e9 19 00 a8 0a aa bf').emit(address(gate_table)).emit('48 af 0c e8 7e aa bf 04 00 7e c3 01 68').branch_far(0x90, 'deny')
    eligible.emit('bf 22 00 7e 29 ff 00 c9 0b 00').branch_far(0xB0, 'deny')
    # 10*region + model index; scratch is confined to a balanced stack push.
    eligible.emit(multiply+' 48 98 18 63 01 aa 68 68 bf').emit(address(region_table)).emit('29 ff 00').branch_far(0xF0, 'deny')
    eligible.emit('af 16 20 7e 29 ff 00 c9 64 00').branch_far(0xB0, 'deny')
    eligible.emit(multiply+' 48 98 18 63 01 aa 68 68 bf').emit(address(town_table)).emit('29 ff 00').branch_far(0xF0, 'deny')
    eligible.emit('7a fa a9 01 00 6b').mark('deny').emit('7a fa a9 00 00 6b')
    write(0x214500, eligible.finish(), 'Extra used hull eligibility; preserves X, Y and direct page')

    spawn = Code().emit('da 5a 48')
    for offset in range(0, 0x60, 2):
        spawn.emit(bytes([0xD4, offset]))
    spawn.emit('f4 04 00 22 57 0a c1 68 a5 00').branch_far(0xD0, 'finish')
    spawn.emit('64 30 a9 19 00 85 32').mark('scan')
    spawn.emit('a5 32 22 00 45 e1 c9 00 00').branch(0xF0, 'next')
    spawn.emit('a5 30 0a aa a5 32 95 40 e6 30').mark('next')
    spawn.emit('e6 32 a5 32 c9').emit(limit).branch(0x90, 'scan')
    spawn.emit('a5 30').branch_far(0xF0, 'finish')
    spawn.emit('d4 30 22 57 0a c1 68 a5 00 0a aa b5 40 85 34 c9 22 00').branch(0xD0, 'slot')
    spawn.emit('f4 0a 00 22 57 0a c1 68 a5 00').branch_far(0xD0, 'finish')
    spawn.mark('slot').emit('a2 00 00').mark('empty')
    spawn.emit('bf fc 8c 7e 29 ff 00 c9 ff 00').branch(0xF0, 'store')
    spawn.emit('e8 e0 03 00').branch(0x90, 'empty').emit('a2 02 00')
    spawn.mark('store').emit('a5 34 e2 20 9f fc 8c 7e c2 20').mark('finish')
    for offset in reversed(range(0, 0x60, 2)):
        spawn.emit(bytes([0x68, 0x85, offset]))
    spawn.emit('68 7a fa 6b')
    write(0x214700, spawn.finish(), 'Occasional used offer; 25% ordinary chance, extra 1-in-10 Sovereign gate')
    wrapper = far_jump(0x22, 0x214700)+bytes.fromhex('3b 18 69 14 00 1b')+far_jump(0x5C, 0xA5BAB)
    write(0x214900, wrapper, 'Fresh used-generation completion wrapper')
    write(0xA5BA5, far_jump(0x5C, 0x214900)+bytes.fromhex('ea ea'), 'Add specials only when fresh stock is generated',
          bytes.fromhex('3b 18 69 14 00 1b'))

    listing = Code().emit('a7 24 29 ff 00 c9 19 00').branch(0x90, 'return')
    listing.emit('48 22 00 45 e1 c9 00 00').branch(0xF0, 'hidden')
    listing.emit('68').mark('return').emit('6b')
    listing.mark('hidden').emit('68 a9 ff 00 6b')
    write(0x214C00, listing.finish(), 'Filter cached special offers by current town, region and industry')
    write(0x82685, far_jump(0x22, 0x214C00)+b'\xea', 'Used-menu eligibility guard', bytes.fromhex('a7 24 29 ff 00'))
    write(0x84897, far_jump(0x22, 0x214C00)+b'\xea', 'Keep used-stock status counts consistent with hidden offers',
          bytes.fromhex('a7 24 29 ff 00'))

    purchase = Code().emit('a3 03 29 ff 00 c9 19 00').branch(0x90, 'allow')
    purchase.emit('48 22 00 45 e1 c9 00 00').branch(0xF0, 'back')
    purchase.emit('68').mark('allow').emit(far_jump(0x5C, 0x827F3))
    purchase.mark('back').emit('68').emit(far_jump(0x5C, 0x8273C))
    write(0x214C40, purchase.finish(), 'Recheck used purchase eligibility before payment')
    write(0x827EE, far_jump(0x5C, 0x214C40)+b'\xea', 'Used-purchase eligibility guard', bytes.fromhex('a3 03 29 ff 00'))

def make_fleet(rom, design):
    # Capitals cannot be developed by player investment. Do not install a
    # model there whose gate exceeds the original port's fixed industry.
    for ship in design['ships']:
        for port in FIXED_INDUSTRY_PORTS:
            record = 0x8DA7F + port * 37
            assigned = (rom[record+34] in ship['stock_groups'] and
                        ('stock_ports' not in ship or port in ship['stock_ports']))
            if assigned and ship['industry_required'] > int.from_bytes(rom[record+4:record+6], 'little'):
                raise ValueError(f"Unreachable capital offer: {ship['name']} at port {port}")
    initial, report = make_pack(rom)
    data = bytearray(initial)
    ships = design['ships'];count=len(ships)
    assert 1<=count<=5
    changes = []

    def write(offset, value, reason, expected=None):
        if expected is not None and rom[offset:offset+len(expected)] != expected:
            raise ValueError(f'Unexpected original bytes at {offset:X}')
        changes.append({'offset': f'0x{offset:06X}', 'size': len(value), 'reason': reason,
                        'before': bytes(data[offset:offset+len(value)]).hex(), 'after': bytes(value).hex()})
        data[offset:offset+len(value)] = value

    templates = bytearray()
    specs = bytearray()
    graphics_pointers = bytearray()
    portrait_status = []
    for n, s in enumerate(ships):
        base = s['base_hull']
        template = bytearray(rom[0x8CBB6+base*25:0x8CBB6+(base+1)*25])
        template[:18] = s['name'].encode('ascii').ljust(18, b'\0')
        template[18] = s['id']
        template[20] = s['default']['guns']
        struct.pack_into('<HH', template, 21, s['default']['crew_space'], s['default']['cargo_space'])
        templates.extend(template)
        spec = bytearray(rom[0x8CE27+base*12:0x8CE27+(base+1)*12])
        spec[:6] = bytes([s['industry_required']//10, s['base_durability'], s['turning'],
                          s['power'], s['max_crew']//10, s['min_crew']])
        struct.pack_into('<H', spec, 6, s['total_capacity'])
        spec[8] = s['max_guns']
        struct.pack_into('<H', spec, 10, s['price_units'])
        specs.extend(spec)
        write(ROM_NAMES+n*32, s['name'].encode('ascii')+b'\0', 'Extra hull name')
        relative=int.from_bytes(rom[0x2BAA4+base*3:0x2BAA7+base*3],'little')
        pointer=int.from_bytes(rom[0xCD556:0xCD559],'little')+relative
        portrait_status.append(dict(ship=s['name'],status='original portrait',base_hull=base))
        graphics_pointers.extend(pointer.to_bytes(3, 'little'))

    write(ROM_RECORDS, templates+b'\xff'*((10-count)*25)+specs+b'\xff'*((10-count)*12), 'Ten default templates and ten distinct specifications')
    write(ROM_ART_PTR, graphics_pointers, 'Ten extra portrait source pointers')
    write(0x200400, rom[0xAD0BC:0xAD13E]+b''.join((RAM_DEFAULTS+n*25).to_bytes(2, 'little') for n in range(count)), '75 template pointers')
    write(0x200500, rom[0xAD13E:0xAD170]+b''.join((RAM_SPECS+n*12).to_bytes(2, 'little') for n in range(count)), '35 specification pointers')

    # Initialization follows the kernel's RAM clearing and precedes the game.
    # Old fixed stack top $08FC becomes $077C; reserved records end at $08F1.
    write(0x8021, bytes.fromhex('a2 7c 07 9a'), 'Reserve immutable extra records above the native stack', bytes.fromhex('a2 fc 08 9a'))
    init = Code().emit('da a2 00 00').mark('copy').emit('bf 00 00 e1 9f 80 07 7e e8 e8 e0 72 01').branch(0xD0, 'copy').emit('fa a9 00 01 5b 6b').finish()
    write(0x213000, init, 'Initialize explicitly reserved extra RAM records')
    write(0x806E, far_jump(0x22, 0x213000), 'Initialize extra immutable records at reset', bytes.fromhex('a9 00 01 5b'))

    for shim, threshold, limit, ram, original in [(0x200A80, 65*25, (65+count)*25, RAM_DEFAULTS, 0x6BD7),
                                                (0x200AC0, 25*12, (25+count)*12, RAM_SPECS, 0x7230)]:
        code = Code().emit('a5 00 c9').emit(threshold.to_bytes(2, 'little')).branch(0x90, 'original')
        code.emit('c9').emit(limit.to_bytes(2, 'little')).branch(0xB0, 'original')
        code.emit('38 e9').emit(threshold.to_bytes(2, 'little')).emit('18 69').emit(ram.to_bytes(2, 'little')).emit('85 00 6b')
        code.mark('original').emit('a5 00 18 69').emit(original.to_bytes(2, 'little')).emit('85 00 6b')
        write(shim, code.finish(), 'Resolve every extra index in arithmetic consumers')

    # The original owned-record creator already writes its selection ID.
    owned = Code().emit('a3 15 29 ff 00 c9 19 00').branch(0x90, 'original').emit('c9').emit((25+count).to_bytes(2,'little')).branch(0xB0, 'original')
    owned.emit('e2 20 a0 14 00 b1 24 91 26 c2 20 a0 15 00 b1 24 91 26 a0 17 00 b1 24 91 26')
    owned.mark('original').emit('a0 01 00 b1 28 29 ff 00 6b')
    write(0x200E00, owned.finish(), 'Apply each new hull default allocation, preserving its unique class')

    names = Code().emit('a3 04 c9 41 00').branch(0x90, 'original').emit('c9').emit((65+count).to_bytes(2,'little')).branch(0xB0, 'original')
    names.emit('38 e9 41 00 0a 0a 0a 0a 0a 18 69 00 10 f4 e1 00 48 22 43 3c c2 68 68 6b')
    names.mark('original').emit('a9 19 00 85 04').emit(far_jump(0x5C, 0x271DC))
    write(0x200A00, names.finish(), 'Print all ten new default ship names')

    stocks = bytearray()
    for group in range(11):
        entries = [v for v in rom[0x8FAE7+group*8:0x8FAEF+group*8] if v != 255]
        entries += [s['id'] for s in ships if group in s['stock_groups']]
        if len(entries) > 16:
            raise ValueError('A regional stock exceeds its expanded capacity')
        stocks.extend(bytes(entries).ljust(16, b'\xff'))
    write(0x200B00, stocks, 'Preserve original stocks and add regional new hulls')
    # Additional models may be restricted to individual towns inside a region.
    # Original hulls retain the existing region/industry behavior and order.
    port_stock = bytes(int(s.get('stock_ports') is None or port in s['stock_ports'])
                       for port in range(100) for s in ships)
    write(0x214000, port_stock, 'Town availability for ten additional models')
    gate = Code().emit('a5 00').branch(0xD0, 'deny')
    gate.emit('a7 24 29 ff 00 c9 19 00').branch(0x90, 'accept')
    gate.emit('c9').emit((25+count).to_bytes(2,'little')).branch(0xB0, 'deny')
    gate.emit('38 e9 19 00 85 10 af 16 20 7e 29 ff 00 c9 64 00').branch(0xB0, 'deny')
    gate.emit('85 0c a9 00 00'+(' 18 65 0c'*count)+' 18 65 10 da aa bf 00 40 e1 29 ff 00 fa c9 00 00').branch(0xF0, 'deny')
    gate.mark('accept').emit(far_jump(0x5C, 0x821C4))
    gate.mark('deny').emit(far_jump(0x5C, 0x821F7))
    write(0x213600, gate.finish(), 'Apply town restrictions after the original industry check')
    write(0x821C0, far_jump(0x5C, 0x213600), 'Filter extra hulls by town', bytes.fromhex('a5 00 d0 33'))
    install_used_market(ships, write, Code, far_jump)
    write(0x200C00, rom[0x8FB3F:0x8FB71]+b''.join(rom[0x8FB3F+s['base_hull']*2:0x8FB41+s['base_hull']*2] for s in ships), '35 confirmation dialog IDs')
    write(0x213400, rom[0x2B6C9:0x2B6E2]+bytes(rom[0x2B6C9+s['base_hull']] for s in ships), '35 sailing and battle size classes')
    import re
    pattern = bytes.fromhex('69 c9 b6 85 0c a5 0e 69 c2 00 85 0e')
    sites = [m.start() for m in re.finditer(re.escape(pattern), rom)]
    if len(sites) != 5:
        raise ValueError('Unexpected size lookup consumer count')
    for site in sites:
        write(site, bytes.fromhex('69 00 34 85 0c a5 0e 69 e1 00 85 0e'), 'Expand sailing/battle size lookup')

    for destination, site, replay, resume in [(0x213100, 0x13CD0, 'f4 00 00 a3 0e', 0x13CD5),
                                              (0x213180, 0x13CF9, 'a3 10 48 a3 10', 0x13CFE)]:
        wrapper = Code().emit('a3 08 c9 19 00').branch(0x90, 'original').emit('c9').emit((25+count).to_bytes(2,'little')).branch(0xB0, 'original')
        wrapper.emit('38 e9 19 00 18 69 e0 7f 83 08').mark('original').emit(replay).emit(far_jump(0x5C, resume))
        write(destination, wrapper.finish(), 'Private portrait IDs for new hulls only')
        write(site, far_jump(0x5C, destination)+b'\xea', 'Extra ship portrait wrapper', bytes.fromhex(replay))
    loader = Code().emit('a3 72 c9 e0 7f').branch(0x90, 'original').emit('c9').emit((0x7fe0+count).to_bytes(2,'little')).branch(0xB0, 'original')
    loader.emit('38 e9 e0 7f da 85 00 0a 18 65 00 aa bf 00 12 e1 85 00 bf 02 12 e1 29 ff 00 85 02 fa').emit(far_jump(0x5C, 0x13C4B))
    loader.mark('original').emit('a3 72 85 00').emit(far_jump(0x5C, 0x13C10))
    write(0x213200, loader.finish(), 'Extra portrait pointer dispatch')
    write(0x13C0C, far_jump(0x5C, 0x213200), 'Extra portrait loader', bytes.fromhex('a3 72 85 00'))

    data[0xFFDC:0xFFE0] = bytes.fromhex('ff ff 00 00')
    checksum = sum(data)&65535
    struct.pack_into('<HH', data, 0xFFDC, checksum^65535, checksum)
    report.update(mod_sha256=sha(data), status='ship-only editor expansion; runtime validation pending',
                  new_ships=ships, extra_ship_count=count, stack_top='0x077C', extra_ram_records='0x0780..0x08F1',
                  original_ship_count=25, original_graphics_preserved=True)
    report['portraits'] = portrait_status
    report['used_market'] = dict(enabled=True, max_extra_offers=1, ordinary_offer_chance_percent=25,
                                sovereign_additional_gate='1 in 10 after selection',
                                original_cache_records=3, original_offer_slots=5,
                                town_industry_region_guards=True)
    report['changes'].extend(changes)
    report.pop('new_ship', None)
    return bytes(data), report

