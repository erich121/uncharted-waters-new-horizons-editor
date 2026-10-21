"""Shop item base prices, stored by the game in hundreds of gold."""
import struct
BASE = 0x8ebc7
STRIDE = 23

def stock(rom, item):
    return struct.unpack_from('<H', rom, BASE + item * STRIDE + 19)[0] * 100

def validate(rom, edits):
    from items import catalogue
    allowed = {row['id'] for row in catalogue(rom)}
    if not isinstance(edits, list):raise ValueError('Invalid item prices.')
    result=[];seen=set()
    for row in edits:
        if not isinstance(row,dict) or set(row)!={'id','price_gold'}:raise ValueError('Invalid item price record.')
        item,price=row['id'],row['price_gold']
        if type(item)is not int or item not in allowed or item in seen:raise ValueError('Invalid or duplicate shop item.')
        if type(price)is not int or not 0<=price<=3276700 or price%100:raise ValueError('Item prices must be 0–3,276,700 gold, in steps of 100.')
        seen.add(item)
        if price!=stock(rom,item):result.append(dict(id=item,price_gold=price))
    return sorted(result,key=lambda row:row['id'])

def price(project,item):
    return next((r['price_gold'] for r in project.item_price_edits if r['id']==item),stock(project.rom,item))

def install(data,project):
    for row in validate(project.rom,project.item_price_edits):
        struct.pack_into('<H',data,BASE+row['id']*STRIDE+19,row['price_gold']//100)
