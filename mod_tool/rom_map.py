"""ROM world grid and port coordinates, decoded without modifying game data.

Compression uses the existing Gilmok/UWNHRando-derived decoder (MIT).
Editor overview colours are a display key, not a recreation of native tile art.
"""
from PIL import Image
from portrait_codec import Decoder

WIDTH,HEIGHT=2160,1080
MAP_BASE=1163902-512
POINTERS=249786-512
TILE_TABLE=983552-512
PORT_BASE=577875-512


def port_positions(rom):
    rows=[]
    for i in range(130):
        at=PORT_BASE+i*22
        x=int.from_bytes(rom[at:at+2],'little');y=int.from_bytes(rom[at+2:at+4],'little')
        if not 0<=x<WIDTH or not 0<=y<HEIGHT:raise ValueError('Port outside ROM map.')
        rows.append(dict(id=i,x=x,y=y,name=rom[at+4:at+22].split(b'\0')[0].decode('ascii')))
    return rows


def decode_grid(rom):
    decoder=Decoder(rom);cache={};tiles=bytearray(WIDTH*HEIGHT)
    for by in range(45):
        for bx in range(90):
            at=POINTERS+3*(by*90+bx)
            delta=int.from_bytes(rom[at:at+3],'little')
            if delta not in cache:cache[delta]=decoder.decode(MAP_BASE+delta,max_output=144)
            block=cache[delta]
            if len(block)!=144:raise ValueError('Invalid ROM world block length.')
            for i,value in enumerate(block):
                x=bx*24+(i%12)*2;y=by*24+(i//12)*2
                quad=bytes(128 if value&bit else 0 for bit in (8,4,2,1))if value<16 else rom[TILE_TABLE+value*4:TILE_TABLE+value*4+4]
                p=y*WIDTH+x;tiles[p:p+2]=quad[:2];tiles[p+WIDTH:p+WIDTH+2]=quad[2:]
    return bytes(tiles)


def overview(grid):
    if len(grid)!=WIDTH*HEIGHT:raise ValueError('Wrong world grid size.')
    # Retain each decoded tile cell. A quiet colour key keeps the port marker legible.
    palette=[(32,83,116)]*256
    for i in range(128,256):palette[i]=(207,207,157)
    for i in (97,98,99,100,102,104,105,108):palette[i]=(207,207,157)
    for i in (168,170,171,173,175,176,178,179):palette[i]=(119,160,119)
    for i in (134,181,184,183,186,187,182,185,180):palette[i]=(223,197,143)
    for i in (144,145,146,147,150,151,152,153,156,157,158,159,162,163,164,165):palette[i]=(169,170,143)
    image=Image.frombytes('P',(WIDTH,HEIGHT),grid);image.putpalette([c for rgb in palette for c in rgb]);return image.convert('RGB')
