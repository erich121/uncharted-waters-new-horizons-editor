"""Current-to-preset values only, without descriptions or blind destinations."""
import json


def changes(current,target):
    from ports import PORT_NAMES
    from sailors import decode_sailors,ATTRIBUTES,LEVEL_FIELDS,skill_names
    from economy import values as economies
    from trade_goods import offers
    from item_shops import values as shops
    from goods import catalogue as goods
    from items import catalogue as items
    from fleet_difficulty import NATIONS,ROLES,SOURCES
    out=[]
    def value(v):
        if type(v)is bool:return 'On'if v else 'Off'
        if v is None:return 'None'
        if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False)
        return str(v)if v!=''else '(empty)'
    def add(label,a,b,hidden=False):
        if a!=b:out.append(label+(': updated (blind)'if hidden else ': '+value(a)+' → '+value(b)))
    def blind(v):
        if isinstance(v,dict):return any(('blind'in k and x is True)or blind(x)for k,x in v.items())
        if isinstance(v,list):return any(blind(x)for x in v)
        return False
    def config(label,a,b,hidden=False):
        if a==b:return
        if isinstance(a,dict)and isinstance(b,dict):
            for key in sorted(set(a)|set(b)):
                if key!='previous':config(label+' / '+key.replace('_',' '),a.get(key),b.get(key),hidden)
        else:add(label,a,b,hidden)
    fields={'name':'Name','hull':'Hull strength','power':'Sailing power','turning':'Turning','max_guns':'Maximum guns','min_crew':'Minimum sailors','max_crew':'Maximum crew spaces','price_gold':'Price (gold)','capacity':'Total capacity','factory_guns':'Starting guns','factory_crew':'Starting crew spaces','factory_cargo':'Starting cargo'}
    hidden_ports=blind(current.shipbuilding_shuffle)or blind(target.shipbuilding_shuffle)
    for slot in range(max(len(current.ships),len(target.ships))):
        a=current.ships[slot]if slot<len(current.ships)else None;b=target.ships[slot]if slot<len(target.ships)else None
        label=f'Ship {slot+1:02d}'+(' '+a['name']if a else '')
        if a is None or b is None:
            add(label,a['name']if a else None,b['name']if b else None)
            if b is None:continue
            a={}
        for key,title in fields.items():
            if not a and key=='name':continue
            add(label+' / '+title,a.get(key),b.get(key))
        old_family=current.library_bases.get(slot,a.get('base_hull',slot))if a else None
        new_family=target.library_bases.get(slot,b.get('base_hull',slot))
        add(label+' / Visual family',current.original[old_family]['name']if old_family is not None else None,target.original[new_family]['name'])
        ao=current.all_offers()[slot]if a else dict(ports=[],industry=None);bo=target.all_offers()[slot]
        add(label+' / Build ports',', '.join(PORT_NAMES[p]for p in ao['ports']),', '.join(PORT_NAMES[p]for p in bo['ports']),hidden_ports)
        add(label+' / Required industry',ao['industry'],bo['industry'])
        if slot<len(current.ships):
            if current.portrait_raw(slot)!=target.portrait_raw(slot):out.append(label+' / Portrait: will change')
            from ship_descriptions import text
            add(label+' / Shipyard text',text(current,slot),text(target,slot))
        else:
            from ship_descriptions import text
            out.append(label+' / Shipyard text: '+text(target,slot))
            out.append(label+' / Portrait: '+('embedded custom portrait'if slot in target.portraits else 'original visual family portrait'))
    a=current.manifest();b=target.manifest()
    if a['character_edits']!=b['character_edits']or a['free_agent_shuffle']!=b['free_agent_shuffle']:
        from character_mods import apply
        def records(p):
            data=bytearray(p.rom);apply(data,p.rom,p.character_edits,p.free_agent_shuffle)
            rows=decode_sailors(data)
            for e in p.effective_character_edits():rows[e['id']][e['field']]=e['value']
            return rows
        hidden=blind(current.free_agent_shuffle)or blind(target.free_agent_shuffle)
        changed=0
        for old,new in zip(records(current),records(target)):
            keys=('name','starting_port')+ATTRIBUTES+LEVEL_FIELDS+('skills',)
            if not any(old.get(k)!=new.get(k)for k in keys):continue
            changed+=1
            if hidden:continue
            for key in keys:
                x=old.get(key);y=new.get(key)
                if key=='skills':x=', '.join(skill_names(x))or 'None';y=', '.join(skill_names(y))or 'None'
                if key=='starting_port':x=PORT_NAMES[x]if x is not None and x<len(PORT_NAMES)else x;y=PORT_NAMES[y]if y is not None and y<len(PORT_NAMES)else y
                add(f'Character {old["id"]+1:03d} {old["name"]} / '+key.replace('_',' ').capitalize(),x,y)
        if hidden and changed:out.append(f'Characters: {changed} records will change (blind)')
    for old,new in zip(economies(current.rom,current.economy_edits),economies(target.rom,target.economy_edits)):
        for key,label in (('economy','Goods economy'),('industry','Shipbuilding economy')):add(PORT_NAMES[old['port']]+' / '+label,old[key],new[key])
    good_names={r['id']:r['name']for r in goods(current.rom)};item_names={r['id']:r['name']for r in items(current.rom)}
    for label,old,new,hidden,names in (
        ('Goods',offers(current.rom,current.goods_edits),offers(target.rom,target.goods_edits),blind(current.goods_shuffle)or blind(target.goods_shuffle),good_names),
        ('Items',shops(current.rom,current.item_edits),shops(target.rom,target.item_edits),current.item_blind or target.item_blind,item_names)):
        count=0
        for port,(x,y)in enumerate(zip(old,new)):
            if x==y:continue
            count+=1
            if hidden:continue
            if label=='Items':
                for i,(u,v)in enumerate(zip(x,y)):add(PORT_NAMES[port]+' / '+('Early-morning item'if i==3 else f'Item {i+1}'),names.get(u,'None'),names.get(v,'None'))
            else:
                for i in range(max(len(x),len(y))):
                    u=x[i]if i<len(x)else {};v=y[i]if i<len(y)else {}
                    prefix=PORT_NAMES[port]+f' / Good {i+1}'
                    add(prefix,names.get(u.get('good'),'None'),names.get(v.get('good'),'None'))
                    for key in ('price','economy_required','kind'):add(prefix+' / '+key.replace('_',' '),u.get(key),v.get(key))
        if hidden and count:out.append(label+f': {count} port lists will change (blind)')
    for n,(old,new)in enumerate(zip(current.fleet_rules,target.fleet_rules)):
        for r,(x,y)in enumerate(zip(old,new)):
            for i,(u,v)in enumerate(zip(x,y)):
                old_name=f'{u+1:02d} '+current.ships[u]['name']if u>=0 else 'No change';new_name=f'{v+1:02d} '+target.ships[v]['name']if v>=0 else 'No change'
                add(f'{NATIONS[n]} / {ROLES[r]} / replacing {current.original[SOURCES[i]]["name"]}',old_name,new_name)
    from starting_gold import bars
    add('Starting gold (bars)','Original'if current.starting_gold is None else bars(current.starting_gold),'Original'if target.starting_gold is None else bars(target.starting_gold))
    for key,label in [('discovery_easy','All discovery difficulties: 10'),('instant_shipbuilding','Instant shipbuilding'),('fifty_year_campaign','50-year campaign'),('discovery_rewrites','Rewritten discovery descriptions'),('repair_safeguard','Repair Safeguard'),('fleet_control','Fleet Control'),('fleet_difficulty','Custom Fleets'),('custom_discoveries','Manual discovery editing'),('custom_ships','Manual ship editing'),('custom_characters','Manual character editing'),('custom_mates','Manual mate editing'),('custom_captains','Manual fleet captain editing'),('custom_economy','Manual economy editing'),('custom_goods','Manual goods editing'),('custom_items','Manual item editing')]:add(label,getattr(current,key),getattr(target,key))
    for key,label in [('free_agent_shuffle','People randomizer'),('goods_shuffle','Goods randomizer'),('shipbuilding_shuffle','Shipbuilding randomizer')]:config(label,getattr(current,key),getattr(target,key),blind(getattr(current,key))or blind(getattr(target,key)))
    for key in ('item_seed','item_blind','item_special','item_special_only'):add(key.replace('_',' ').capitalize(),getattr(current,key),getattr(target,key),key=='item_seed'and(current.item_blind or target.item_blind))
    for slot in sorted(set(current.discovery_entries)|set(target.discovery_entries)):
        old=current.discovery_entries.get(slot);new=target.discovery_entries.get(slot)
        if old==new:continue
        prefix=f'Discovery {slot+1:02d}'
        for key in ('name','description','category','difficulty'):add(prefix+' / '+key,(old or {}).get(key,'Original'),(new or {}).get(key,'Original'))
        if any((old or {}).get(key)!=(new or {}).get(key)for key in ('tiles','palette')):out.append(prefix+' / Artwork: will change')
    from item_prices import price
    from items import catalogue
    for row in catalogue(current.rom):add(row['name']+' / Price (gold)',price(current,row['id']),price(target,row['id']))
    return out or ['No settings will change.']
