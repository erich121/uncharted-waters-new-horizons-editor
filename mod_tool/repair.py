"""Clamp repair deficits without changing stock repair rates."""
HELPER=0x218C00
CODE=bytes.fromhex('a5 00 c5 04 b0 03 64 00 6b 38 e5 04 85 00 6b')
SITES=(0x8294A,0x82965,0x82983,0x9CBF4,0x9CC12,0x9CC30,0x9CE86,0x9CF20,0x9CFBB)

def apply(data):
    if len(data)==0x200000:
        data.extend(b'\xff'*0x200000)
        data[0xFFD7]=0x0C
    if len(data)!=0x400000:raise ValueError('Unsupported repair patch ROM size.')
    if data[HELPER:HELPER+len(CODE)]!=b'\xff'*len(CODE):raise ValueError('Repair helper overlaps occupied data.')
    for site in SITES:
        if data[site:site+4]!=bytes.fromhex('22 b5 fc c1'):raise ValueError('Unexpected repair routine; refusing patch.')
    data[HELPER:HELPER+len(CODE)]=CODE
    for site in SITES:data[site:site+4]=bytes.fromhex('22 00 8c e1')
