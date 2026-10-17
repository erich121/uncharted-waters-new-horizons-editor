"""Read-only commodity sources from native regional markets and town specialties."""
from discoveries import read_text
COUNT=46
MARKETS=0xb11a5
TOWNS=0x8da7f


def catalogue(rom):
    goods=[dict(id=i,name=read_text(rom,0xb0f07,i).replace('- ',''),sources=[])for i in range(COUNT)]
    for port in range(100):
        at=TOWNS+port*37;town=rom[at:at+37];region=town[33]
        if region>=13:raise ValueError('Invalid market region.')
        market=rom[MARKETS+region*128:MARKETS+(region+1)*128]
        offers=[(market[110+i],market[119+i]*10,'Regional')for i in range(9)if market[110+i]!=255]
        if town[26]!=255:offers.append((town[26],town[27]*10,'Specialty'))
        economy=int.from_bytes(town[:2],'little');seen=set()
        for good,required,kind in offers:
            if not 0<=good<COUNT or good in seen:raise ValueError('Invalid or duplicate market good.')
            seen.add(good)
            goods[good]['sources'].append(dict(port=port,economy_required=required,available_at_start=economy>=required,kind=kind))
    return goods
