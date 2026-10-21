"""Independent new-build offers; never modify the stock used-market table."""
STOCK=0x219000
PORTS=0x219200
INDUSTRY=0x219E00
GATE=0x219F00
LARGE_STOCK=0x21B000
LARGE_PORTS=0x21B400
LARGE_INDUSTRY=0x21C200
LARGE_GATE=0x21C300

def layout(count):
    from ship_limits import MAX_SHIPS
    if type(count)is not int or not 25<=count<=MAX_SHIPS:raise ValueError('Unsupported new-build ship count.')
    return (STOCK,PORTS,INDUSTRY,GATE,32)if count<=30 else (LARGE_STOCK,LARGE_PORTS,LARGE_INDUSTRY,LARGE_GATE,64)

def install(data,rom,offers):
    from expansion import Code,far_jump
    if len(data)==0x200000:data.extend(b'\xff'*0x200000);data[0xffd7]=0x0c
    count=len(offers)
    stock,port_table,industry_table,gate,stride=layout(count)
    rows=[]
    for group in range(11):
        ports=[p for p in range(100)if rom[0x8da7f+p*37+34]==group]
        wanted={i for i,o in enumerate(offers)if set(o['ports']).intersection(ports)}
        order=[i for i in rom[0x8fae7+group*8:0x8faef+group*8]if i in wanted]
        order += sorted(wanted-set(order))
        if len(order)>stride:raise ValueError('Regional new-build candidates exceed their table stride.')
        rows.extend(bytes(order).ljust(stride,b'\xff'))
    blocks={stock:bytes(rows),port_table:bytes(int(p in o['ports'])for p in range(100)for o in offers),
            industry_table:b''.join(o['industry'].to_bytes(2,'little')for o in offers)}
    c=Code().emit('a7 24 29 ff 00 c9').emit(count.to_bytes(2,'little')).branch_far(0xB0,'deny').emit('85 10')
    c.emit('af 16 20 7e 29 ff 00 c9 64 00').branch_far(0xB0,'deny').emit('85 0c a9 00 00'+(' 18 65 0c'*count)+' 18 65 10 da aa bf').emit((port_table+0xc00000).to_bytes(3,'little')).emit('29 ff 00 fa c9 00 00').branch_far(0xF0,'deny')
    c.emit('a5 10 0a da aa bf').emit((industry_table+0xc00000).to_bytes(3,'little')).emit('fa c5 04').branch(0x90,'accept').branch(0xF0,'accept')
    c.mark('deny').emit(far_jump(0x5C,0x821f7))
    c.mark('accept').emit(far_jump(0x5C,0x821c4));blocks[gate]=c.finish()
    for at,code in blocks.items():
        if data[at:at+len(code)]!=b'\xff'*len(code):raise ValueError('New-build availability overlaps occupied data.')
        data[at:at+len(code)]=code
    # Only the NEW menu's pointer, stride, scan count and gate are changed.
    for at,expected in [(0x82144,[bytes.fromhex('a9 03 00'),bytes.fromhex('a9 04 00')]),
                        (0x82168,[bytes.fromhex('a9 08 00'),bytes.fromhex('a9 10 00')]),
                        (0x82149,[bytes.fromhex('a9 e7 fa 85 08 a9 c8 00 85 0a'),bytes.fromhex('a9 00 0b 85 08 a9 e0 00 85 0a')]),
                        (0x821c0,[bytes.fromhex('a5 00 d0 33'),far_jump(0x5c,0x213600)])]:
        if not any(data[at:at+len(e)]==e for e in expected):raise ValueError('Unexpected new-build stock instructions.')
    data[0x82144:0x82147]=bytes([0xa9,5 if stride==32 else 6,0])
    data[0x82168:0x8216b]=bytes([0xa9,stride,0])
    data[0x82149:0x82153]=b'\xa9'+(stock&65535).to_bytes(2,'little')+b'\x85\x08\xa9'+((stock+0xc00000)>>16).to_bytes(2,'little')+b'\x85\x0a'
    data[0x821c0:0x821c4]=far_jump(0x5c,gate)
