"""Per-port market offers; regional valuations and unrelated towns stay unchanged."""
import copy,statistics
from goods import MARKETS,TOWNS,COUNT
TABLE=0x228000
HELPER=0x22B200
SITE=0xE474A
NATIVE=bytes.fromhex('22 fa 01 c5')

def stock_offers(rom):
    result=[]
    for port in range(100):
        town=rom[TOWNS+port*37:TOWNS+(port+1)*37]
        market=rom[MARKETS+town[33]*128:MARKETS+(town[33]+1)*128]
        offers=[dict(good=market[110+i],economy_required=market[119+i]*10,kind='Regional',price=int.from_bytes(market[92+i*2:94+i*2],'little'))for i in range(9)if market[110+i]!=255]
        if town[26]!=255:offers.append(dict(good=town[26],economy_required=town[27]*10,kind='Specialty',price=int.from_bytes(town[24:26],'little')))
        result.append(offers)
    return result

def validate(rom,edits):
    if not isinstance(edits,list):raise ValueError('Invalid goods edits.')
    result=[];seen=set();stock=stock_offers(rom)
    for row in edits:
        if not isinstance(row,dict)or set(row)!={'port','offers'}or type(row['port'])is not int or not 0<=row['port']<100 or row['port']in seen:raise ValueError('Invalid or duplicate goods port.')
        seen.add(row['port']);offers=row['offers'];goods=set();regular=special=0
        if not isinstance(offers,list):raise ValueError('Invalid port offers.')
        for offer in offers:
            if not isinstance(offer,dict)or set(offer)!={'good','economy_required','kind','price'}:raise ValueError('Invalid good offer.')
            good=offer['good'];gate=offer['economy_required'];price=offer['price']
            if type(good)is not int or not 0<=good<COUNT or good in goods:raise ValueError('Duplicate or invalid good at a port.')
            if type(gate)is not int or not 0<=gate<=2550 or gate%10:raise ValueError('Required economy must be 0–2550 in steps of 10.')
            if type(price)is not int or not 1<=price<=65535:raise ValueError('Goods need a positive native base price.')
            goods.add(good)
            if offer['kind']=='Regional':regular+=1
            elif offer['kind']=='Specialty':special+=1
            else:raise ValueError('Invalid offer type.')
        if regular>9 or special>1:raise ValueError('A port has room for nine regular goods and one specialty. Remove another good first.')
        if offers!=stock[row['port']]:result.append(copy.deepcopy(row))
    return sorted(result,key=lambda row:row['port'])

def offers(rom,edits):
    result=stock_offers(rom)
    for row in validate(rom,edits):result[row['port']]=row['offers']
    return result

def change(rom,edits,port,good,gate=None,remove=False):
    if type(port)is not int or not 0<=port<100 or type(good)is not int or not 0<=good<COUNT:raise ValueError('Choose a trading port and good.')
    rows=offers(rom,edits);row=rows[port];found=next((o for o in row if o['good']==good),None)
    if remove:row[:]=[o for o in row if o['good']!=good]
    elif found:found['economy_required']=gate
    else:
        regular=sum(o['kind']=='Regional'for o in row)
        kind='Regional'if regular<9 else 'Specialty'
        if kind=='Specialty'and any(o['kind']=='Specialty'for o in row):raise ValueError('This port is full: nine regular goods and one specialty. Remove a good first.')
        prices=[o['price']for group in stock_offers(rom)for o in group if o['good']==good and o['kind']==kind]
        if not prices:prices=[o['price']for group in stock_offers(rom)for o in group if o['good']==good]
        row.append(dict(good=good,economy_required=gate,kind=kind,price=int(statistics.median(prices))))
    replacement=[e for e in edits if e['port']!=port]+[dict(port=port,offers=row)]
    return validate(rom,replacement)

def catalogue(rom,edits):
    from goods import catalogue as original
    result=original(rom)
    for good in result:good['sources']=[]
    for port,row in enumerate(offers(rom,edits)):
        economy=int.from_bytes(rom[TOWNS+port*37:TOWNS+port*37+2],'little')
        for o in row:result[o['good']]['sources'].append(dict(port=port,economy_required=o['economy_required'],available_at_start=economy>=o['economy_required'],kind=o['kind']))
    return result

def install(data,rom,edits):
    edits=validate(rom,edits)
    if not edits:return
    from expansion import Code,far_jump
    if data[SITE:SITE+4]!=NATIVE:raise ValueError('Unexpected native market setup.')
    if len(data)==0x200000:data.extend(b'\xff'*0x200000);data[0xffd7]=12
    tables=bytearray();changed_ports={e['port']for e in edits}
    for port,row in enumerate(offers(rom,edits)):
        town=TOWNS+port*37;region=rom[town+33]
        market=bytearray(rom[MARKETS+region*128:MARKETS+(region+1)*128])
        if port not in changed_ports:tables.extend(market);continue
        market[92:110]=bytes(18);market[110:119]=b'\xff'*9;market[119:128]=bytes(9)
        regular=[o for o in row if o['kind']=='Regional']
        for slot,o in enumerate(regular):
            market[92+slot*2:94+slot*2]=o['price'].to_bytes(2,'little');market[110+slot]=o['good'];market[119+slot]=o['economy_required']//10
        tables.extend(market)
    # Only changed specialties need town-ROM changes. Native SRAM initialization
    # copies these values on a new game; existing saves are not rewritten.
    originals=stock_offers(rom)
    for e in edits:
        original=next((o for o in originals[e['port']]if o['kind']=='Specialty'),None)
        new=next((o for o in e['offers']if o['kind']=='Specialty'),None)
        if original==new:continue
        at=TOWNS+e['port']*37;o=next((o for o in e['offers']if o['kind']=='Specialty'),None)
        data[at+24:at+28]=(o['price'].to_bytes(2,'little')+bytes([o['good'],o['economy_required']//10]))if o else bytes([0,0,255,0])
    # The market UI has a live town pointer. Derive its index without changing
    # town region IDs, shared valuation tables, AI prices or SRAM layouts.
    c=Code().emit('da af 0c e8 7e 38 e9 88 7e').branch(0x90,'fallback')
    c.emit('c9 74 0e').branch(0xB0,'fallback').emit('a2 00 00')
    c.mark('loop').emit('c9 00 00').branch(0xF0,'found').emit('38 e9 25 00').branch(0x90,'fallback').emit('e8').branch(0x80,'loop')
    c.mark('found').emit('8a'+(' 0a'*7)+' 18 69 00 80 85 00 a9 e2 00 85 02 fa 6b')
    c.mark('fallback').emit('fa 5c fa 01 c5')
    for at,raw in [(TABLE,bytes(tables)),(HELPER,c.finish())]:
        if data[at:at+len(raw)]!=b'\xff'*len(raw):raise ValueError('Goods data overlaps another patch.')
        data[at:at+len(raw)]=raw
    data[SITE:SITE+4]=far_jump(0x22,HELPER)


SHUFFLE_MODES=('normal','specialty','all')

def validate_shuffle(config):
    from character_mods import validate_seed
    if not isinstance(config,dict)or not {'seed','mode'}<=set(config)or set(config)-{'seed','mode','blind'}or config['mode']not in SHUFFLE_MODES or type(config.get('blind',False))is not bool:
        raise ValueError('Choose normal goods, specialty goods or all goods.')
    result=dict(seed=validate_seed(config['seed'])if config['seed']is not None else None,mode=config['mode'])
    if config.get('blind',False):result['blind']=True
    return result

def seeded_shuffle(rom,seed,mode='normal',blind=False):
    """Preserve offer counts, specialties, prices per good and economy gates."""
    import random
    from character_mods import validate_seed
    validate_shuffle(dict(seed=seed,mode=mode,blind=blind));validate_seed(seed)
    rng=random.Random('NH-trade-v1:'+seed+':'+mode+(':blind'if blind else ''));rows=stock_offers(rom)
    kinds=('Regional','Specialty')if mode=='all'else ('Specialty',)if mode=='specialty'else ('Regional',)
    for kind in kinds:
        positions=[(p,i)for p,row in enumerate(rows)for i,o in enumerate(row)if o['kind']==kind]
        for _ in range(len(positions)*60):
            if len(positions)<2:break
            (a,x),(b,y)=rng.sample(positions,2);first,second=rows[a][x],rows[b][y]
            if a!=b and (any(o['good']==second['good']for o in rows[a])or any(o['good']==first['good']for o in rows[b])):continue
            for field in ('good','price'):first[field],second[field]=second[field],first[field]
    return validate(rom,[dict(port=p,offers=row)for p,row in enumerate(rows)])
