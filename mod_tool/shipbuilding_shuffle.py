"""Seeded stock location-group permutation for the original 25 hulls only."""
import copy,random
from character_mods import validate_seed

def default():return dict(seed=None,blind=False)

def validate(config):
 if not isinstance(config,dict)or set(config)not in ({'seed','blind'},{'seed','blind','previous'})or type(config.get('blind'))is not bool:raise ValueError('Invalid ship building shuffle settings.')
 seed=config['seed']
 if seed is None:
  if config['blind']or 'previous'in config:raise ValueError('Inactive ship shuffle cannot contain destinations.')
  return default()
 validate_seed(seed);previous=config.get('previous')
 if not isinstance(previous,list)or len(previous)!=25:raise ValueError('Missing original ship availability backup.')
 for row in previous:
  if not isinstance(row,dict)or set(row)!={'ports','industry'}or type(row['industry'])is not int or not 0<=row['industry']<=1000 or row['industry']%10:raise ValueError('Invalid ship availability backup.')
  ps=row['ports']
  if not isinstance(ps,list)or any(type(p)is not int or not 0<=p<100 for p in ps)or len(ps)!=len(set(ps)):raise ValueError('Invalid ship ports backup.')
 return dict(seed=seed,blind=config['blind'],previous=copy.deepcopy(previous))

def hidden(project):return bool(project and project.shipbuilding_shuffle['seed']is not None and project.shipbuilding_shuffle['blind'])

def generate(project,seed,blind=False):
 from backend import ports
 validate_seed(seed)
 if type(blind)is not bool:raise ValueError('Invalid blind mode.')
 rng=random.Random('NH-shipbuilding-v1:'+seed+(':blind'if blind else ':normal'))
 catalog=ports(project.economy_rom());stock=project.stock_availability
 choices={}
 for ship in range(25):
  gate=project.original_availability[ship]['industry'];options=[]
  for source,row in enumerate(stock):
   if all(catalog[p]['group']<11 and (not catalog[p]['capital']or gate<=catalog[p]['industry']or(p in stock[ship]['ports']and gate<=stock[ship]['industry']))for p in row['ports']):options.append(source)
  rng.shuffle(options);options.sort(key=lambda source:source==ship);choices[ship]=options
 order=list(range(25));rng.shuffle(order);order.sort(key=lambda ship:len(choices[ship]))
 owner={}
 def assign(ship,seen):
  for source in choices[ship]:
   if source in seen:continue
   seen.add(source)
   if source not in owner or assign(owner[source],seen):owner[source]=ship;return True
  return False
 for ship in order:
  if not assign(ship,set()):raise ValueError('No safe ship-building shuffle fits the current industry requirements and capital levels. Adjust those values before shuffling.')
 result=copy.deepcopy(project.original_availability)
 for source,ship in owner.items():result[ship]['ports']=list(stock[source]['ports'])
 project.validate_offer_counts(result+project.all_offers()[25:])
 return result


def plan(project,seed,blind=False):
 offers=generate(project,seed,blind)
 previous=project.shipbuilding_shuffle.get('previous',project.original_availability)
 return dict(original_availability=offers,shipbuilding_shuffle=validate(dict(seed=seed,blind=blind,previous=previous)))
