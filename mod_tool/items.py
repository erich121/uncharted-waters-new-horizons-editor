"""Original equipment-shop catalogue; includes only IDs present in town shop stock."""
from discoveries import read_text
TOWNS=0x8da7f


def catalogue(rom):
    sources={}
    for port in range(100):
        for slot in range(4):
            item=rom[TOWNS+port*37+29+slot]
            if item==255:continue
            if not 0<=item<100:raise ValueError('Invalid shop item ID.')
            sources.setdefault(item,[]).append(dict(port=port,slot=slot,rare=slot==3,hours='02:00–02:59'if slot==3 else 'Shop hours'))
    return [dict(id=i,name=read_text(rom,0xb2378,i).replace('- ',''),description=read_text(rom,0x5d93e,i),sources=stock)for i,stock in sorted(sources.items())]


from functools import lru_cache
from PIL import Image
from portrait_codec import Decoder

@lru_cache(maxsize=100)
def picture_data(rom,item_id):
    if type(item_id)is not int or not 0<=item_id<100:raise ValueError('Invalid item picture ID.')
    # C7BC26 passes item ID+100 to C13D7C; item graphic and palette branch.
    graphic=115+rom[0x8ebc7+item_id*23+18];palette_id=36+rom[0x5fab7+item_id]
    base=int.from_bytes(rom[0xcd556:0xcd559],'little')
    at=0x2baa4+graphic*3;pointer=base+int.from_bytes(rom[at:at+3],'little')-0xc00000
    if not 0<=pointer<len(rom):raise ValueError('Invalid item picture pointer.')
    raw=Decoder(rom).decode(pointer,512)
    if len(raw)!=512:raise ValueError('Wrong item picture dimensions.')
    at=0xaa8e0+palette_id*32
    return raw,rom[at:at+32]


def picture(rom,item_id,scale=4):
    raw,palette=picture_data(rom,item_id)
    colors=[tuple(((int.from_bytes(palette[i*2:i*2+2],'little')>>shift)&31)*255//31 for shift in (0,5,10))for i in range(16)]
    pixels=[None]*1024
    for tile in range(16):
        for y in range(8):
            for x in range(8):
                color=sum(((raw[tile*32+plane//2*16+y*2+plane%2]>>(7-x))&1)<<plane for plane in range(4))
                pixels[(tile//4*8+y)*32+tile%4*8+x]=colors[color]
    image=Image.new('RGB',(32,32));image.putdata(pixels)
    return image.resize((32*scale,32*scale),Image.Resampling.NEAREST)if scale!=1 else image
