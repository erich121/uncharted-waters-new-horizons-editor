"""Read native 40x48 sailor portraits, including tile-composed generic faces.

Fixed path: C1:37A0; composed path: C1:3007. No artwork is bundled or written.
"""
from functools import lru_cache
from PIL import Image
from portrait_codec import Decoder

WIDTH,HEIGHT=40,48
RAW_SIZE=960

def word(rom,offset):return int.from_bytes(rom[offset:offset+2],'little')

def block(rom,origin,table,index,expected):
    base=int.from_bytes(rom[origin:origin+3],'little')
    pointer=base+int.from_bytes(rom[table+index*3:table+index*3+3],'little')-0xC00000
    if not 0<=pointer<len(rom):raise ValueError('Invalid character portrait pointer.')
    raw=Decoder(rom).decode(pointer,expected)
    if len(raw)!=expected:raise ValueError('Invalid character portrait dimensions.')
    return raw

@lru_cache(maxsize=7)
def parts(rom,group):return block(rom,0xCD566,0x2BA8F,group,7680)

@lru_cache(maxsize=120)
def native_portrait(rom,face):
    if type(face)is not int or not 0<=face<=65535:raise ValueError('Invalid sailor portrait ID.')
    if face&0x8000:
        group=min((face>>12)&7,6)
        source=parts(rom,group);raw=bytearray(RAW_SIZE)
        def copy(dst,src,count):
            if not 0<=dst<30 or dst+count>30 or src+count>240:raise ValueError('Invalid face-part range.')
            raw[dst*32:(dst+count)*32]=source[src*32:(src+count)*32]
        top=(face>>9)&7;bottom=face&7;detail=(face>>3)&7;nose=(face>>6)&7
        copy(0,top*30,20);copy(20,bottom*30+20,10)
        a=word(rom,0x1F0EC+14+group*2)
        b=word(rom,0x1F0EC+28+group*2)
        c=word(rom,0x1F0EC+group*2)
        copy(15+a,detail*30+15+a,2 if 2<=group<=5 else 1)
        copy(20+b,detail*30+20+b,2 if group==1 else 3)
        copy(10+c,nose*30+10+c,3)
        if group==1:copy(15,bottom*30+15,1)
        palette_at=0x1F0AC+(32 if group==2 else 0)
        return bytes(raw),rom[palette_at:palette_at+32]
    if face>=128:raise ValueError('Unsupported stock character portrait index.')
    return block(rom,0xCD55A,0x2BCB7,face,RAW_SIZE),rom[0xAAF00:0xAAF20]

def portrait(rom,sailor_id,scale=3):
    if type(sailor_id)is not int or not 0<=sailor_id<120:raise ValueError('Invalid sailor ID.')
    face=word(rom,0x881F3+sailor_id*50+26)
    raw,palette=native_portrait(rom,face)
    colors=[tuple(((word(palette,i*2)>>shift)&31)*255//31 for shift in (0,5,10))for i in range(16)]
    pixels=[0]*(WIDTH*HEIGHT)
    for tile in range(30):
        for y in range(8):
            for x in range(8):
                index=sum(((raw[tile*32+plane//2*16+y*2+plane%2]>>(7-x))&1)<<plane for plane in range(4))
                pixels[(tile//5*8+y)*WIDTH+tile%5*8+x]=colors[index]
    im=Image.new('RGB',(WIDTH,HEIGHT));im.putdata(pixels)
    return im.resize((WIDTH*scale,HEIGHT*scale),Image.Resampling.NEAREST)if scale!=1 else im
