"""Read-only discovery name/location records from the stock USA ROM.

A catalogue is not the set enabled in a particular playthrough.
"""
from rom_map import WIDTH,HEIGHT
from functools import lru_cache
from PIL import Image
from portrait_codec import Decoder
BASE=584459-512
NAME_POINTERS=980297-512
SLOTS=99


def catalogue(rom):
    rows=[]
    for i in range(SLOTS):
        at=NAME_POINTERS+i*3
        ptr=int.from_bytes(rom[at:at+3],'little')-0xc00000
        if not 0<=ptr<len(rom):raise ValueError('Invalid discovery name pointer.')
        end=rom.find(b'\0',ptr,ptr+128)
        if end<0:raise ValueError('Missing discovery name terminator.')
        raw=rom[ptr:end];text=bytearray();j=0
        while j<len(raw):
            if raw[j]==27:j+=2;text.extend(b' ')
            else:text.append(raw[j]);j+=1
        name=' '.join(text.decode('ascii').split())
        if not name:continue # The final stock slot has no discovery name or location.
        at=BASE+i*7
        x=int.from_bytes(rom[at:at+2],'little');y=int.from_bytes(rom[at+2:at+4],'little')
        if not 0<=x<WIDTH or not 0<=y<HEIGHT:raise ValueError('Discovery outside the ROM map.')
        rows.append(dict(id=i,name=name,x=x,y=y,kind='Discovery',description=read_text(rom,0xebe62,i),category=read_text(rom,0xb0cf7,rom[at+6]&7),difficulty=rom[at+5],required_score=rom[at+5]+1))
    return rows


def read_text(rom,table,index):
    at=table+index*3;ptr=int.from_bytes(rom[at:at+3],'little')-0xc00000
    if not 0<=ptr<len(rom):raise ValueError('Invalid discovery text pointer.')
    end=rom.find(b'\0',ptr,ptr+2048)
    if end<0:raise ValueError('Missing discovery text terminator.')
    raw=rom[ptr:end];text=bytearray();j=0
    while j<len(raw):
        if raw[j]==27:j+=2;text.extend(b' ')
        else:text.append(raw[j]);j+=1
    return ' '.join(text.decode('ascii').split())


@lru_cache(maxsize=98)
def picture_data(rom,discovery_id):
    if type(discovery_id)is not int or not 0<=discovery_id<98:raise ValueError('Invalid discovery picture ID.')
    # C13D7C..C13E4C: graphic25+lookup[id], palette lookup[id]+1.
    graphic=25+rom[0x9fb49+discovery_id];palette_id=rom[0x9fbad+discovery_id]+1
    base=int.from_bytes(rom[0xcd556:0xcd559],'little')
    at=0x2baa4+graphic*3;pointer=base+int.from_bytes(rom[at:at+3],'little')-0xc00000
    if not 0<=pointer<len(rom):raise ValueError('Invalid discovery picture pointer.')
    raw=Decoder(rom).decode(pointer,512)
    if len(raw)!=512:raise ValueError('Wrong discovery picture dimensions.')
    at=0xaa8e0+palette_id*32
    return raw,rom[at:at+32]


def picture(rom,discovery_id,scale=4):
    raw,palette=picture_data(rom,discovery_id)
    colors=[tuple(((int.from_bytes(palette[i*2:i*2+2],'little')>>shift)&31)*255//31 for shift in (0,5,10))for i in range(16)]
    pixels=[None]*1024
    for tile in range(16):
        for y in range(8):
            for x in range(8):
                color=sum(((raw[tile*32+plane//2*16+y*2+plane%2]>>(7-x))&1)<<plane for plane in range(4))
                pixels[(tile//4*8+y)*32+tile%4*8+x]=colors[color]
    image=Image.new('RGB',(32,32));image.putdata(pixels)
    return image.resize((32*scale,32*scale),Image.Resampling.NEAREST)if scale!=1 else image
