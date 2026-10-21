"""Nation/role-specific top-tier naval replacement selection; native fittings."""
import copy
from expansion import Code,far_jump
HELPER=0x21A000
TABLE=0x21A200
SITES=(0x9199F,0x91B6F)
NATIVE=bytes.fromhex('e2 20 a5 00 a0 07 00')
NATIONS=('Portugal','Spain','Ottoman','England','Italy','Holland')
SOURCES=(9,10,11,20)
ROLES=('Flagship (ship 1)','Second ship','Third ship','Fourth ship')

PRESETS={
    'stock':('Stock','Use the game’s original fleets.'),
    'flagships':('Stronger flagships','Upgrade only the flagship: Galleon to Barge, and Xebec to Venetian Galeass.'),
    'regional':('Regional variety','Upgrade flagships and add a fourth ship suited to each nation. Italy also gets mixed second and third ships. Portugal and Spain keep flagship-only changes.'),
    'stronger':('Stronger fleets','Upgrade the flagship, second ship and fourth ship. The third ship stays unchanged.'),
}

def preset(name='flagships'):
    if name not in PRESETS:raise ValueError('Unknown fleet preset.')
    rules=[[[-1,15,20,-1]if role==0 and name!='stock'else [-1]*4 for role in range(4)]for _ in NATIONS]
    if name=='regional':
        rules[2][3][2]=20
        rules[3][3][1]=15;rules[5][3][1]=15
        rules[4][0][0]=20;rules[4][1][0]=11;rules[4][2][0]=14;rules[4][3][0]=10
    elif name=='stronger':
        for nation in rules:
            nation[0][0]=10;nation[1]=[10,15,20,-1];nation[3]=[10,15,20,-1]
    return rules

def validate_rules(rules,ships,positions=4):
    if not isinstance(rules,list)or len(rules)!=6:raise ValueError('Fleet settings require six nations.')
    for nation in rules:
        if not isinstance(nation,list)or len(nation)!=positions:raise ValueError('Choose settings for the first four ships.')
        for role in nation:
            if not isinstance(role,list)or len(role)!=4:raise ValueError('Invalid fleet source rules.')
            if any(type(i)is not int or not -1<=i<len(ships)for i in role):raise ValueError('Fleet choice must refer to an existing ship or No change.')
    return copy.deepcopy(rules)

def resolve(ships,source,target):
    if target<0 or source==target:return None,'No change'
    return target+40,'Uses this ship’s normal guns and crew'

def compile_table(ships,rules):
    rules=validate_rules(rules,ships)
    return bytes(255 if (choice:=resolve(ships,source,target)[0])is None else choice
        for nation in rules for role in nation for source,target in zip(SOURCES,role))

def upgrades(ships):
    return [(source+40,target+40)for source,target in ((10,15),(11,20))if resolve(ships,source,target)[0]is not None]

def install(data,ships,rules=None):
    rules=preset()if rules is None else validate_rules(rules,ships)
    table=compile_table(ships,rules)
    if len(data)==0x200000:data.extend(b'\xff'*0x200000);data[0xffd7]=0x0c
    if len(data)!=0x400000:raise ValueError('Unsupported Custom Fleets ROM size.')
    for site in SITES:
        if data[site:site+len(NATIVE)]!=NATIVE:raise ValueError('Unsupported national fleet initializer.')
    # JSL+PHP+PHX add6 bytes: tier+9,nation+11,slot+15.
    c=Code().emit('08 da c2 30 a3 09 c9 02 00').branch_far(0xD0,'done')
    c.emit('a3 0b c9 06 00').branch_far(0xB0,'done')
    c.emit('a3 0f c9 04 00').branch_far(0xB0,'done')
    c.emit('a0 29 00 b1 26 29 f0 00').branch_far(0xD0,'done')
    c.emit('a5 26 cf 06 e8 7e').branch_far(0xF0,'done')
    # X=16*nation+4*slot. Temporary stack values are discarded before return.
    c.emit('a3 0b 0a 0a 0a 0a 48 a3 11 0a 0a 18 63 01 aa 68')
    for source in SOURCES:
        c.emit('a5 00 c9').emit((source+40).to_bytes(2,'little')).branch(0xF0,'pick').emit('e8')
    c.branch(0x80,'done').mark('pick').emit('bf').emit((TABLE+0xC00000).to_bytes(3,'little'))
    c.emit('29 ff 00 c9 ff 00').branch(0xF0,'done').emit('85 00')
    c.mark('done').emit('fa 28').emit(NATIVE).emit('6b');raw=c.finish()
    for at,payload in ((HELPER,raw),(TABLE,table)):
        if data[at:at+len(payload)]!=b'\xff'*len(payload):raise ValueError('Custom Fleets helper space is occupied.')
        data[at:at+len(payload)]=payload
    for site in SITES:data[site:site+7]=far_jump(0x22,HELPER)+b'\xea'*3
    return dict(enabled=True,experimental=True,helper=HELPER,helper_size=len(raw),table=TABLE,
        sites=list(SITES),rules=rules,occupied_positions_preserved=True,private_templates=False,persistent_ram=False)
