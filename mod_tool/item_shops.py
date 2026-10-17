"""Editable native town equipment-shop slots; item definitions stay original."""
import copy
from items import TOWNS,catalogue as original

def stock(rom):return [list(rom[TOWNS+p*37+29:TOWNS+p*37+33])for p in range(100)]
def validate(rom,edits):
 if not isinstance(edits,list):raise ValueError('Invalid item shop edits.')
 allowed={r['id']for r in original(rom)};seen=set();result=[];defaults=stock(rom)
 for row in edits:
  if not isinstance(row,dict)or set(row)!={'port','slots'}or type(row['port'])is not int or not 0<=row['port']<100 or row['port']in seen:raise ValueError('Invalid or duplicate item port.')
  seen.add(row['port']);slots=row['slots']
  if not isinstance(slots,list)or len(slots)!=4 or any(type(i)is not int or i!=255 and i not in allowed for i in slots):raise ValueError('Choose original shop items; three regular slots and one early-morning slot per port.')
  used=[i for i in slots if i!=255]
  if len(used)!=len(set(used)):raise ValueError('A port cannot sell the same item twice.')
  if slots!=defaults[row['port']]:result.append(copy.deepcopy(row))
 return sorted(result,key=lambda row:row['port'])
def values(rom,edits):
 rows=stock(rom)
 for row in validate(rom,edits):rows[row['port']]=row['slots']
 return rows

def change(rom,edits,port,item,early=False,remove=False):
 if type(port)is not int or not 0<=port<100 or type(item)is not int or item not in {r['id']for r in original(rom)}:raise ValueError('Choose an original shop item and trading port.')
 if type(early)is not bool or type(remove)is not bool:raise ValueError('Invalid item offer type.')
 rows=values(rom,edits);slots=rows[port];old=slots.index(item)if item in slots else None
 if remove:
  if old is not None:slots[old]=255
 else:
  candidates=[3]if early else [0,1,2]
  target=old if old in candidates else next((i for i in candidates if slots[i]==255),None)
  if target is None:raise ValueError('No free early-morning slot at this port.'if early else 'No free regular slot at this port. Remove an item first.')
  if old is not None:slots[old]=255
  slots[target]=item
 return validate(rom,[dict(port=p,slots=row)for p,row in enumerate(rows)])

def restore_item(rom,edits,item):
 rows=values(rom,edits);defaults=stock(rom)
 for port,slots in enumerate(rows):
  slots[:]=[255 if i==item else i for i in slots]
  if item in defaults[port]:
   target=defaults[port].index(item)
   if slots[target]!=255:raise ValueError('An original slot is occupied by another item. Remove that item or reset World first.')
   slots[target]=item
 return validate(rom,[dict(port=p,slots=row)for p,row in enumerate(rows)])

def catalogue(rom,edits):
 result=original(rom);by_id={r['id']:r for r in result}
 for row in result:row['sources']=[]
 for port,slots in enumerate(values(rom,edits)):
  for slot,item in enumerate(slots):
   if item!=255:by_id[item]['sources'].append(dict(port=port,slot=slot,rare=slot==3,hours='02:00–02:59'if slot==3 else 'Shop hours'))
 return result

def install(data,rom,edits):
 for row in validate(rom,edits):
  at=TOWNS+row['port']*37+29;data[at:at+4]=bytes(row['slots'])


def seeded_shuffle(rom,seed,blind=False,include_special=False,special_only=False):
 """Deterministic constrained swaps; preserve slot types and global item counts."""
 import random
 from character_mods import validate_seed
 seed=validate_seed(seed)
 if type(blind)is not bool or type(include_special)is not bool or type(special_only)is not bool:raise ValueError('Invalid item shuffle mode.')
 rng=random.Random('item-shops-v1:'+seed+(':blind'if blind else ':normal')+(':special'if special_only else ':all'if include_special else ':regular'));rows=stock(rom)
 for slots in (((3,),)if special_only else (range(3),(3,))if include_special else (range(3),)):
  positions=[(p,s)for p,row in enumerate(rows)for s in slots if row[s]!=255]
  for _ in range(len(positions)*40):
   if len(positions)<2:continue
   (a,x),(b,y)=rng.sample(positions,2);first,second=rows[a][x],rows[b][y]
   if a!=b and (second in rows[a]or first in rows[b]):continue
   rows[a][x],rows[b][y]=second,first
 return validate(rom,[dict(port=p,slots=row)for p,row in enumerate(rows)])
