"""Starting trade economy/shipbuilding industry; native town words only."""
import copy
TOWNS=0x8DA7F
FIELDS={'economy':0,'industry':4}

def stock(rom):
 return [dict(port=p,**{k:int.from_bytes(rom[TOWNS+p*37+n:TOWNS+p*37+n+2],'little')for k,n in FIELDS.items()})for p in range(100)]

def validate(rom,edits):
 if not isinstance(edits,list):raise ValueError('Invalid economy edits.')
 originals=stock(rom);seen=set();result=[]
 for row in edits:
  if not isinstance(row,dict)or set(row)!={'port','economy','industry'}or type(row['port'])is not int or not 0<=row['port']<100 or row['port']in seen:raise ValueError('Choose unique trading ports.')
  seen.add(row['port'])
  if any(type(row[k])is not int or not 1<=row[k]<=1000 for k in FIELDS):raise ValueError('Economy and industry must be whole numbers from 1 to 1000.')
  if row!=originals[row['port']]:result.append(copy.deepcopy(row))
 return sorted(result,key=lambda r:r['port'])

def values(rom,edits):
 result=stock(rom)
 for row in validate(rom,edits):result[row['port']]=row
 return result

def update(rom,edits,port,**changes):
 if type(port)is not int or not 0<=port<100 or set(changes)-set(FIELDS):raise ValueError('Choose a trading port and valid economy fields.')
 rows=values(rom,edits);rows[port].update(changes)
 return validate(rom,rows)

def bulk(rom,edits,ports,mode,economy=None,industry=None):
 if not isinstance(ports,list)or not ports or any(type(p)is not int or not 0<=p<100 for p in ports)or len(set(ports))!=len(ports):raise ValueError('Choose a nonempty trading-port group.')
 if mode not in ('Set to','Add','Scale %'):raise ValueError('Choose a bulk operation.')
 targets={k:v for k,v in dict(economy=economy,industry=industry).items()if v is not None}
 if not targets:raise ValueError('Enter economy, industry, or both; blank leaves a value unchanged.')
 if any(type(v)is not int for v in targets.values()):raise ValueError('Bulk adjustments need whole numbers.')
 if mode=='Set to'and any(not 1<=v<=1000 for v in targets.values()):raise ValueError('Set values must be 1–1000.')
 if mode=='Add'and any(not -1000<=v<=1000 for v in targets.values()):raise ValueError('Add values must be -1000 to 1000.')
 if mode=='Scale %'and any(not 0<=v<=1000 for v in targets.values()):raise ValueError('Percentages must be 0–1000; 100 keeps the same value.')
 rows=values(rom,edits)
 for p in ports:
  for key,amount in targets.items():
   old=rows[p][key];new=amount if mode=='Set to'else old+amount if mode=='Add'else (old*amount+50)//100
   rows[p][key]=min(1000,max(1,new))
 return validate(rom,rows)

def install(data,rom,edits):
 for row in validate(rom,edits):
  for key,offset in FIELDS.items():
   at=TOWNS+row['port']*37+offset;data[at:at+2]=row[key].to_bytes(2,'little')

def projected(rom,edits):
 if not edits:return rom
 data=bytearray(rom);install(data,rom,edits);return bytes(data)
