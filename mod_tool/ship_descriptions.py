"""Shipyard-worker text: independent per-ship paragraphs using native messages."""
PRIMARY = 0xB4EFB
SECONDARY = 0xE54F2
SECONDARY_COUNT = 468
FIRST_ID = 900 + SECONDARY_COUNT
TABLE = 0x330000
TEXT = 0x331000
MAX_LENGTH = 226


def validate(text):
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_LENGTH or '%' in text or any(not 32<=ord(c)<=126 for c in text):
        raise ValueError('Shipyard description needs 1–226 printable English characters, without %.')
    return text


def stock_text(rom,family):
    if type(family)is not int or not 0<=family<25:raise ValueError('Invalid description family.')
    message=int.from_bytes(rom[0x8FB3F+family*2:0x8FB41+family*2],'little')
    pointer=int.from_bytes(rom[PRIMARY+message*3:PRIMARY+message*3+3],'little')-0xC00000
    end=rom.find(b'\0',pointer,pointer+256)
    if not 0<=pointer<len(rom) or end<0:raise ValueError('Invalid stock shipyard description.')
    return validate(rom[pointer:end].decode('ascii').strip())


def default_text(project,slot):
    family=project.library_bases.get(slot,slot if slot<25 else project.ships[slot]['base_hull'])
    return stock_text(project.rom,family)


def text(project,slot):
    return project.ship_descriptions.get(slot,default_text(project,slot))


def read_state(raw,count):
    if not isinstance(raw,list):raise ValueError('Invalid shipyard descriptions.')
    result={}
    for row in raw:
        if not isinstance(row,dict) or set(row)!={'id','text'} or type(row['id'])is not int or not 0<=row['id']<count or row['id']in result:
            raise ValueError('Invalid or duplicate shipyard description slot.')
        result[row['id']]=validate(row['text'])
    return result


def state(project):
    rows=[dict(id=i,text=t)for i,t in sorted(project.ship_descriptions.items())]
    read_state(rows,len(project.ships))
    return rows


def set_text(project,slot,value):
    if type(slot)is not int or not 0<=slot<len(project.ships):raise ValueError('Invalid ship description slot.')
    value=validate(value)
    if value==default_text(project,slot):project.ship_descriptions.pop(slot,None)
    else:project.ship_descriptions[slot]=value


def install(data,project):
    entries=state(project)
    if not entries:return
    if len(data)==0x200000:
        data.extend(b'\xff'*0x200000);data[0xFFD7]=12
    stock=project.rom
    # The secondary table ends precisely at its first text pointer.
    if int.from_bytes(stock[SECONDARY:SECONDARY+3],'little')-0xC00000 != SECONDARY+SECONDARY_COUNT*3:
        raise ValueError('Unsupported native message table.')
    pointers=bytearray(stock[SECONDARY:SECONDARY+SECONDARY_COUNT*3])+bytearray(35*3)
    def write(at,raw):
        if data[at:at+len(raw)]!=b'\xff'*len(raw):raise ValueError('Ship description storage overlaps another modification.')
        data[at:at+len(raw)]=raw
    for row in entries:
        slot=row['id'];at=TEXT+slot*256
        write(at,row['text'].encode('ascii')+b'\0')
        i=SECONDARY_COUNT+slot
        pointers[i*3:i*3+3]=(0xC00000+at).to_bytes(3,'little')
        table=0x200C00 if len(project.ships)>25 else 0x8FB3F
        data[table+slot*2:table+slot*2+2]=(FIRST_ID+slot).to_bytes(2,'little')
    write(TABLE,pointers)
    # Two native message presenters use this secondary pointer table. Keep all
    # 468 existing entries byte-for-byte; only explicit ship IDs use the suffix.
    for at in (0x1759E,0x1763B):
        expected=bytes.fromhex('a9 f2 54 85 08 a9 ce 00')
        if data[at:at+8]!=expected:raise ValueError('Unsupported native message presenter.')
        data[at:at+8]=bytes.fromhex('a9 00 00 85 08 a9 f3 00')
