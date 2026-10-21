"""Reusable settings for existing shop items; no new engine item IDs."""
import copy
import json
import uuid
from items import catalogue
import item_shops
import item_prices

def validate(entry,rom):
    from content_library import valid_id
    keys={'kind','version','id','name','item_id','price_gold','sources'}
    if not isinstance(entry,dict)or set(entry)!=keys or entry['kind']!='item'or type(entry['version'])is not int or entry['version']!=1 or not valid_id(entry['id']):raise ValueError('Invalid Library item.')
    item=entry['item_id']
    if type(item)is not int or item not in {r['id']for r in catalogue(rom)}:raise ValueError('Choose an original shop item.')
    if entry['id'].startswith('stock-')and entry['id']!=f'stock-item:{item:02d}':raise ValueError('Item identity does not match its original item.')
    name=entry['name']
    if not isinstance(name,str)or not name.strip()or len(name)>80 or any(ord(c)<32 for c in name):raise ValueError('Library item names need 1–80 characters.')
    item_prices.validate(rom,[dict(id=item,price_gold=entry['price_gold'])])
    sources=entry['sources'];seen=set()
    if not isinstance(sources,list):raise ValueError('Invalid item selling ports.')
    for source in sources:
        if not isinstance(source,dict)or set(source)!={'port','early'}or type(source['port'])is not int or not 0<=source['port']<100 or type(source['early'])is not bool or source['port']in seen:raise ValueError('Choose valid selling ports without duplicates.')
        seen.add(source['port'])
    result=copy.deepcopy(entry);result['sources'].sort(key=lambda r:r['port'])
    return result

def capture(project,item):
    stock=next(r for r in catalogue(project.rom)if r['id']==item)
    row=next(r for r in item_shops.catalogue(project.rom,project.item_edits)if r['id']==item)
    sources=[dict(port=s['port'],early=s['rare'])for s in row['sources']]
    cost=item_prices.price(project,item)
    defaults=[dict(port=s['port'],early=s['rare'])for s in stock['sources']]
    identity=f'stock-item:{item:02d}'if sources==defaults and cost==stock['price_gold']else str(uuid.uuid5(uuid.NAMESPACE_URL,'new-horizons-item:'+json.dumps([item,cost,sources],sort_keys=True)))
    return validate(dict(kind='item',version=1,id=identity,name=stock['name'],item_id=item,price_gold=cost,sources=sources),project.rom)

def prepare(project,entry,use_locations=True):
    entry=validate(entry,project.rom)
    if type(use_locations)is not bool:raise ValueError('Invalid saved-port option.')
    trial=copy.deepcopy(project);item=entry['item_id']
    trial.item_price_edits=item_prices.validate(project.rom,[r for r in project.item_price_edits if r['id']!=item]+[dict(id=item,price_gold=entry['price_gold'])])
    if use_locations:
        desired={s['port']:s['early']for s in entry['sources']}
        edits=trial.item_edits
        for port,slots in enumerate(item_shops.values(project.rom,edits)):
            if item in slots and (port not in desired or (slots.index(item)==3)!=desired[port]):edits=item_shops.change(project.rom,edits,port,item,remove=True)
        for port,early in sorted(desired.items()):edits=item_shops.change(project.rom,edits,port,item,early=early)
        trial.item_edits=edits
        trial.item_seed=None;trial.item_blind=False;trial.item_special=False;trial.item_special_only=False
    trial.manifest()
    return trial

def apply(project,trial):
    for field in ('item_price_edits','item_edits','item_seed','item_blind','item_special','item_special_only'):setattr(project,field,copy.deepcopy(getattr(trial,field)))
