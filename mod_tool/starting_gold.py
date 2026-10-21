"""New-game wallet override, including the two scripted opening assignments."""
from decimal import Decimal, InvalidOperation

MAXIMUM = 250000
INIT_SITE = 0x74EA7
INIT_NATIVE = bytes.fromhex('22 cc 4d c7')
STORY_SITE = 0x985FF
STORY_NATIVE = bytes.fromhex('22 f2 fe c1')
INIT_HELPER = 0x33E300
STORY_HELPER = 0x33E400


def validate(value):
    if value is not None and (type(value) is not int or not 0 <= value <= MAXIMUM):
        raise ValueError('Starting gold must be 0–25 gold bars, in whole gold pieces.')
    return value


def from_bars(value):
    try:
        gold = Decimal(str(value)) * 10000
        if not gold.is_finite() or gold != gold.to_integral_value():raise ValueError()
        return validate(int(gold))
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError('Enter 0–25 gold bars, with at most four decimal places.') from None


def bars(value):
    text = format(Decimal(value)/10000, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def install(data, value):
    value = validate(value)
    if value is None:return
    if data[INIT_SITE:INIT_SITE+4] != INIT_NATIVE or data[STORY_SITE:STORY_SITE+4] != STORY_NATIVE:
        raise ValueError('Unsupported starting-money initializer.')
    from expansion import Code, far_jump
    if len(data) == 0x200000:
        data.extend(b'\xff'*0x200000);data[0xffd7] = 12
    lo = (value & 65535).to_bytes(2, 'little')
    hi = (value >> 16).to_bytes(2, 'little')
    c = Code().emit(INIT_NATIVE).emit('08 c2 30 48')
    c.emit('a9').emit(lo).emit('8f f4 25 7e a9').emit(hi).emit('8f f6 25 7e 68 28 6b')
    initial = c.finish()
    # Ernst and Pietro alone use an absolute 5,000-gold assignment in their
    # opening stories. Identify that exact six-byte native command, rather than
    # changing generic rewards, purchases, income or arbitrary 5,000-gold values.
    c = Code().emit(STORY_NATIVE).emit('08 c2 30 48 da 5a d4 0c d4 0e')
    c.emit('af fb 25 7e 29 ff 00 c9 03 00').branch(0xf0, 'hero')
    c.emit('c9 04 00').branch(0xd0, 'restore')
    c.mark('hero').emit('af 3b 9f 7e 29 ff 00 c9 7f 00').branch(0xd0, 'restore')
    c.emit('85 0e af 39 9f 7e c9 06 00').branch(0x90, 'restore')
    c.emit('38 e9 06 00 85 0c a7 0c c9 0c 00').branch(0xd0, 'restore')
    c.emit('a0 02 00 b7 0c c9 13 88').branch(0xd0, 'restore')
    c.emit('a0 04 00 b7 0c c9 e4 00').branch(0xd0, 'restore')
    c.emit('a9').emit(lo).emit('85 00 a9').emit(hi).emit('85 02')
    c.mark('restore').emit('68 85 0e 68 85 0c 7a fa 68 28 6b')
    story = c.finish()
    for at, raw in ((INIT_HELPER, initial), (STORY_HELPER, story)):
        if data[at:at+len(raw)] != b'\xff'*len(raw):
            raise ValueError('Starting gold storage overlaps another patch.')
        data[at:at+len(raw)] = raw
    data[INIT_SITE:INIT_SITE+4] = far_jump(0x22, INIT_HELPER)
    data[STORY_SITE:STORY_SITE+4] = far_jump(0x22, STORY_HELPER)
