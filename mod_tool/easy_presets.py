"""Composable presets; plans are pure, previews precede atomic application."""
import copy,random
from economy import stock as economy_stock,values as economy_values,validate as validate_economy
from sailors import decode_sailors,ATTRIBUTES
from character_mods import validate_edits,validate_seed,merge_options
from fleet_difficulty import preset
PRESETS={
 'Classic Plus':'Enable Repair Safeguard. Keep all other settings as they are; starting from stock retains the original world and ship balance.',
 'Prosperous World':'Starting goods economy +25% and shipbuilding +10%, based on stock and capped at 1000. Replaces starting economy and industry at all trading ports.',
 'Naval Challenge':'Upgrade top-tier ordinary national flagships and fourth ships. Other positions, pirates and player fleets keep native selection. Experimental; existing fleets change as ships are replaced.',
 'Fresh World':'Shuffle free-agent starting ports, normal goods, regular shop items and original-ship building locations. Preserve character names/stats/skills, specialty goods and special shop items.',
 'Full Randomizer':'Shuffle free-agent ports, mate/captain names, attributes and skills, all goods, all shop items and original-ship building locations. Preserve each person’s attribute total and skill count; exclude story companions and protagonists.',
 'Uncharted Challenge':'Full Randomizer plus Naval Challenge. The same seed and blind mode reproduce the arrangements. Fleet upgrades are experimental.',
 'Regional Fleets':'Use regional national fleet choices. Only eligible top-tier national fleets are affected; weaker replacements are skipped. Experimental.',
 'Developing World':'Set noncapital shipbuilding industry to 75% of stock. Preserve goods economy and all capital levels. Investment becomes more important for advanced ships.',
 'Trade Opportunities':'Set existing goods economy requirements to 80% of their stock slot requirement, rounded to a multiple of 10. Preserve selling locations, prices and town economies.',
 'Unknown Recruits':'Shuffle free-agent attributes and skills. Keep names, ports, captains and companions unchanged. Each person keeps their original attribute total and skill count; attributes stay 50–100.',
 'Hidden Treasures':'Shuffle special early-morning shop items only. Preserve regular shop stock, item counts and empty slots.',
 'Random Shipyards':'Shuffle stock building-location groups among the original 25 ships only. Preserve ship stats, prices, industry requirements and added ships; respect fixed-capital restrictions.',
 'New Faces':'Shuffle first and last names independently for free agents and fleet captains. Keep attributes, skills, portraits and starting ports unchanged.',
}
# Older preset plans remain available to existing scripts, not in the menu.
LEGACY_PRESETS=PRESETS
PRESETS={
 'Classic Plus':LEGACY_PRESETS['Classic Plus'],
 'Hard Mode':'Naval Challenge plus noncapital shipbuilding at 75% of stock. Goods economy and fixed capital industry stay unchanged. Advanced ships require more investment; no shuffles.',
 'Naval Challenge':LEGACY_PRESETS['Naval Challenge'],
 'Trade & Exploration':'Starting goods economy +25% and shipbuilding +10%, capped at 1000, with goods unlock requirements at 80% of stock. Preserve goods locations, prices, ships and people; no shuffles.',
 'Full Randomizer':LEGACY_PRESETS['Full Randomizer'],
}
RANDOMIZED={'Fresh World','Full Randomizer','Uncharted Challenge','Unknown Recruits','Hidden Treasures','New Faces','Random Shipyards'}
ALIASES={'Busy Ports':'Prosperous World','Stronger Flagships':'legacy_flagships','Stronger Fleets':'legacy_fleets','Random Mates':'legacy_mates','Random Items':'legacy_items','Skilled Recruits':'legacy_recruits'}


def _people(project,flags,seed,blind):
 config=merge_options(project.rom,project.free_agent_shuffle,flags,seed,blind)
 roles={r['id']:r['role']for r in decode_sailors(project.rom)}
 def affected(e):
  role=roles[e['id']];prefix='mate'if role=='Free agent'else 'captain'if role=='Fleet captain'else None
  return prefix and ((prefix+'_stats'in flags and e['field']in ATTRIBUTES)or (prefix+'_skills'in flags and e['field']=='skills'))
 result={'free_agent_shuffle':config}
 if any(k.endswith(('_stats','_skills'))for k in flags):result['character_edits']=[copy.deepcopy(e)for e in project.character_edits if not affected(e)]
 return result


def _items(project,seed,blind,scope):
 from item_shops import seeded_shuffle,stock,values,validate
 original=stock(project.rom);current=values(project.rom,project.item_edits)
 selected=(3,)if scope=='special'else (0,1,2)if scope=='regular'else (0,1,2,3)
 proposed=values(project.rom,seeded_shuffle(project.rom,seed,blind,scope=='all',scope=='special'))
 rows=[[proposed[p][i]if i in selected else current[p][i]for i in range(4)]for p in range(100)]
 # Mixed regular/special shuffles may conflict at a port. Reassign only the
 # selected stock pool around fixed offers, preserving every outside slot.
 if any(len([v for v in row if v!=255])!=len({v for v in row if v!=255})for row in rows):
  from collections import Counter
  pool=Counter(original[p][i]for p in range(100)for i in selected if original[p][i]!=255)
  positions=[(p,i)for p in range(100)for i in selected if original[p][i]!=255]
  rng=random.Random('NH-preset-items-v1:'+seed+':'+scope+':'+str(blind))
  for attempt in range(128):
   rows=[[255 if i in selected else current[p][i]for i in range(4)]for p in range(100)];remaining=pool.copy();order=list(positions);rng.shuffle(order)
   order.sort(key=lambda pos:-sum(v!=255 for v in rows[pos[0]]))
   for p,i in order:
    choices=[v for v,n in remaining.items()if n and v not in rows[p]]
    if not choices:break
    v=rng.choices(choices,weights=[remaining[v]for v in choices])[0];rows[p][i]=v;remaining[v]-=1
   else:break
  else:raise ValueError('This item preset cannot preserve the current outside stock. Restore conflicting shop edits or use Full Randomizer.')
 edits=validate(project.rom,[dict(port=p,slots=row)for p,row in enumerate(rows)])
 # A single metadata record covers both scopes. Preserve privacy if an earlier
 # complementary blind shuffle is still active.
 effective_blind=blind or (scope!='all'and project.item_seed is not None and project.item_blind)
 regular=scope in ('regular','all')or (project.item_seed is not None and not project.item_special_only)
 special=scope in ('special','all')or (project.item_seed is not None and (project.item_special or project.item_special_only))
 return dict(item_edits=edits,item_seed=seed,item_blind=effective_blind,item_special=regular and special,item_special_only=special and not regular)


def _goods(project,seed,blind,scope):
 from trade_goods import shuffle_plan
 return shuffle_plan(project,seed,scope,blind)


def plan(project,name,seed=None,blind=False):
 name=ALIASES.get(name,name)
 if name not in PRESETS and name not in LEGACY_PRESETS and not name.startswith('legacy_'):raise ValueError('Choose a preset.')
 if type(blind)is not bool:raise ValueError('Invalid blind mode.')
 if name in RANDOMIZED or name in ('legacy_mates','legacy_items'):seed=validate_seed('0000'if seed is None else seed)
 if name=='Classic Plus':return dict(repair_safeguard=True)
 if name=='Hard Mode':
  result=plan(project,'Developing World');result.update(plan(project,'Naval Challenge'));return result
 if name=='Trade & Exploration':
  result=plan(project,'Prosperous World');result.update(plan(project,'Trade Opportunities'));return result
 if name in ('Prosperous World','Developing World'):
  from backend import CAPITALS
  rows=economy_values(project.rom,project.economy_edits);original=economy_stock(project.rom)
  for p,row in enumerate(rows):
   if name=='Prosperous World':
    for field,percent in (('economy',125),('industry',110)):row[field]=min(1000,max(1,(original[p][field]*percent+50)//100))
   elif p not in CAPITALS:row['industry']=max(1,(original[p]['industry']*75+50)//100)
  return dict(economy_edits=validate_economy(project.rom,rows))
 if name in ('Naval Challenge','Regional Fleets','legacy_flagships','legacy_fleets'):
  rules=preset('regional'if name=='Regional Fleets'else 'stronger'if name=='legacy_fleets'else 'flagships')
  if name=='Naval Challenge':
   for nation in rules:nation[3]=[10,15,20,-1]
  return dict(fleet_difficulty=True,fleet_rules=rules)
 if name=='Trade Opportunities':
  from trade_goods import stock_offers,offers,validate
  rows=offers(project.rom,project.goods_edits);original=stock_offers(project.rom)
  for p,row in enumerate(rows):
   for kind in ('Regional','Specialty'):
    refs=[o for o in original[p]if o['kind']==kind]
    for i,o in enumerate(x for x in row if x['kind']==kind):
     if i>=len(refs):continue
     gate=refs[i]['economy_required']
     o['economy_required']=((gate*80+500)//1000)*10
  return dict(goods_edits=validate(project.rom,[dict(port=p,offers=row)for p,row in enumerate(rows)]))
 if name=='legacy_recruits':
  free=[r for r in decode_sailors(project.rom)if r['role']=='Free agent'];ids={r['id']for r in free}
  edits=[e for e in project.character_edits if not(e['id']in ids and e['field']in ('leadership','seamanship'))]
  edits +=[dict(id=r['id'],field=k,value=min(100,r[k]+10))for r in free for k in ('leadership','seamanship')]
  return dict(character_edits=validate_edits(project.rom,edits))
 if name in ('Fresh World','Full Randomizer','Uncharted Challenge'):
  full=name!='Fresh World';flags=('ports','names','mate_stats','mate_skills','captain_names','captain_stats','captain_skills')if full else ('ports',)
  result=_people(project,flags,seed,blind);result.update(_items(project,seed,blind,'all'if full else 'regular'));result.update(_goods(project,seed,blind,'all'if full else 'normal'))
  from shipbuilding_shuffle import plan as shipyard_plan
  result.update(shipyard_plan(project,seed,blind))
  if name=='Uncharted Challenge':result.update(plan(project,'Naval Challenge'))
  return result
 if name=='Random Shipyards':
  from shipbuilding_shuffle import plan as shipyard_plan
  return shipyard_plan(project,seed,blind)
 if name=='Unknown Recruits':return _people(project,('mate_stats','mate_skills'),seed,blind)
 if name=='New Faces':return _people(project,('names','captain_names'),seed,blind)
 if name=='Hidden Treasures':return _items(project,seed,blind,'special')
 if name=='legacy_mates':return _people(project,('ports',),seed,blind)
 if name=='legacy_items':return _items(project,seed,blind,'regular')
 raise ValueError('Choose a preset.')


def validate_plan(project,changes):
 candidate=copy.copy(project)
 for key,value in changes.items():setattr(candidate,key,copy.deepcopy(value))
 if 'economy_edits'in changes:
  from backend import CAPITALS
  from ports import PORT_NAMES
  old=economy_values(project.rom,project.economy_edits);new=economy_values(project.rom,candidate.economy_edits)
  for ship,offer in zip(candidate.ships,candidate.all_offers()):
   for port in offer['ports']:
    if port in CAPITALS and old[port]['industry']>=offer['industry']>new[port]['industry']:
     raise ValueError(f"This preset would lock {ship['name']} at {PORT_NAMES[port]}, where industry cannot be raised through investment. Adjust that ship’s industry requirement first.")
 candidate.build()


def apply_plan(project,changes):
 validate_plan(project,changes)
 for key,value in changes.items():setattr(project,key,copy.deepcopy(value))


def apply(project,name,seed=None,blind=False):
 changes=plan(project,name,seed,blind);apply_plan(project,changes)


def preview(project,name,seed=None,blind=False):
 """Return a validated draft and concise current-to-proposed summary."""
 changes=plan(project,name,seed,blind);validate_plan(project,changes);lines=[]
 for key,value in changes.items():
  current=getattr(project,key)
  if current==value:continue
  if key=='economy_edits':
   old=economy_values(project.rom,current);new=economy_values(project.rom,value)
   for field,label in (('economy','Goods economy'),('industry','Shipbuilding')):
    pairs=[(a[field],b[field])for a,b in zip(old,new)if a[field]!=b[field]]
    if pairs:lines.append(f'{label}: {len(pairs)} ports; current {min(a for a,b in pairs)}–{max(a for a,b in pairs)} → proposed {min(b for a,b in pairs)}–{max(b for a,b in pairs)}.')
  elif key=='goods_edits':
   from trade_goods import offers
   old=offers(project.rom,current);new=offers(project.rom,value);lines.append(f'Goods: {sum(a!=b for a,b in zip(old,new))} port offer lists change. Destinations hidden.'if blind or project.goods_shuffle.get('blind',False)else f'Goods: {sum(a!=b for a,b in zip(old,new))} port offer lists change.')
  elif key=='item_edits':
   from item_shops import values
   lines.append(f'Items: {sum(a!=b for a,b in zip(values(project.rom,current),values(project.rom,value)))} shop lists change.'+(' Destinations hidden.'if changes.get('item_blind')else ''))
  elif key=='free_agent_shuffle':
   from character_mods import group_settings
   labels={'ports':'Mate starting ports','names':'Mate names','mate_stats':'Mate attributes','mate_skills':'Mate skills','captain_names':'Captain names','captain_stats':'Captain attributes','captain_skills':'Captain skills'}
   for flag,label in labels.items():
    if value.get(flag,flag=='ports')and (not current['enabled']or not current.get(flag,flag=='ports')or any(group_settings(current,flag).get(k)!=group_settings(value,flag).get(k)for k in ('seed','blind','name_parts','stat_budget'))):
     lines.append(label+': seeded shuffle'+(' (blind). 'if group_settings(value,flag)['blind']else '. '))
  elif key=='character_edits':lines.append('Replace manual attributes/skills covered by this preset; keep unrelated edits.')
  elif key=='original_availability':lines.append(f'Ship building: {sum(a!=b for a,b in zip(current,value))} original ship location lists change.'+(' Destinations hidden.'if changes.get('shipbuilding_shuffle',{}).get('blind',False)else ''))
  elif key=='shipbuilding_shuffle':lines.append('Ship building randomizer options will be updated'+(' (blind).'if value['blind']else '.'))
  elif key=='repair_safeguard':lines.append('Repair Safeguard: '+('On'if current else 'Off')+' → On.')
  elif key=='fleet_rules':lines.append('Replace current national fleet choices with this preset’s flagship/escort choices.')
  elif key=='fleet_difficulty':lines.append('Custom Fleets: Off → On.')
 if any(k in changes and getattr(project,k)!=changes[k]for k in ('item_seed','item_blind','item_special','item_special_only')):
  lines.append('Item shuffle options will be updated'+(' (blind).'if changes.get('item_blind')else '.'))
 if 'goods_shuffle'in changes and project.goods_shuffle!=changes['goods_shuffle']:lines.append('Goods shuffle options will be updated'+(' (blind).'if changes['goods_shuffle'].get('blind',False)else '.'))
 if 'free_agent_shuffle'in changes and project.free_agent_shuffle!=changes['free_agent_shuffle']and not any('seeded shuffle'in line for line in lines):lines.append('Character shuffle options will be updated; unrelated options keep their earlier results.')
 if not lines:lines=['Already matches this preset. No settings will change.']
 return changes,lines
