"""Bounded starting attributes and random free-agent port-slot shuffling."""
import secrets
from functools import lru_cache
from sailors import BASE,STRIDE,ATTRIBUTES,MATE_IDS,CAPTAIN_IDS,decode_sailors,EDITABLE_FIELDS

def validate_edits(rom,entries,config=None):
    if not isinstance(entries,list):raise ValueError('Invalid character edits.')
    projected={(e['id'],e['field']):e['value']for e in shuffled_stats(rom,config)+shuffled_skills(rom,config)}if config is not None else {}
    result=[];seen=set()
    for entry in entries:
        if not isinstance(entry,dict)or set(entry)!={'id','field','value'}:raise ValueError('Invalid character edit.')
        i,key,value=entry['id'],entry['field'],entry['value']
        if type(i)is not int or i not in MATE_IDS+CAPTAIN_IDS or not isinstance(key,str)or key not in EDITABLE_FIELDS:
            raise ValueError('Only mate and fleet captain attributes and skills can be edited.')
        limit=31 if key=='skills'else 100
        if type(value)is not int or not 0<=value<=limit:raise ValueError('Invalid skill selection.'if key=='skills'else 'Character attributes must be whole numbers from 0 to 100.')
        baseline=rom[BASE+STRIDE*i+(48 if key=='skills'else 28+ATTRIBUTES.index(key))]
        if key=='skills':
            baseline&=31
            if 69<=i<79 and value&baseline!=baseline:raise ValueError('Story companions must keep their original skills. You can add other skills.')
        if (i,key)in seen:raise ValueError('Duplicate character edit.')
        seen.add((i,key))
        if value!=projected.get((i,key),baseline):result.append(dict(entry))
    return sorted(result,key=lambda e:(e['id'],EDITABLE_FIELDS.index(e['field'])))

def free_agent_rows(rom):
    return [r for r in decode_sailors(rom)if r['role']=='Free agent']

def validate_seed(seed):
    if not isinstance(seed,str) or len(seed)!=4 or any(c not in '0123456789' for c in seed):
        raise ValueError('Enter exactly four digits (0000–9999).')
    return seed

def validate_shuffle(rom,config):
    if not isinstance(config,dict) or not {'enabled','blind','seed'}<=set(config) or set(config)-{'enabled','blind','seed','names','captain_names','mate_stats','captain_stats','ports','name_parts','stat_budget','mate_skills','captain_skills','captain_seed','captain_blind','captain_name_parts','captain_stat_budget','option_settings'} or type(config['enabled'])is not bool or type(config['blind'])is not bool:
        raise ValueError('Invalid free-agent shuffle settings.')
    result=dict(enabled=config['enabled'],blind=config['blind'],seed=validate_seed(config['seed']))
    for key in ('names','captain_names','mate_stats','captain_stats','ports','name_parts','stat_budget','mate_skills','captain_skills'):
        if type(config.get(key,True if key=='ports'else False))is not bool:raise ValueError('Invalid name shuffle option.')
        if key=='ports':
            if config.get(key,True)is False:result[key]=False
        elif config.get(key,False):result[key]=True
    if 'captain_seed'in config:result['captain_seed']=validate_seed(config['captain_seed'])
    for key in ('captain_blind','captain_name_parts','captain_stat_budget'):
        if key in config:
            if type(config[key])is not bool:raise ValueError('Invalid captain shuffle option.')
            result[key]=config[key]
    if 'option_settings'in config:
        overrides=config['option_settings']
        allowed=('ports','names','mate_stats','mate_skills','captain_names','captain_stats','captain_skills')
        if not isinstance(overrides,dict)or set(overrides)-set(allowed):raise ValueError('Invalid per-option shuffle settings.')
        normalized={}
        for flag,settings in overrides.items():
            if not isinstance(settings,dict)or set(settings)!={'seed','blind','name_parts','stat_budget'}:raise ValueError('Invalid per-option shuffle settings.')
            if any(type(settings[k])is not bool for k in ('blind','name_parts','stat_budget')):raise ValueError('Invalid per-option shuffle settings.')
            normalized[flag]={**settings,'seed':validate_seed(settings['seed'])}
        if normalized:result['option_settings']=normalized
    return result

MATE_SHUFFLES=('ports','names','mate_stats','mate_skills')
CAPTAIN_SHUFFLES=('captain_names','captain_stats','captain_skills')

def group_active(config,group):
    keys=MATE_SHUFFLES if group=='mates'else CAPTAIN_SHUFFLES
    return config['enabled']and any(config.get(k,k=='ports')for k in keys)

def group_settings(config,flag):
    result=dict(config)
    if flag.startswith('captain'):
        result.update({key:config.get('captain_'+key,config.get(key,False))for key in ('seed','blind','name_parts','stat_budget')})
    result.update(config.get('option_settings',{}).get(flag,{}))
    return result


def group_summary(config,group):
    keys=MATE_SHUFFLES if group=='mates'else CAPTAIN_SHUFFLES
    states=[group_settings(config,k)for k in keys if config['enabled']and config.get(k,k=='ports')]
    if not states:return 'Off'
    if any(s['blind']for s in states):return 'Blind shuffle'
    seeds={s['seed']for s in states}
    return 'Seed '+next(iter(seeds))if len(seeds)==1 else 'Mixed seeds'


def merge_options(rom,current,flags,seed,blind=False):
    """Preset edits retain all other options' exact prior seed/algorithm."""
    validate_seed(seed)
    if type(blind)is not bool:raise ValueError('Invalid blind mode.')
    current=validate_shuffle(rom,current);result=dict(current);all_keys=MATE_SHUFFLES+CAPTAIN_SHUFFLES
    if set(flags)-set(all_keys):raise ValueError('Invalid shuffle option.')
    overrides={}
    for key in all_keys:
        active=current['enabled']and current.get(key,key=='ports');result[key]=active
        if active:
            settings=group_settings(current,key)
            overrides[key]={k:settings.get(k,False)for k in ('seed','blind','name_parts','stat_budget')}
    for flag in flags:
        result[flag]=True;overrides[flag]=dict(seed=seed,blind=blind,name_parts=True,stat_budget=True)
    result['enabled']=bool(overrides);result['option_settings']=overrides
    for keys,prefix in ((MATE_SHUFFLES,''),(CAPTAIN_SHUFFLES,'captain_')):
        active=[overrides[k]for k in keys if k in overrides]
        if set(flags).intersection(keys):result[prefix+'seed']=seed;result[prefix+'name_parts']=True;result[prefix+'stat_budget']=True
        result[prefix+'blind']=any(s['blind']for s in active)
    return validate_shuffle(rom,result)


def configure_group(rom,current,group,seed=None,blind=False,options=None,enabled=True):
    current=validate_shuffle(rom,current);options=options or {}
    if group not in ('mates','captains','all'):raise ValueError('Invalid people shuffle group.')
    keys=MATE_SHUFFLES if group=='mates'else CAPTAIN_SHUFFLES if group=='captains'else MATE_SHUFFLES+CAPTAIN_SHUFFLES
    result=dict(current)
    overrides={k:v for k,v in current.get('option_settings',{}).items()if k not in keys}
    result.pop('option_settings',None)
    if overrides:result['option_settings']=overrides
    if not current['enabled']:
        for key in MATE_SHUFFLES+CAPTAIN_SHUFFLES:result[key]=False
    if group=='mates':
        # Freeze the captain settings before changing the previously shared seed.
        for key in ('seed','blind','name_parts','stat_budget'):result['captain_'+key]=current.get('captain_'+key,current.get(key,False))
    if enabled:
        seed=validate_seed(seed)
        prefix='captain_'if group=='captains'else ''
        result[prefix+'seed']=seed;result[prefix+'blind']=blind
        result[prefix+'name_parts']=True;result[prefix+'stat_budget']=True
        if group=='all':
            for key in ('seed','blind','name_parts','stat_budget'):result.pop('captain_'+key,None)
    for key in keys:result[key]=bool(options.get(key,False))if enabled else False
    result['enabled']=any(result.get(k,k=='ports')for k in MATE_SHUFFLES+CAPTAIN_SHUFFLES)
    return validate_shuffle(rom,result)

def seeded_ports(rom,seed,blind=False):
    # Version 1: stable SHA256 ordering of numbered stock slots. No dependency
    # on Python's random implementation or the order of previous shuffles.
    import hashlib
    validate_seed(seed)
    rows=free_agent_rows(rom);slots=[r['starting_port'] for r in rows]
    def arrange(mode):
        domain=('NH-free-agent-v1:'+mode+':'+seed+':').encode('ascii')
        order=sorted(range(len(slots)),key=lambda i:hashlib.sha256(domain+str(i).encode('ascii')).digest())
        return [slots[i] for i in order]
    normal=arrange('normal');ports=arrange('blind') if blind else normal
    if blind and ports==normal:
        # Guarantee separate blind and normal arrangements, even in a collision.
        while ports==normal:ports=ports[1:]+ports[:1]
    return [dict(id=r['id'],port=port) for r,port in zip(rows,ports)]

def port_shuffle(rom,config):
    config=validate_shuffle(rom,config)
    if config['enabled']and config.get('ports',True):
        settings=group_settings(config,'ports')
        return {e['id']:e['port'] for e in seeded_ports(rom,settings['seed'],settings['blind'])}
    return {r['id']:r['starting_port']for r in free_agent_rows(rom)}

def name_shuffle(rom,config):
    """Map separate fixed-width first/last fields; retain legacy paired seeds."""
    import hashlib
    config=validate_shuffle(rom,config);result={}
    if not config['enabled']:return result
    for flag,ids in [('names',[r['id']for r in free_agent_rows(rom)]),('captain_names',list(CAPTAIN_IDS))]:
        if not config.get(flag,False):continue
        settings=group_settings(config,flag)
        if settings.get('name_parts',False):
            groups=[]
            for part in ('first','last'):
                domain=('NH-name-parts-v2:'+flag+':'+part+':'+settings['seed']+(':blind:'if settings['blind']else ':normal:')).encode('ascii')
                groups.append(sorted(ids,key=lambda i:hashlib.sha256(domain+str(i).encode('ascii')).digest()))
            result.update((i,(first,last))for i,first,last in zip(ids,*groups))
        else:
            domain=('NH-names-v1:'+flag+':'+settings['seed']+(':blind:'if settings['blind']else ':normal:')).encode('ascii')
            sources=sorted(ids,key=lambda i:hashlib.sha256(domain+str(i).encode('ascii')).digest())
            result.update((i,(source,source))for i,source in zip(ids,sources))
    return result

def shuffled_names(rom,config):
    records=decode_sailors(rom);result={}
    for i,(first,last)in name_shuffle(rom,config).items():
        a,b=records[first]['first_name'],records[last]['last_name']
        result[i]=dict(first_name=a,last_name=b,name=a+' '+b)
    return result


@lru_cache(None)
def _stat_allocations(n,points):
    if not 0<=points<=n*50:return 0
    if n==0:return int(points==0)
    return sum(_stat_allocations(n-1,points-v)for v in range(min(50,points)+1))

@lru_cache(maxsize=4096)
def budget_profile(total,seed):
    """Uniformly choose a bounded eight-stat allocation with an exact total."""
    import random
    count=len(ATTRIBUTES);remaining=total-count*50
    if type(total)is not int or not 0<=remaining<=count*50:
        raise ValueError('The original stat total cannot fit eight stats from 50 to 100.')
    rng=random.Random(seed);values=[]
    for n in range(count,0,-1):
        ticket=rng.randrange(_stat_allocations(n,remaining))
        for v in range(min(50,remaining)+1):
            weight=_stat_allocations(n-1,remaining-v)
            if ticket<weight:
                values.append(50+v);remaining-=v;break
            ticket-=weight
    assert sum(values)==total and all(50<=v<=100 for v in values)
    return tuple(values)

def shuffled_stats(rom,config):
    """Redistribute each original point budget; preserve old profile projects."""
    import hashlib
    config=validate_shuffle(rom,config);result=[];records=decode_sailors(rom)
    if not config['enabled']:return result
    for flag,ids in [('mate_stats',[r['id']for r in free_agent_rows(rom)]),('captain_stats',list(CAPTAIN_IDS))]:
        if not config.get(flag,False):continue
        settings=group_settings(config,flag)
        if settings.get('stat_budget',False):
            for i in ids:
                total=sum(records[i][key]for key in ATTRIBUTES)
                domain='NH-stat-budget-v2:'+flag+':'+str(i)+':'+settings['seed']+(':blind'if settings['blind']else ':normal')
                for key,value in zip(ATTRIBUTES,budget_profile(total,domain)):
                    if value!=records[i][key]:result.append(dict(id=i,field=key,value=value))
            continue
        domain=('NH-stats-v1:'+flag+':'+settings['seed']+(':blind:'if settings['blind']else ':normal:')).encode('ascii')
        sources=sorted(ids,key=lambda i:hashlib.sha256(domain+str(i).encode('ascii')).digest())
        for i,source in zip(ids,sources):
            for key in ATTRIBUTES:
                value=max(50,min(100,records[source][key]))
                if value!=records[i][key]:result.append(dict(id=i,field=key,value=value))
    return validate_edits(rom,result)


def shuffled_skills(rom,config):
    """Reassign learned skills, retaining each character's native skill count."""
    import random
    config=validate_shuffle(rom,config);records=decode_sailors(rom);result=[]
    if not config['enabled']:return result
    for flag,ids in [('mate_skills',[r['id']for r in free_agent_rows(rom)]),('captain_skills',list(CAPTAIN_IDS))]:
        if not config.get(flag,False):continue
        settings=group_settings(config,flag)
        for i in ids:
            domain='NH-skills-v1:'+flag+':'+str(i)+':'+settings['seed']+(':blind'if settings['blind']else ':normal')
            rng=random.Random(domain);count=records[i]['skills'].bit_count()
            mask=sum(rng.sample([1,2,4,8,16],count))
            if mask!=records[i]['skills']:result.append(dict(id=i,field='skills',value=mask))
    return validate_edits(rom,result)


def random_seed():
    return f'{secrets.randbelow(10000):04d}'

def apply(data,rom,edits,config):
    shuffled=shuffled_stats(rom,config)+shuffled_skills(rom,config)
    combined={(e['id'],e['field']):e for e in shuffled}
    combined.update({(e['id'],e['field']):e for e in validate_edits(rom,edits,config)})
    edits=list(combined.values());mapping=port_shuffle(rom,config)
    for e in edits:
        at=BASE+STRIDE*e['id']
        if e['field']=='skills':data[at+48]=(rom[at+48]&224)|e['value']
        else:data[at+28+ATTRIBUTES.index(e['field'])]=e['value']
    for i,port in mapping.items():data[BASE+STRIDE*i+45]=port

    for i,sources in name_shuffle(rom,config).items():
        for part,source in enumerate(sources):
            at=BASE+i*STRIDE+part*13;original=BASE+source*STRIDE+part*13
            data[at:at+13]=rom[original:original+13]


def preview_changes(rom,edits,config):
    """Compare proposed native records with stock; no project/ROM mutation."""
    from sailors import skill_names
    stock=decode_sailors(rom);data=bytearray(rom);apply(data,rom,edits,config);after=decode_sailors(data);changes=[]
    for before,new in zip(stock,after):
        fields=[]
        if before['name']!=new['name']:fields.append(('Name',before['name'],new['name']))
        if before['starting_port']!=new['starting_port']:fields.append(('Port',before['starting_port_name'],new['starting_port_name']))
        for key in ATTRIBUTES:
            if before[key]!=new[key]:fields.append((key.capitalize(),before[key],new[key]))
        if before['skills']!=new['skills']:fields.append(('Skills',', '.join(skill_names(before['skills']))or 'None',', '.join(skill_names(new['skills']))or 'None'))
        if fields:changes.append(dict(id=before['id'],name=before['name'],changes=fields))
    return changes
