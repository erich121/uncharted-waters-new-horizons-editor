"""Honor explicitly edited protagonist Luck at native new-game initialization."""
HELPER=0x337000
FLAGS=0x337100
VALUES=0x337110
SITE=0x74E61
NATIVE=bytes.fromhex('a5 00 a0 23 00 91 0c')


def install(data,edits):
    values={e['id']:e['value']for e in edits if e['id']<6 and e['field']=='luck'}
    if not values:return
    from expansion import Code,far_jump
    if data[SITE:SITE+7]!=NATIVE:raise ValueError('Unsupported protagonist Luck initializer.')
    if len(data)==0x200000:data.extend(b'\xff'*0x200000);data[0xffd7]=12
    flags=bytes(int(i in values)for i in range(6));fixed=bytes(values.get(i,0)for i in range(6))
    c=Code().emit('08 c2 30 48 da af fb 25 7e 29 ff 00 c9 06 00').branch(0xb0,'native')
    c.emit('aa bf 00 71 f3 29 ff 00').branch(0xf0,'native')
    c.emit('e2 20 bf 10 71 f3 83 03').branch(0x80,'restore')
    c.mark('native').emit('e2 20 a5 00 83 03')
    c.mark('restore').emit('c2 20 fa 68 28 a0 23 00 91 0c 6b')
    for at,raw in ((HELPER,c.finish()),(FLAGS,flags),(VALUES,fixed)):
        if data[at:at+len(raw)]!=b'\xff'*len(raw):raise ValueError('Protagonist Luck storage overlaps another patch.')
        data[at:at+len(raw)]=raw
    data[SITE:SITE+7]=far_jump(0x22,HELPER)+b'\xea'*3
