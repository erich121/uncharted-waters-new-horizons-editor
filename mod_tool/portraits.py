"""64x48 portraits: PNG conversion, exact previews and fixed-slot installation."""
from pathlib import Path
import base64
from PIL import Image
from portrait_codec import Decoder

WIDTH, HEIGHT, RAW_SIZE = 64, 48, 1536
SLOTS = 0x280000
SLOT_SIZE = 0x1000

def palette(rom):
    return [tuple(((int.from_bytes(rom[0xAA8E0+i*2:0xAA8E2+i*2], 'little') >> shift) & 31)*255//31
                  for shift in (0,5,10)) for i in range(16)]

def validate_raw(raw):
    if not isinstance(raw,bytes) or len(raw)!=RAW_SIZE:
        raise ValueError('A portrait must contain exactly 1,536 bytes of SNES tiles.')

def encode_tiles(indices):
    if len(indices)!=WIDTH*HEIGHT or any(type(v)is not int or not 0<=v<16 for v in indices):
        raise ValueError('Portrait needs 64x48 pixels using palette indices 0-15.')
    out=bytearray(RAW_SIZE)
    for tile in range(48):
        for y in range(8):
            for x in range(8):
                value=indices[(tile//8*8+y)*WIDTH+tile%8*8+x]
                for plane in range(4):
                    out[tile*32+plane//2*16+y*2+plane%2]|=((value>>plane)&1)<<(7-x)
    return bytes(out)

def decode_tiles(raw):
    validate_raw(raw);indices=[0]*(WIDTH*HEIGHT)
    for tile in range(48):
        for y in range(8):
            for x in range(8):
                indices[(tile//8*8+y)*WIDTH+tile%8*8+x]=sum(
                    ((raw[tile*32+plane//2*16+y*2+plane%2]>>(7-x))&1)<<plane for plane in range(4))
    return indices

def image(raw,rom,scale=1):
    colors=palette(rom);im=Image.new('RGB',(WIDTH,HEIGHT))
    im.putdata([colors[i]for i in decode_tiles(raw)])
    return im.resize((WIDTH*scale,HEIGHT*scale),Image.Resampling.NEAREST) if scale!=1 else im

def convert_png(path,rom):
    path=Path(path)
    if path.stat().st_size>32*1024*1024:raise ValueError('PNG must be smaller than 32 MB.')
    with Image.open(path)as source:
        if source.format!='PNG':raise ValueError('Choose a PNG image.')
        if source.width*source.height>16_000_000:raise ValueError('PNG must contain at most 16 million pixels.')
        size=source.size
        colors=palette(rom)
        # Alpha is flattened against the game's palette-zero background.
        rgba=source.convert('RGBA').resize((WIDTH,HEIGHT),Image.Resampling.NEAREST)
        background=Image.new('RGBA',(WIDTH,HEIGHT),colors[0]+(255,))
        rgb=Image.alpha_composite(background,rgba).convert('RGB')
    cache={};indices=[]
    pixels=rgb.tobytes()
    for n in range(0,len(pixels),3):
        pixel=tuple(pixels[n:n+3])
        if pixel not in cache:
            cache[pixel]=min(range(16),key=lambda i:sum((pixel[c]-colors[i][c])**2 for c in range(3)))
        indices.append(cache[pixel])
    raw=encode_tiles(indices)
    stream=literal_stream(raw)
    if Decoder(rom+stream).decode(len(rom),RAW_SIZE)!=raw:raise ValueError('Portrait compression verification failed.')
    return raw,size

def literal_stream(raw):
    validate_raw(raw)
    return b'\xfc\x01'+b''.join(b'\xff'+raw[n:n+8]for n in range(0,RAW_SIZE,8))+b'\0'

def original_pointer(rom,hull):
    if type(hull)is not int or not 0<=hull<25:raise ValueError('Invalid original portrait hull.')
    return int.from_bytes(rom[0xCD556:0xCD559],'little')+int.from_bytes(rom[0x2BAA4+hull*3:0x2BAA7+hull*3],'little')

def original_raw(rom,hull):
    raw=Decoder(rom).decode(original_pointer(rom,hull)-0xC00000,RAW_SIZE)
    validate_raw(raw);return raw

def pack(overrides):
    return [dict(id=i,tiles=base64.b64encode(raw).decode('ascii'))for i,raw in sorted(overrides.items())]

def unpack(entries,count):
    if not isinstance(entries,list):raise ValueError('Invalid portrait list.')
    result={}
    for e in entries:
        if not isinstance(e,dict)or set(e)!={'id','tiles'}or type(e['id'])is not int or not 0<=e['id']<count or e['id']in result:
            raise ValueError('Invalid or duplicate portrait ship ID.')
        if not isinstance(e['tiles'],str)or len(e['tiles'])!=2048:raise ValueError('Invalid portrait tile data.')
        try:raw=base64.b64decode(e['tiles'],validate=True)
        except (ValueError,TypeError)as ex:raise ValueError('Invalid portrait tile data.')from ex
        validate_raw(raw);result[e['id']]=raw
    return result

def install(data,stock,overrides,count):
    unpack(pack(overrides),count)
    if not overrides:return
    if len(data)==0x200000:
        data.extend(b'\xff'*0x200000);data[0xFFD7]=0x0C
    if len(data)!=0x400000:raise ValueError('Unsupported portrait ROM size.')
    origin=int.from_bytes(stock[0xCD556:0xCD559],'little')
    for hull,raw in sorted(overrides.items()):
        slot=SLOTS+hull*SLOT_SIZE;stream=literal_stream(raw)
        if len(stream)>SLOT_SIZE or data[slot:slot+SLOT_SIZE]!=b'\xff'*SLOT_SIZE:
            raise ValueError('Portrait storage overlaps occupied ROM data.')
        pointer=0xC00000+slot
        if hull<25:
            at=0x2BAA4+hull*3
            if data[at:at+3]!=stock[at:at+3]:raise ValueError('Unexpected original portrait pointer.')
            data[at:at+3]=(pointer-origin).to_bytes(3,'little')
        else:
            at=0x211200+(hull-25)*3
            data[at:at+3]=pointer.to_bytes(3,'little')
        data[slot:slot+len(stream)]=stream
        if Decoder(data).decode(slot,RAW_SIZE)!=raw:raise ValueError('Installed portrait verification failed.')
