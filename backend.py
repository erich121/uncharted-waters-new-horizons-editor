"""Bounded stock-USA ship editing. No save access and no engine extensions."""
import hashlib,json,struct,zipfile
from decimal import Decimal,InvalidOperation
from pathlib import Path

ROM_SHA='64bc4707f422661a66618088887e2363a5f896ea683c58984fffd96dd21ab5f0'
TOOL_VERSION='0.1.0'
MODEL_BASE=0x8cbb6
SPEC_BASE=0x8ce27
FIELDS=('name','hull','turning','power','max_guns','min_crew','max_crew','price_gold')

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
    for key in set(original)-set(FIELDS):
        if row[key]!=original[key]:raise ValueError(f'{key} is read-only in version 1.')
    name=row['name']
    if not isinstance(name,str)or not name.strip()or len(name)>17 or '%'in name or any(ord(c)<32 or ord(c)>126 for c in name):
        raise ValueError('Ship names need 1–17 printable English characters, without %.')
    ranges=dict(hull=(1,100),turning=(1,100),power=(1,100),max_guns=(0,150),min_crew=(1,255),max_crew=(10,500),price_gold=(10,320000))
    for key,(low,high)in ranges.items():
        if type(row[key])is not int or not low<=row[key]<=high:raise ValueError(f'{key.replace("_"," ")} must be a whole number from {low} to {high}.')
    if row['max_crew']%10:raise ValueError('Maximum crew must be a multiple of 10.')
    if row['price_gold']%10:raise ValueError('The base price must be a multiple of 10 gold (0.001 bar).')
    if row['min_crew']>row['max_crew']:raise ValueError('Minimum crew cannot exceed maximum crew.')
    if row['max_guns']!=original['max_guns'] and row['max_guns']<original['factory_guns']:
        raise ValueError('The gun limit cannot be below the factory gun allocation.')
    if row['max_crew']!=original['max_crew'] and row['max_crew']<original['factory_crew']:
        raise ValueError('The crew limit cannot be below the existing factory crew allocation.')

def price_from_bars(value):
    try:
        amount=Decimal(str(value))*10000
        if not amount.is_finite()or amount!=amount.to_integral_value():raise ValueError()
        return int(amount)
    except (InvalidOperation,ValueError,OverflowError):raise ValueError('Enter a valid price in gold bars, in steps of 0.001 bar.')

def ips(base,modified):
    output=bytearray(b'PATCH');at=0
    while at<len(base):
        if base[at]==modified[at]:at+=1;continue
        start=at
        while at<len(base)and base[at]!=modified[at]and at-start<65535:at+=1
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
        data[offset:offset+len(payload)]=payload
    return bytes(data)

class ShipProject:
    def __init__(self,path):
        self.source=Path(path).resolve();self.rom,self.header=read_stock(self.source)
        self.original=decode(self.rom);self.ships=[dict(s)for s in self.original]
        self.project_path=None

    def update(self,i,values):
        if type(i)is not int or not 0<=i<25:raise ValueError('Invalid ship ID.')
        if set(values)-set(FIELDS):raise ValueError('Unknown editable fields.')
        row=dict(self.ships[i]);row.update(values);validate(row,self.original[i]);self.ships[i]=row

    def changes(self):
        for i,row in enumerate(self.ships):validate(row,self.original[i])
        return [dict(id=i,field=k,before=self.original[i][k],after=s[k])for i,s in enumerate(self.ships)for k in FIELDS if s[k]!=self.original[i][k]]

    def manifest(self):
        return dict(format='new-horizons-ship-project',version=1,base_sha256=ROM_SHA,
            edits=[dict(id=c['id'],field=c['field'],value=c['after'])for c in self.changes()])

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
        if set(m)!= {'format','version','base_sha256','edits'}or m['format']!='new-horizons-ship-project'or type(m['version'])is not int or m['version']!=1 or m['base_sha256']!=ROM_SHA or not isinstance(m['edits'],list):
            raise ValueError('Unsupported project or ROM revision.')
        rows=[dict(s)for s in self.original];seen=set()
        for e in m['edits']:
            if not isinstance(e,dict)or set(e)!={'id','field','value'}or type(e['id'])is not int or not 0<=e['id']<25 or e['field']not in FIELDS:
                raise ValueError('Invalid project edit.')
            key=(e['id'],e['field'])
            if key in seen:raise ValueError('Duplicate project edit.')
            seen.add(key);rows[e['id']][e['field']]=e['value']
        for i,row in enumerate(rows):validate(row,self.original[i])
        self.ships=rows;self.project_path=path

    def build(self):
        changes=self.changes()
        if not changes:return self.rom,[]
        data=bytearray(self.rom)
        offsets=dict(hull=1,turning=2,power=3,max_crew=4,min_crew=5,max_guns=8,price_gold=10)
        for c in changes:
            i=c['id'];field=c['field'];value=c['after']
            if field=='name':
                at=MODEL_BASE+i*25;data[at:at+18]=value.encode('ascii').ljust(18,b'\0')
            else:
                at=SPEC_BASE+i*12+offsets[field]
                if field=='price_gold':struct.pack_into('<H',data,at,value//10)
                else:data[at]=value//10 if field=='max_crew'else value
        data[0xffdc:0xffe0]=b'\xff\xff\0\0';check=sum(data)&65535
        struct.pack_into('<HH',data,0xffdc,check^65535,check)
        assert len(data)==len(self.rom)and sum(data)&65535==check
        return bytes(data),changes

    def export(self,path):
        path=Path(path).resolve()
        if path.suffix.lower()!='.sfc':raise ValueError('Choose a new .sfc output filename.')
        targets=[path,path.with_suffix('.ips'),path.with_suffix('.changes.json')]
        if self.source in targets or self.project_path in targets:raise ValueError('Output cannot replace the source game or project.')
        if any(p.exists()for p in targets):raise ValueError('An output file already exists. Choose a new filename to preserve previous versions.')
        rom,changes=self.build();patch=ips(self.rom,rom);assert apply_ips(self.rom,patch)==rom
        report=dict(tool='New Horizons Ship Editor',tool_version=TOOL_VERSION,base_sha256=ROM_SHA,output_sha256=sha(rom),
            input_header_removed=bool(self.header),output_headerless=True,changed_fields=changes,
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
