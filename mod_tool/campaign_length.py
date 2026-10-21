"""Extend only the native campaign deadline; retain calendar and aging logic."""
OFFSET = 0x100E9
ORIGINAL = bytes.fromhex('a9 34 00')
EXTENDED = bytes.fromhex('a9 46 00')


def validate(value):
    if type(value) is not bool:
        raise ValueError('50-year campaign must be On or Off.')
    return value


def install(data, enabled):
    if not validate(enabled):
        return
    if data[OFFSET:OFFSET+3] != ORIGINAL:
        raise ValueError('Unsupported campaign deadline code.')
    # Displayed year = internal year + 1501. The native comparison permits
    # internal years <= 52 (1553); > 52 ends play in January 1554.
    # Permit <= 70 (1571), ending in January 1572: 50 years after 1522.
    data[OFFSET:OFFSET+3] = EXTENDED
