"""Read stock sailor records. No writes, recruitment changes, or save access.

Record layout: ROM-MODDING.md. Roles cross-checked against Dirtyferret's
first-hand Sailor List (GameFAQs FAQ 21827). IDs here are zero-based.
Hamid Lal (114) is a pirate captain, not a free agent despite his record order.
"""
BASE=0x881F3
STRIDE=50
COUNT=120
NATIONALITIES=('Portugal','Spain','Turkey','England','Italy','Holland','Pirate')
MATE_IDS=tuple(range(69,114))+tuple(range(115,120))
CAPTAIN_IDS=tuple(range(6,69))+(114,)
ATTRIBUTES=('leadership','seamanship','knowledge','intuition','courage',
            'swordsmanship','charm','luck')

# Native profile order and the five low bits at record+48.
SKILLS=(('celestial_navigation','Celestial Navigation',16),('cartography','Cartography',8),
        ('gunnery','Gunnery',4),('accounting','Accounting',2),('negotiation','Negotiation',1))
EDITABLE_FIELDS=ATTRIBUTES+('skills',)

def skill_names(mask):return [label for _,label,bit in SKILLS if mask&bit]

def decode_sailors(rom):
    from ports import PORT_NAMES
    if len(rom)<BASE+COUNT*STRIDE:
        raise ValueError('The sailor table is incomplete.')
    result=[]
    for i in range(COUNT):
        offset=BASE+i*STRIDE
        record=rom[offset:offset+STRIDE]
        names=[]
        for field in (record[:13],record[13:26]):
            end=field.find(b'\0')
            if end<1 or any(b<32 or b>126 for b in field[:end]):
                raise ValueError(f'Invalid sailor name in record {i}.')
            names.append(field[:end].decode('ascii'))
        role=('Protagonist' if i<6 else 'Story companion' if 69<=i<79
              else 'Free agent' if i in MATE_IDS else 'Fleet captain')
        port=record[45] if role=='Free agent' else None
        if port is not None and not 0<=port<100:
            raise ValueError(f'Invalid free-agent starting port in record {i}.')
        nation=record[49]&15
        if nation>=len(NATIONALITIES):raise ValueError(f'Invalid sailor nationality in record {i}.')
        result.append(dict(nationality=NATIONALITIES[nation],id=i,name=' '.join(names),first_name=names[0],last_name=names[1],
            role=role,skills=record[48]&31,skill_names=skill_names(record[48]),**{key:record[28+j] for j,key in enumerate(ATTRIBUTES)},
            navigation_level=record[36],battle_level=record[37],age=record[42],
            starting_port=port,starting_port_name=PORT_NAMES[port] if port is not None else None))
    return result

def mates(rom):
    records=decode_sailors(rom)
    return [records[i] for i in MATE_IDS]


def fleet_captains(rom):
    """Starting fleet roles, not a claim that a sailor can never become a mate."""
    records=decode_sailors(rom)
    return [records[i] for i in CAPTAIN_IDS]
