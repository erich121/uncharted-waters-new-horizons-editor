"""Stock-USA ship editing plus1..5 independent additive hulls; no save writes."""
import hashlib,json,struct,zipfile,copy
from decimal import Decimal,InvalidOperation
from pathlib import Path

ROM_SHA='64bc4707f422661a66618088887e2363a5f896ea683c58984fffd96dd21ab5f0'
TOOL_VERSION='1.0.1'
MODEL_BASE=0x8cbb6
SPEC_BASE=0x8ce27
FIELDS=('name','hull','turning','power','max_guns','min_crew','max_crew','price_gold')
EDIT_FIELDS=FIELDS+('capacity','factory_cargo')
UPDATE_FIELDS=EDIT_FIELDS+('yard_cargo',)
EXTRA_FIELDS=('base_hull','capacity','industry','factory_guns','factory_crew','ports')
CAPITALS=(0,1,2,8,29,33,77)

def ports(rom):
    from ports import PORT_NAMES
    return [dict(id=i,name=PORT_NAMES[i],industry=int.from_bytes(rom[0x8da83+i*37:0x8da85+i*37],'little'),
        group=rom[0x8da7f+i*37+34],capital=i in CAPITALS) for i in range(100)]

def validate_extra(s,rom,allow_locked_ports=()):
    if not isinstance(s,dict):raise ValueError('Each added ship must be a ship record.')
    expected=set(decode(rom)[0])|{'base_hull','ports'}
    if set(s)!=expected:raise ValueError('Unknown or missing added-ship fields.')
    if type(s['id'])is not int or not 25<=s['id']<30:raise ValueError('Added ship ID outside25..29.')
    if type(s['base_hull'])is not int or not 0<=s['base_hull']<25:raise ValueError('Choose an original hull for graphics and build-time family.')
    dummy=dict(s);dummy.pop('base_hull');dummy.pop('ports')
    # Added ships have fully editable allocations; apply the common bounds without stock grandfathering.
    validate(dummy,dict(dummy))
    for k,lo,hi in [('capacity',1,2000),('industry',0,1000),('factory_guns',0,150),('factory_crew',1,500)]:
        if type(s[k])is not int or not lo<=s[k]<=hi:raise ValueError(f'{k.replace("_"," ")} must be {lo}–{hi}.')
    if s['industry']%10:raise ValueError('Industry requirement must be a multiple of10.')
    if s['factory_guns']>s['max_guns']or not s['min_crew']<=s['factory_crew']<=s['max_crew']:
        raise ValueError('Factory guns/crew must fit the ship limits.')
    cargo=s['capacity']-s['factory_guns']-s['factory_crew']
    if cargo<0 or s['factory_cargo']!=cargo:raise ValueError('Capacity must cover factory guns and crew; remaining space is cargo.')
    ps=s['ports']
    if not isinstance(ps,list)or not ps or any(type(p)is not int or not 0<=p<100 for p in ps)or len(set(ps))!=len(ps):raise ValueError('Choose at least one valid port, without duplicates.')
    catalog=ports(rom)
    for p in ps:
        if catalog[p]['group']>=11:raise ValueError('This port has no supported shipyard stock group.')
        if catalog[p]['capital']and p not in allow_locked_ports and s['industry']>catalog[p]['industry']:
            raise ValueError(f'{catalog[p]["name"]} cannot reach industry {s["industry"]}; its fixed starting industry is {catalog[p]["industry"]}.')

def sha(data):return hashlib.sha256(data).hexdigest()

def read_stock(path):
    path=Path(path)
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path)as z:
            files=[n for n in z.namelist()if n.lower().endswith(('.sfc','.smc'))and not n.endswith('/')]
            if len(files)!=1:raise ValueError('The ZIP must contain exactly one .sfc or .smc game file.')
            if z.getinfo(files[0]).file_size not in (0x200000,0x200200):raise ValueError('Expected the stock 2 MB USA game.')
            raw=z.read(files[0])
    else:raw=path.read_bytes()
    header=raw[:512]if len(raw)==0x200200 else b''
    rom=raw[len(header):]
    if len(rom)!=0x200000 or sha(rom)!=ROM_SHA:
        raise ValueError('This version supports only the original USA New Horizons ROM. Patched games and other revisions are not supported yet.')
    return rom,header

def decode(rom):
    rows=[]
    for i in range(25):
        t=rom[MODEL_BASE+i*25:MODEL_BASE+(i+1)*25];s=rom[SPEC_BASE+i*12:SPEC_BASE+(i+1)*12]
        rows.append(dict(id=i,name=t[:18].split(b'\0')[0].decode('ascii'),hull=s[1],turning=s[2],power=s[3],
            max_guns=s[8],min_crew=s[5],max_crew=s[4]*10,price_gold=struct.unpack_from('<H',s,10)[0]*10,
            capacity=struct.unpack_from('<H',s,6)[0],industry=s[0]*10,
            factory_guns=t[20],factory_crew=struct.unpack_from('<H',t,21)[0],factory_cargo=struct.unpack_from('<H',t,23)[0]))
    return rows

def validate(row,original):
    if set(row)!=set(original):raise ValueError('Unknown or missing ship fields.')
    for key in set(original)-set(EDIT_FIELDS):
        if row[key]!=original[key]:raise ValueError(f'{key} is read-only for original ships.')
    name=row['name']
    if not isinstance(name,str)or not name.strip()or len(name)>17 or '%'in name or any(ord(c)<32 or ord(c)>126 for c in name):
        raise ValueError('Ship names need 1–17 printable English characters, without %.')
    ranges=dict(hull=(1,100),turning=(1,100),power=(1,100),max_guns=(0,150),min_crew=(1,255),max_crew=(10,500),price_gold=(10,320000),capacity=(1,2000),factory_cargo=(0,2000))
    for key,(low,high)in ranges.items():
        if type(row[key])is not int or not low<=row[key]<=high:raise ValueError(f'{key.replace("_"," ")} must be a whole number from {low} to {high}.')
    if row['max_crew']%10:raise ValueError('Maximum crew must be a multiple of 10.')
    if row['price_gold']%10:raise ValueError('The base price must be a multiple of 10 gold (0.001 bar).')
    if row['min_crew']>row['max_crew']:raise ValueError('Minimum crew cannot exceed maximum crew.')
    if row['max_guns']!=original['max_guns'] and row['max_guns']<original['factory_guns']:
        raise ValueError('The gun limit cannot be below the factory gun allocation.')
    if row['max_crew']!=original['max_crew'] and row['max_crew']<original['factory_crew']:
        raise ValueError('The crew limit cannot be below the existing factory crew allocation.')
    if row['capacity']!=row['factory_guns']+row['factory_crew']+row['factory_cargo']:
        raise ValueError('Total capacity must equal factory guns + crew spaces + cargo.')
    if row['capacity']<row['max_guns']+row['max_crew']:
        raise ValueError('Total capacity must cover the maximum gun and crew spaces; shipyard cargo cannot be negative.')

def fit_values(previous,values):
    values=copy.deepcopy(values);yard=values.pop('yard_cargo',None)
    if yard is not None and (type(yard)is not int or yard<0):raise ValueError('Shipyard cargo capacity needs a nonnegative whole number.')
    row=copy.deepcopy(previous);row.update(values)
    for key in ('capacity','factory_guns','factory_crew','factory_cargo'):
        if type(row[key])is not int:raise ValueError(key.replace('_',' ')+' needs a whole number.')
    cargo_changed='factory_cargo'in values and row['factory_cargo']!=previous['factory_cargo']
    capacity_changed='capacity'in values and row['capacity']!=previous['capacity']
    used=row['factory_guns']+row['factory_crew']
    if yard is not None:
        wanted=yard+row['max_guns']+row['max_crew']
        if not capacity_changed and not cargo_changed:
            row['capacity']=wanted;capacity_changed=wanted!=previous['capacity']
        elif row['capacity']!=wanted:raise ValueError('Shipyard cargo capacity disagrees with total capacity and gun/crew limits.')
    if cargo_changed and not capacity_changed:row['capacity']=used+row['factory_cargo']
    elif capacity_changed and cargo_changed:
        if row['capacity']!=used+row['factory_cargo']:raise ValueError('Cargo and total capacity disagree with the factory guns/crew.')
    else:row['factory_cargo']=row['capacity']-used
    return row

def price_from_bars(value):
    try:
        amount=Decimal(str(value))*10000
        if not amount.is_finite()or amount!=amount.to_integral_value():raise ValueError()
        return int(amount)
    except (InvalidOperation,ValueError,OverflowError):raise ValueError('Enter a valid price in gold bars, in steps of 0.001 bar.')

def ips(base,modified):
    output=bytearray(b'PATCH');at=0
    while at<len(modified):
        if at<len(base)and base[at]==modified[at]:at+=1;continue
        start=at
        while at<len(modified)and (at>=len(base)or base[at]!=modified[at])and at-start<65535:at+=1
        payload=modified[start:at];output+=start.to_bytes(3,'big')+len(payload).to_bytes(2,'big')+payload
    return bytes(output+b'EOF')

def apply_ips(base,patch):
    data=bytearray(base);at=5
    if patch[:5]!=b'PATCH':raise ValueError('Invalid IPS.')
    while patch[at:at+3]!=b'EOF':
        offset=int.from_bytes(patch[at:at+3],'big');n=int.from_bytes(patch[at+3:at+5],'big');at+=5
        if n:payload=patch[at:at+n];at+=n
        else:
            n=int.from_bytes(patch[at:at+2],'big');payload=patch[at+2:at+3]*n;at+=3
        if offset+len(payload)>len(data):data.extend(b'\0'*(offset+len(payload)-len(data)))
        data[offset:offset+len(payload)]=payload
    return bytes(data)

class ShipProject:
    def __init__(self,path):
        self.source=Path(path).resolve();self.rom,self.header=read_stock(self.source)
        self.original=decode(self.rom);self.ships=[dict(s)for s in self.original]
        self.project_path=None;self.repair_safeguard=False;self.fleet_control=False;self.fleet_difficulty=False;self.portraits={}
        from fleet_difficulty import preset
        self.fleet_rules=preset()
        self.shipbuilding_shuffle=__import__('shipbuilding_shuffle').default()
        self.goods_shuffle=dict(seed=None,mode='normal')
        self.item_special_only=False;self.item_blind=False;self.item_special=False;self.item_seed=None;self.item_edits=[];self.custom_items=False;self.custom_ships=False;self.custom_mates=False;self.custom_captains=False;self.custom_goods=False;self.custom_economy=False;self.economy_edits=[];self.goods_edits=[];self.character_edits=[];self.free_agent_shuffle=dict(enabled=False,blind=False,seed='0000')
        catalog=ports(self.rom)
        self.stock_availability=[dict(ports=[p['id']for p in catalog if i in self.rom[0x8fae7+p['group']*8:0x8faef+p['group']*8]],industry=s['industry'])for i,s in enumerate(self.original)]
        self.original_availability=copy.deepcopy(self.stock_availability)

    def economy_rom(self):
        from economy import projected
        return projected(self.rom,self.economy_edits)

    def update(self,i,values):
        if type(i)is not int or not 0<=i<len(self.ships):raise ValueError('Invalid ship ID.')
        if i>=25:
            if set(values)-set(UPDATE_FIELDS+EXTRA_FIELDS):raise ValueError('Unknown added-ship fields.')
            row=fit_values(self.ships[i],values)
            retained=self.ships[i]['ports']if row['industry']==self.ships[i]['industry']else []
            validate_extra(row,self.economy_rom(),retained)
            offers=self.all_offers();offers[i]=dict(ports=row['ports'],industry=row['industry']);self.validate_offer_counts(offers)
            self.ships[i]=row;return
        if set(values)-set(UPDATE_FIELDS+('ports','industry')):raise ValueError('Unknown editable fields.')
        values=copy.deepcopy(values);offer=copy.deepcopy(self.original_availability[i])
        for k in ('ports','industry'):
            if k in values:offer[k]=values.pop(k)
        self.validate_availability(i,offer)
        row=fit_values(self.ships[i],values);validate(row,self.original[i])
        offers=self.all_offers();offers[i]=offer;self.validate_offer_counts(offers)
        if offer!=self.original_availability[i]:self.shipbuilding_shuffle=__import__('shipbuilding_shuffle').default()
        self.ships[i]=row;self.original_availability[i]=offer

    def validate_availability(self,i,offer,rom=None,edited_ports=None):
        if not isinstance(offer,dict)or set(offer)!={'ports','industry'}:raise ValueError('Invalid original ship availability.')
        industry=offer['industry'];ps=offer['ports']
        if type(industry)is not int or not 0<=industry<=1000 or industry%10:raise ValueError('Industry must be 0–1000 in steps of 10.')
        if not isinstance(ps,list)or any(type(p)is not int or not 0<=p<100 for p in ps)or len(set(ps))!=len(ps):raise ValueError('Choose valid ports without duplicates.')
        catalog=ports(self.economy_rom()if rom is None else rom);stock=self.stock_availability[i]
        edited_ports=set()if edited_ports is None else edited_ports
        for p in ps:
            if catalog[p]['group']>=11:raise ValueError('Port has no supported shipyard.')
            unchanged=(p in stock['ports']and industry<=stock['industry'])or(p in self.original_availability[i]['ports']and industry==self.original_availability[i]['industry'])
            if catalog[p]['capital']and p not in edited_ports and industry>catalog[p]['industry']and not unchanged:raise ValueError(f"{catalog[p]['name']} cannot reach industry {industry}; its industry is fixed at {catalog[p]['industry']}.")
        offer['ports']=sorted(ps)

    def availability_changes(self):
        result=[]
        for i,o in enumerate(self.original_availability):
            self.validate_availability(i,o)
            if o!=self.stock_availability[i]:result.append(dict(id=i,**copy.deepcopy(o)))
        return result

    def all_offers(self):
        return copy.deepcopy(self.original_availability)+[dict(ports=s['ports'],industry=s['industry'])for s in self.ships[25:]]

    def validate_offer_counts(self,offers=None):
        offers=self.all_offers()if offers is None else offers
        for port in ports(self.rom):
            # Native menu storage was already verified for sixteen visible offers.
            if sum(port['id']in o['ports']for o in offers)>16:raise ValueError(f"{port['name']} exceeds the 16-ship new-build menu limit.")

    def changes(self):
        if not 25<=len(self.ships)<=30:raise ValueError('You may add up to five ships.')
        for i,row in enumerate(self.ships):
            if i<25:validate(row,self.original[i])
            else:validate_extra(row,self.economy_rom(),CAPITALS)
        return [dict(id=i,field=k,before=self.original[i][k],after=s[k])for i,s in enumerate(self.ships[:25])for k in EDIT_FIELDS if s[k]!=self.original[i][k]]

    def add_ship(self,base_hull=10):
        if len(self.ships)>=30:raise ValueError('This version supports five added ships.')
        if type(base_hull)is not int or not 0<=base_hull<25:raise ValueError('Invalid original hull.')
        s=dict(self.ships[base_hull]);s.update(id=len(self.ships),name=f'New Ship {len(self.ships)-24}',base_hull=base_hull,ports=[0],industry=0)
        # Some stock factory crews exceed their refit cap; new ships must be internally consistent.
        s['max_crew']=max(s['max_crew'],((s['factory_crew']+9)//10)*10)
        s['factory_crew']=max(s['factory_crew'],s['min_crew'])
        s['factory_cargo']=s['capacity']-s['factory_guns']-s['factory_crew']
        s['capacity']=s['factory_guns']+s['factory_crew']+s['factory_cargo']
        validate_extra(s,self.economy_rom());self.validate_offer_counts(self.all_offers()+[dict(ports=s['ports'],industry=s['industry'])]);self.ships.append(s);return s['id']

    def remove_ship(self,i):
        if type(i)is not int or not 25<=i<len(self.ships):raise ValueError('Only added ships can be removed.')
        self.ships.pop(i)
        self.fleet_rules=[[[(-1 if target==i else target-1 if target>i else target)for target in role]for role in nation]for nation in self.fleet_rules]
        self.portraits={n-(n>i):raw for n,raw in self.portraits.items()if n!=i}
        for n,s in enumerate(self.ships):s['id']=n

    def portrait_raw(self,i):
        if type(i)is not int or not 0<=i<len(self.ships):raise ValueError('Invalid portrait ship ID.')
        if i in self.portraits:return self.portraits[i]
        from portraits import original_raw
        return original_raw(self.rom,i if i<25 else self.ships[i]['base_hull'])

    def set_portrait(self,i,raw):
        if type(i)is not int or not 0<=i<len(self.ships):raise ValueError('Invalid portrait ship ID.')
        from portraits import validate_raw
        validate_raw(raw);self.portraits[i]=raw

    def restore_portrait(self,i):
        self.portraits.pop(i,None)

    def update_character(self,i,values):
        from character_mods import validate_edits
        from sailors import ATTRIBUTES,MATE_IDS,CAPTAIN_IDS,EDITABLE_FIELDS
        if type(i)is not int or i not in MATE_IDS+CAPTAIN_IDS or not isinstance(values,dict)or any(k not in EDITABLE_FIELDS for k in values):
            raise ValueError('Only existing mate/captain attributes and skills can be edited.')
        entries=[dict(e)for e in self.character_edits if e['id']!=i or e['field']not in values]
        entries += [dict(id=i,field=k,value=v)for k,v in values.items()]
        self.character_edits=validate_edits(self.rom,entries,self.free_agent_shuffle)

    def set_free_agent_shuffle(self,enabled,seed,blind=False,names=False,captain_names=False,mate_stats=False,captain_stats=False,ports=True,name_parts=True,stat_budget=True,mate_skills=False,captain_skills=False):
        from character_mods import validate_shuffle
        config=dict(enabled=enabled,seed=seed,blind=blind,names=names,captain_names=captain_names,mate_stats=mate_stats,captain_stats=captain_stats,ports=ports,mate_skills=mate_skills,captain_skills=captain_skills)
        if names or captain_names:config['name_parts']=name_parts
        if mate_stats or captain_stats:config['stat_budget']=stat_budget
        self.free_agent_shuffle=validate_shuffle(self.rom,config)

    def set_shipbuilding_shuffle(self,seed,blind=False):
        from shipbuilding_shuffle import plan
        changes=plan(self,seed,blind);candidate=copy.copy(self)
        for key,value in changes.items():setattr(candidate,key,value)
        candidate.build()
        self.original_availability=changes['original_availability'];self.shipbuilding_shuffle=changes['shipbuilding_shuffle']

    def clear_shipbuilding_shuffle(self):
        if self.shipbuilding_shuffle['seed']is not None:
            previous=copy.deepcopy(self.shipbuilding_shuffle['previous']);self.validate_offer_counts(previous+self.all_offers()[25:])
            self.original_availability=previous
        self.shipbuilding_shuffle=__import__('shipbuilding_shuffle').default()

    def set_goods_shuffle(self,seed,mode='normal',blind=False):
        from trade_goods import seeded_shuffle,validate_shuffle
        edits=seeded_shuffle(self.rom,seed,mode,blind)
        self.goods_edits=edits;self.goods_shuffle=validate_shuffle(dict(seed=seed,mode=mode,blind=blind))

    def set_item_shuffle(self,seed,blind=False,include_special=False,special_only=False):
        from item_shops import seeded_shuffle
        edits=seeded_shuffle(self.rom,seed,blind,include_special,special_only)
        self.item_edits=edits;self.item_seed=seed;self.item_blind=blind;self.item_special=include_special;self.item_special_only=special_only

    def effective_character_edits(self):
        # Manual-edit locks never disable values set by presets or earlier edits.
        from character_mods import shuffled_stats,shuffled_skills
        merged={(e['id'],e['field']):e for e in shuffled_stats(self.rom,self.free_agent_shuffle)+shuffled_skills(self.rom,self.free_agent_shuffle)}
        merged.update({(e['id'],e['field']):e for e in self.character_edits})
        from character_mods import validate_edits
        return validate_edits(self.rom,list(merged.values()))

    def character_record(self,i):
        from sailors import decode_sailors,skill_names
        from character_mods import port_shuffle
        from ports import PORT_NAMES
        records=decode_sailors(self.rom);row=records[i]
        from character_mods import shuffled_names
        row.update(shuffled_names(self.rom,self.free_agent_shuffle).get(i,{}))
        row.update({e['field']:e['value']for e in self.effective_character_edits() if e['id']==i})
        row['skill_names']=skill_names(row['skills'])
        if row['role']=='Free agent':
            row['starting_port']=port_shuffle(self.rom,self.free_agent_shuffle)[i]
            row['starting_port_name']=PORT_NAMES[row['starting_port']]
        return row

    def manifest(self):
        from portraits import pack,unpack
        if any(type(v)is not bool for v in (self.item_special_only,self.item_blind,self.item_special,self.custom_items,self.custom_ships,self.custom_economy,self.custom_goods,self.custom_mates,self.custom_captains)):raise ValueError('Invalid custom world setting.')
        embedded=pack(self.portraits);unpack(embedded,len(self.ships))
        from character_mods import validate_edits,validate_shuffle
        from fleet_difficulty import validate_rules
        if self.item_seed is not None:__import__('character_mods').validate_seed(self.item_seed)
        return dict(character_edits=validate_edits(self.rom,self.character_edits,self.free_agent_shuffle),free_agent_shuffle=validate_shuffle(self.rom,self.free_agent_shuffle),gameplay=dict(fleet_difficulty=self.fleet_difficulty,fleet_rules=validate_rules(self.fleet_rules,self.ships)),portraits=embedded,format='new-horizons-ship-project',version=19,shipbuilding_shuffle=__import__('shipbuilding_shuffle').validate(self.shipbuilding_shuffle),goods_shuffle=__import__('trade_goods').validate_shuffle(self.goods_shuffle),item_special_only=self.item_special_only,item_blind=self.item_blind,item_special=self.item_special,item_seed=self.item_seed,item_edits=__import__('item_shops').validate(self.rom,self.item_edits),custom_items=self.custom_items,custom_ships=self.custom_ships,custom_mates=self.custom_mates,custom_captains=self.custom_captains,custom_goods=self.custom_goods,custom_economy=self.custom_economy,economy_edits=__import__('economy').validate(self.rom,self.economy_edits),goods_edits=__import__('trade_goods').validate(self.rom,self.goods_edits),base_sha256=ROM_SHA,original_availability=self.availability_changes(),fixes=dict(repair_safeguard=self.repair_safeguard,fleet_control=self.fleet_control),
            edits=[dict(id=c['id'],field=c['field'],value=c['after'])for c in self.changes()],added_ships=copy.deepcopy(self.ships[25:]))

    def save_project(self,path):
        path=Path(path).resolve()
        if path.suffix.lower()!='.json':raise ValueError('Save projects as .json files; game and save files cannot be replaced.')
        if path==self.source:raise ValueError('A project cannot replace the source game.')
        if path.exists():
            backup=path.with_suffix(path.suffix+'.bak')
            # Keep the immediately previous project; no game/save is written here.
            backup.write_bytes(path.read_bytes())
        path.write_text(json.dumps(self.manifest(),indent=2)+'\n',encoding='utf-8');self.project_path=path

    def load_project(self,path):
        path=Path(path).resolve();m=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(m,dict):raise ValueError('Unsupported project: expected a ship project object.')
        keys={'format','version','base_sha256','edits'}|({'added_ships'}if m.get('version')in (2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)else set())|({'fixes'}if m.get('version')in (3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)else set())|({'original_availability'}if m.get('version')in (4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19) else set())|({'portraits'}if m.get('version')in (6,7,8,9,10,11,12,13,14,15,16,17,18,19) else set())|({'character_edits','free_agent_shuffle'}if m.get('version')in (7,8,9,10,11,12,13,14,15,16,17,18,19) else set())|({'gameplay'}if m.get('version')in (8,9,10,11,12,13,14,15,16,17,18,19) else set())|({'goods_edits'}if m.get('version')in (12,13,14,15,16,17,18,19) else set())|({'economy_edits'}if m.get('version')in (13,14,15,16,17,18,19) else set())|({'custom_economy','custom_goods','custom_mates','custom_captains'}if m.get('version')in (14,15,16,17,18,19) else set())|({'custom_ships'}if m.get('version')in (15,16,17,18,19) else set())|({'custom_items','item_edits'}if m.get('version')in (16,17,18,19) else set())|({'item_seed','item_blind','item_special','item_special_only'}if m.get('version')in (17,18,19) else set())
        if m.get('version')in (18,19):keys|={'goods_shuffle'}
        if m.get('version')==19:keys|={'shipbuilding_shuffle'}
        if set(m)!=keys or m['format']!='new-horizons-ship-project'or type(m['version'])is not int or m['version']not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)or m['base_sha256']!=ROM_SHA or not isinstance(m['edits'],list):
            raise ValueError('Unsupported project or ROM revision.')
        from economy import validate as validate_economy,projected
        economy_edits=validate_economy(self.rom,m.get('economy_edits',[]))
        custom_economy=m.get('custom_economy',bool(economy_edits))
        if type(custom_economy)is not bool:raise ValueError('Invalid custom economy setting.')
        economy_rom=projected(self.rom,economy_edits)
        fixes=m.get('fixes',dict(repair_safeguard=True))
        expected={'repair_safeguard','fleet_control'}if m['version']>=5 else {'repair_safeguard'}
        if not isinstance(fixes,dict)or set(fixes)!=expected or any(type(v)is not bool for v in fixes.values()):raise ValueError('Invalid optional fix settings.')
        fleet_control=fixes.get('fleet_control',False)
        gameplay=m.get('gameplay',dict(fleet_difficulty=False))
        expected_gameplay={'fleet_difficulty','fleet_rules'}if m['version']>=9 else {'fleet_difficulty'}
        if not isinstance(gameplay,dict)or set(gameplay)!=expected_gameplay or type(gameplay['fleet_difficulty'])is not bool:raise ValueError('Invalid gameplay settings.')
        fleet_difficulty=gameplay['fleet_difficulty']
        rows=[dict(s)for s in self.original];seen=set()
        for e in m['edits']:
            if not isinstance(e,dict)or set(e)!={'id','field','value'}or type(e['id'])is not int or not 0<=e['id']<25 or e['field']not in EDIT_FIELDS:
                raise ValueError('Invalid project edit.')
            key=(e['id'],e['field'])
            if key in seen:raise ValueError('Duplicate project edit.')
            seen.add(key);rows[e['id']][e['field']]=e['value']
        for i,row in enumerate(rows):validate(row,self.original[i])
        added=m.get('added_ships',[])
        if not isinstance(added,list)or len(added)>5:raise ValueError('Project supports at most five added ships.')
        for n,s in enumerate(added):
            validate_extra(s,economy_rom,CAPITALS)
            if s['id']!=25+n:raise ValueError('Added ship IDs must be consecutive.')
        offers=copy.deepcopy(self.stock_availability);seen=set()
        raw=m.get('original_availability',[])
        if not isinstance(raw,list):raise ValueError('Invalid original availability list.')
        for o in raw:
            if not isinstance(o,dict)or set(o)!={'id','ports','industry'}or type(o['id'])is not int or not 0<=o['id']<25 or o['id']in seen:raise ValueError('Invalid original availability entry.')
            seen.add(o['id']);offer=dict(ports=o['ports'],industry=o['industry']);self.validate_availability(o['id'],offer,economy_rom,set(CAPITALS));offers[o['id']]=offer
        rows.extend(added)
        for port in ports(self.rom):
            if sum(port['id']in o['ports']for o in offers)+sum(port['id']in o['ports']for o in added)>16:raise ValueError('New-build menu exceeds sixteen ships.')
        from portraits import unpack
        portrait_data=unpack(m.get('portraits',[]),len(rows))
        from character_mods import validate_edits,validate_shuffle
        free_agent_shuffle=validate_shuffle(self.rom,m.get('free_agent_shuffle',dict(enabled=False,blind=False,seed='0000')))
        character_edits=validate_edits(self.rom,m.get('character_edits',[]),free_agent_shuffle)
        from fleet_difficulty import preset,validate_rules
        raw_rules=gameplay.get('fleet_rules',preset())
        if m['version']==9:
            raw_rules=[nation+[[-1]*4]for nation in validate_rules(raw_rules,rows,positions=3)]
        fleet_rules=validate_rules(raw_rules,rows)
        from trade_goods import validate as validate_goods
        goods_edits=validate_goods(self.rom,m.get('goods_edits',[]))
        goods_shuffle=__import__('trade_goods').validate_shuffle(m.get('goods_shuffle',dict(seed=None,mode='normal')))
        from sailors import MATE_IDS,CAPTAIN_IDS
        custom_mates=m.get('custom_mates',any(e['id']in MATE_IDS for e in character_edits))
        custom_captains=m.get('custom_captains',any(e['id']in CAPTAIN_IDS for e in character_edits))
        if type(custom_mates)is not bool or type(custom_captains)is not bool:raise ValueError('Invalid custom character setting.')
        custom_goods=m.get('custom_goods',bool(goods_edits))
        if type(custom_goods)is not bool:raise ValueError('Invalid custom goods setting.')
        from item_shops import validate as validate_items
        item_edits=validate_items(self.rom,m.get('item_edits',[]));custom_items=m.get('custom_items',False)
        if type(custom_items)is not bool:raise ValueError('Invalid custom items setting.')
        item_special_only=m.get('item_special_only',False)
        if type(item_special_only)is not bool:raise ValueError('Invalid item shuffle mode.')
        item_blind=m.get('item_blind',False);item_special=m.get('item_special',False)
        if type(item_blind)is not bool or type(item_special)is not bool:raise ValueError('Invalid item shuffle mode.')
        item_seed=m.get('item_seed')
        if item_seed is not None:
            from character_mods import validate_seed
            item_seed=validate_seed(item_seed)
        custom_ships=m.get('custom_ships',bool(m['edits']or added or portrait_data or offers!=self.stock_availability))
        if type(custom_ships)is not bool:raise ValueError('Invalid custom ships setting.')
        shipbuilding_shuffle=__import__('shipbuilding_shuffle').validate(m.get('shipbuilding_shuffle',__import__('shipbuilding_shuffle').default()))
        for offer in shipbuilding_shuffle.get('previous',[]):
            if any(ports(self.rom)[p]['group']>=11 for p in offer['ports']):raise ValueError('Invalid shipyard backup port.')
        self.shipbuilding_shuffle=shipbuilding_shuffle
        self.goods_shuffle=goods_shuffle
        self.item_special_only=item_special_only;self.item_blind=item_blind;self.item_special=item_special;self.item_seed=item_seed;self.item_edits=item_edits;self.custom_items=custom_items;self.custom_ships=custom_ships;self.custom_mates=custom_mates;self.custom_captains=custom_captains;self.custom_goods=custom_goods;self.custom_economy=custom_economy;self.economy_edits=economy_edits;self.goods_edits=goods_edits;self.character_edits=character_edits;self.free_agent_shuffle=free_agent_shuffle
        self.portraits=portrait_data
        self.original_availability=offers
        self.ships=rows;self.repair_safeguard=fixes['repair_safeguard'];self.fleet_control=fleet_control;self.fleet_difficulty=fleet_difficulty;self.fleet_rules=fleet_rules;self.project_path=path

    def build(self):
        if any(type(v)is not bool for v in (self.item_special_only,self.item_blind,self.item_special,self.custom_items,self.custom_ships,self.custom_economy,self.custom_goods,self.custom_mates,self.custom_captains)):raise ValueError('Invalid custom world setting.')
        changes=self.changes();offers=self.availability_changes();self.validate_offer_counts()
        from fleet_difficulty import validate_rules
        validate_rules(self.fleet_rules,self.ships)
        if not self.item_edits and not self.economy_edits and not self.goods_edits and not offers and not changes and len(self.ships)==25 and not self.repair_safeguard and not self.fleet_control and not self.fleet_difficulty and not self.portraits and not self.effective_character_edits() and not self.free_agent_shuffle['enabled']:return self.rom,[]
        if len(self.ships)>25:
            from expansion import make_fleet
            catalog=ports(self.rom)
            additions=[dict(id=s['id'],name=s['name'],base_hull=s['base_hull'],industry_required=s['industry'],
                base_durability=s['hull'],turning=s['turning'],power=s['power'],max_crew=s['max_crew'],min_crew=s['min_crew'],
                total_capacity=s['capacity'],max_guns=s['max_guns'],price_units=s['price_gold']//10,
                default=dict(guns=s['factory_guns'],crew_space=s['factory_crew'],cargo_space=s['factory_cargo']),
                stock_ports=s['ports'],stock_groups=sorted({catalog[p]['group']for p in s['ports']}))for s in self.ships[25:]]
            compiled,_=make_fleet(self.rom,dict(ships=additions),allow_locked_ports=CAPITALS);data=bytearray(compiled)
        else:data=bytearray(self.rom)
        offsets=dict(hull=1,turning=2,power=3,max_crew=4,min_crew=5,max_guns=8,price_gold=10)
        for c in changes:
            i=c['id'];field=c['field'];value=c['after']
            if field=='name':
                at=MODEL_BASE+i*25;data[at:at+18]=value.encode('ascii').ljust(18,b'\0')
            elif field=='factory_cargo':struct.pack_into('<H',data,MODEL_BASE+i*25+23,value)
            elif field=='capacity':struct.pack_into('<H',data,SPEC_BASE+i*12+6,value)
            else:
                at=SPEC_BASE+i*12+offsets[field]
                if field=='price_gold':struct.pack_into('<H',data,at,value//10)
                else:data[at]=value//10 if field=='max_crew'else value
        if offers:
            from availability import install
            install(data,self.rom,self.all_offers())
        if self.repair_safeguard:
            from repair import apply
            apply(data)
        if self.fleet_control:
            from fleet_control import apply_manual_fleet
            result,_=apply_manual_fleet(bytes(data));data=bytearray(result)
        if type(self.fleet_difficulty)is not bool:raise ValueError('Invalid Custom Fleets setting.')
        if self.fleet_difficulty:
            from fleet_difficulty import install as install_difficulty
            install_difficulty(data,self.ships,self.fleet_rules)
        from portraits import install
        install(data,self.rom,self.portraits,len(self.ships))
        from character_mods import apply as apply_characters
        apply_characters(data,self.rom,self.character_edits,self.free_agent_shuffle)
        from trade_goods import install as install_goods
        install_goods(data,self.rom,self.goods_edits)
        from economy import install as install_economy
        install_economy(data,self.rom,self.economy_edits)
        from item_shops import install as install_items
        install_items(data,self.rom,self.item_edits)
        data[0xffdc:0xffe0]=b'\xff\xff\0\0';check=sum(data)&65535
        struct.pack_into('<HH',data,0xffdc,check^65535,check)
        assert len(data)in (0x200000,0x400000)and sum(data)&65535==check
        return bytes(data),changes

    def export(self,path):
        path=Path(path).resolve()
        if path.suffix.lower()!='.sfc':raise ValueError('Choose a new .sfc output filename.')
        targets=[path,path.with_suffix('.ips'),path.with_suffix('.changes.json')]
        if self.source in targets or self.project_path in targets:raise ValueError('Output cannot replace the source game or project.')
        if any(p.exists()for p in targets):raise ValueError('An output file already exists. Choose a new filename to preserve previous versions.')
        rom,changes=self.build();patch=ips(self.rom,rom);assert apply_ips(self.rom,patch)==rom
        report=dict(shipbuilding_shuffle=(dict(seed=None,blind=True)if __import__('shipbuilding_shuffle').hidden(self)else {k:v for k,v in self.shipbuilding_shuffle.items()if k!='previous'}),goods_shuffle=(dict(seed=None,mode=self.goods_shuffle['mode'],blind=True)if self.goods_shuffle.get('blind',False)else __import__('trade_goods').validate_shuffle(self.goods_shuffle)),item_shuffle=dict(enabled=self.item_seed is not None,blind=self.item_blind,include_special=self.item_special,special_only=self.item_special_only),item_seed=None if self.item_blind else self.item_seed,item_edits=[]if self.item_seed is not None and self.item_blind else copy.deepcopy(self.item_edits),custom_items=self.custom_items,custom_ships=self.custom_ships,custom_mates=self.custom_mates,custom_captains=self.custom_captains,custom_goods=self.custom_goods,custom_economy=self.custom_economy,economy_edits=copy.deepcopy(self.economy_edits),goods_edits=[]if self.goods_shuffle.get('blind',False)else copy.deepcopy(self.goods_edits),gameplay=dict(fleet_difficulty=self.fleet_difficulty,fleet_rules=copy.deepcopy(self.fleet_rules)),character_edits=copy.deepcopy(self.character_edits),free_agent_shuffle=(dict(enabled=True,blind=True,agents=40)if self.free_agent_shuffle['enabled']and (self.free_agent_shuffle['blind']or self.free_agent_shuffle.get('captain_blind',False))else copy.deepcopy(self.free_agent_shuffle)),custom_portraits=[dict(id=i,tiles_sha256=sha(raw))for i,raw in sorted(self.portraits.items())],tool='New Horizons Ship Editor',tool_version=TOOL_VERSION,base_sha256=ROM_SHA,output_sha256=sha(rom),
            original_availability=[]if __import__('shipbuilding_shuffle').hidden(self)else copy.deepcopy(self.availability_changes()),fixes=dict(repair_safeguard=self.repair_safeguard,fleet_control=self.fleet_control),input_header_removed=bool(self.header),output_headerless=True,changed_fields=changes,added_ships=self.ships[25:],
            ips_base='Original unheadered USA New Horizons ROM',runtime_tested=False,
            note='Data validation and patch reconstruction passed. Edited gameplay balance still needs emulator testing.')
        path.parent.mkdir(parents=True,exist_ok=True)
        written=[]
        try:
            for target,payload in zip(targets,[rom,patch,(json.dumps(report,indent=2)+'\n').encode()]):
                with target.open('xb')as stream:stream.write(payload)
                written.append(target)
        except Exception:
            for target in written:target.unlink()
            raise
        return report
