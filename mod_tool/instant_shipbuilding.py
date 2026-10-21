"""Zero construction days for newly placed orders; retain payment and pickup."""
OFFSET = 0x824AB
ORIGINAL = bytes.fromhex('a5 00')
INSTANT = bytes.fromhex('a9 00')


def validate(value):
    if type(value) is not bool:raise ValueError('Instant shipbuilding must be On or Off.')
    return value


def install(data, enabled):
    if not validate(enabled):return
    if data[OFFSET:OFFSET+2] != ORIGINAL:raise ValueError('Unsupported ship construction timer.')
    # M=8 here: load zero instead of the calculated day count. The native order
    # record, quote, payment, naming and collection routines remain in place.
    data[OFFSET:OFFSET+2] = INSTANT
