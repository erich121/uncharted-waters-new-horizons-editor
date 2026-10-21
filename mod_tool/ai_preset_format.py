"""Small, name-based AI exchange translated into the validated native adapter.

Artwork references select existing pixels; image bytes never enter this format.
Version 1 remains supported by ai_presets.candidate for earlier exports.
"""
import copy
import hashlib

import ai_presets as legacy

ALIASES={'price_bars':'price_gold_bars','ports':'build_ports',
         'industry':'industry_required','description':'shipyard_description'}
SECTIONS={'edit_ships','add_ships','characters','ports','goods','items','gameplay','randomizers'}


def artwork(project):
    import portraits
    result={}
    for i,row in enumerate(project.original):
        result[f'A{i+1:02}']=dict(name=row['name'],source='Original',family=i,
                                  raw=portraits.original_raw(project.rom,i))
    for identity,(entry,raw,digest)in legacy.library_artwork(project).items():
        code='L'+hashlib.sha256((identity+digest).encode('utf-8')).hexdigest()[:12]
        if code in result:raise ValueError('Artwork reference collision. Export again after renaming the Library entry.')
        result[code]=dict(name=entry['ship']['name'],source='Library',family=entry['family'],raw=raw)
    for i,raw in project.portraits.items():
        family=project.library_bases.get(i,project.ships[i].get('base_hull',i))
        code='P'+hashlib.sha256(bytes([family])+raw).hexdigest()[:12]
        result.setdefault(code,dict(name=project.ships[i]['name'],source='Current project',family=family,raw=raw))
    return result


def reference(value,rows,label,key='name',prefix=None):
    if not isinstance(value,str):raise ValueError(label+' must be a name or an exported short reference.')
    if prefix and value.startswith(prefix) and value[len(prefix):].isdigit():
        index=int(value[len(prefix):])-1
        if 0<=index<len(rows):return index
    matches=[i for i,row in enumerate(rows)if row[key]==value]
    if len(matches)!=1:raise ValueError(f'{label} "{value}" is missing or ambiguous. Use its exported short reference.')
    return matches[0]


def record_list(value,label):
    if not isinstance(value,list)or any(not isinstance(row,dict)for row in value):raise ValueError(label+' must be a list of objects.')
    return copy.deepcopy(value)


def named_rows(rows,key,catalog,label,prefix=None):
    seen=set()
    for row in record_list(rows,label):
        if 'id'in row:raise ValueError('IDs are assigned by the editor; use exported names or short references.')
        index=reference(row.pop(key,None),catalog,label,prefix=prefix)
        if index in seen:raise ValueError('Duplicate '+label+' record.')
        seen.add(index);yield index,row


def export_document(project):
    old=legacy.parse(legacy.export_legacy(project))
    current=old['current'];refs=old['reference']
    port_names=[row['name']for row in refs['ports']]
    good_names={r['id']:r['name']for r in refs['goods']}
    item_names={r['id']:r['name']for r in refs['items']}
    art=artwork(project)
    def ship(row):
        row=copy.deepcopy(row);row['ship']=f"S{row.pop('id')+1:02}"
        for alias,native in ALIASES.items():
            if native in row:row[alias]=row.pop(native)
        row['ports']=[port_names[i]for i in row['ports']]
        return row
    from sailors import SKILLS
    characters=[]
    for row in current['characters']:
        row=copy.deepcopy(row);row['character']=f"C{row.pop('id')+1:03}"
        row['skills']=[name for _,name,bit in SKILLS if row.get('skills',0)&bit]
        characters.append(row)
    ports=[]
    for row,economy in zip(refs['ports'],current['ports']):
        ports.append(dict(port=row['name'],goods_economy=economy['goods_economy'],shipbuilding_economy=economy['shipbuilding_economy'],
                          shipyard=row['group']<11,capital=row['capital'],shipyard_spaces=row['shipyard_spaces']))
    guide=dict(
        instructions=[
            'Create a named preset. Return this JSON format with your requested edits. Keep format, version and context unchanged. You may omit guide and empty sections.',
            'When asked to design new ships, develop independent ship designs with distinct names, gameplay roles, specifications, prices, build locations and newly written shipyard descriptions. Follow any requested historical period or ship types. Recreate a particular named ship only when the user requests it.',
            'Omitted fields stay unchanged. Exporting and importing an unchanged document makes no edits. Import reviews and saves a preset; it does not load it.',
            'edit_ships: identify existing ships by name or S01-style reference. add_ships: require name, art, ports and industry. No IDs to allocate. For independent designs, explicitly provide hull_strength, sailing_power, turning, maximum_guns, minimum_sailors, crew_capacity, total_capacity, starting_guns, starting_crew_spaces, price_bars and description. Use stock ships as balance references and deliberately choose these values for each design. The importer permits omissions and falls back to stock-family values, but this fallback does not design a new ship for you.',
            'The artwork catalogue supplies portraits and matching map/battle visual families ONLY. Its family label describes the underlying game visuals, not the name or specifications of the new ship. Choose a suitable art code after designing the ship. Multiple independent designs may share a portrait. Library ship names, stats and descriptions are not design instructions and are not provided in this catalogue.',
            'Copy art codes exactly from guide.artwork and port names exactly from guide.ports. Never invent codes, infer Library ship identities or send image data. The AI cannot see a portrait from its code; family indicates the game visual type. Library/current art is embedded in the saved preset.',
            'ports on a ship is a replacement list of port names. industry is its shipbuilding requirement. price_bars uses 10000 gold per bar. Write an original description (shipyard text, 1..226 printable English characters without %) for each new design, although the importer accepts omitted descriptions for compatibility. Cargo is calculated.',
            'Ship names: 1..17 printable English characters without %. Hull, power and turning: 1..100. Guns: 0..200, at least starting guns. Minimum sailors: 1..255. Crew capacity: 10..500, multiples of 10. Total capacity: 1..2000. Price: .001..32 bars, steps of .001. Industry: 0..1000, steps of 10. Allocations must fit capacity. Starting guns and crew spaces can be edited for original and added ships; all allocations must fit the selected limits. Lowering crew_capacity below starting crew trims those spaces and frees cargo.',
            'Each shipyard holds at most 16 types. Capitals cannot develop further: new ships must be reachable at their starting shipbuilding economy. Ports edits can change starting economies first.',
            'characters: character name or C001 reference, attributes 0..100; navigation_level and battle_level 1..100 only for the six playable characters. skills is a list of skill names. Story companion skills may only be added.',
            'ports: port name and goods_economy and/or shipbuilding_economy (1..1000). goods: port and complete offers list, with good name, economy_required (0..2550, steps of 10), kind (Regional/Specialty), price (gold, 1..65535). Max nine Regional and one Specialty. items: port and four item names or null for empty, last slot is early-morning inventory.',
            'gameplay switches: repair_safeguard, fleet_control, custom_fleets, discovery_rewrites, discovery_easy (all discovery difficulties become 10), fifty_year_campaign, instant_shipbuilding. starting_gold is null for original or an integer 0..250000 gold pieces (25 bars); new games only. fleet_rules is the existing nation/role/source matrix, retaining dimensions, with ship names/references or null (unchanged). Newly added ships may be referenced by unique name.',
            'randomizers: people, goods, items, shipbuilding. Seeds must be four digits as TEXT. blind is boolean. People options: enabled, names, captain_names, mate_stats, captain_stats, ports, name_parts, stat_budget, mate_skills, captain_skills (booleans). stat_budget preserves each character’s attribute total. Goods mode: normal/specialty/all. Items mode: normal/special/all. Shipbuilding supports seed and blind only. Shuffles run before explicit edits.',
            'The guide is read-only reference. Put edits in the top-level operation sections, not the guide. Export includes blind results; share only if you want them revealed.'
        ],
        remaining_ship_slots=old['ship_capacity']['remaining_slots'],
        artwork=[dict(art=code,source=row['source'],family=project.original[row['family']]['name'])for code,row in art.items()],
        ship_fields=['ship (edits only)','name','art','ports','industry','price_bars','hull_strength','sailing_power','turning','maximum_guns','minimum_sailors','crew_capacity','total_capacity','starting_guns','starting_crew_spaces','description'],
        current_ships=[ship(r)for r in current['ships']],stock_ships=[ship(r)for r in refs['stock_ships']],
        characters=characters,skills=list(refs['skills']),ports=ports,
        goods=[dict(port=port_names[r['port']],offers=[dict(o,good=good_names[o['good']])for o in r['offers']])for r in current['goods']],
        items=[dict(port=port_names[r['port']],slots=[None if i==255 else item_names[i]for i in r['slots']])for r in current['items']],
        available_goods=list(good_names.values()),available_items=list(item_names.values()),
        gameplay=copy.deepcopy(current['gameplay']),fleet_labels=copy.deepcopy(refs['fleet_labels']))
    def fleet_names(value):
        if isinstance(value,list):return [fleet_names(v)for v in value]
        return None if value==-1 else f'S{value+1:02}'
    guide['gameplay']['fleet_rules']=fleet_names(guide['gameplay']['fleet_rules'])
    guide['fleet_labels']['source_ships']=[project.original[i]['name']for i in guide['fleet_labels'].pop('source_ship_ids')]
    return dict(format='new-horizons-ai-preset',version=2,context=legacy.fingerprint(project)[:16],name='My preset',description='',
                edit_ships=[],add_ships=[],characters=[],ports=[],goods=[],items=[],gameplay={},randomizers={},guide=guide)


def convert(project,data):
    allowed=SECTIONS|{'format','version','context','name','description','guide'}
    if set(data)-allowed or not {'format','version','context','name'}<=set(data)or data['format']!='new-horizons-ai-preset':raise ValueError('Unknown or missing AI preset field. Use the exported format.')
    if data['context']!=legacy.fingerprint(project)[:16]:raise ValueError('This preset was made for different settings. Export the current settings again.')
    from backend import ports
    from goods import catalogue as goods
    from items import catalogue as items
    from sailors import SKILLS
    port_rows=ports(project.economy_rom());good_rows=goods(project.rom);item_rows=items(project.rom)
    art=artwork(project);pictures={};changes={};descriptions=[]
    ship_rows=copy.deepcopy(project.ships)
    new_rows=record_list(data.get('add_ships',[]),'add_ships')
    for row in new_rows:ship_rows.append(dict(name=row.get('name')))
    def port(value):return port_rows[reference(value,port_rows,'Port')]['id']
    def ship_fields(row,new=False):
        fields=(set(legacy.SHIP_FIELDS)-{'build_ports','industry_required'})|set(ALIASES)|{'art','id'}
        if set(row)-fields:raise ValueError('Unknown ship field. Use the exported ship_fields list.')
        for alias,native in ALIASES.items():
            if alias in row:row[native]=row.pop(alias)
        if 'build_ports'in row:
            if not isinstance(row['build_ports'],list):raise ValueError('Ship ports must be a list of port names.')
            row['build_ports']=[port(v)for v in row['build_ports']]
        if 'art'in row:
            code=row.pop('art')
            if not isinstance(code,str)or code not in art:raise ValueError('Artwork reference is missing or changed. Export a fresh guide and use a listed art code.')
            selection=art[code];pictures[row['id']]=selection['raw']
            if new:row['visual_family']=selection['family']
            elif selection['family']!=project.library_bases.get(row['id'],project.ships[row['id']].get('base_hull',row['id'])):raise ValueError('Existing ship artwork must use its matching visual family.')
        elif new:raise ValueError('Each added ship requires an art code from the exported catalogue.')
        if not new and 'shipyard_description'in row:descriptions.append(dict(id=row['id'],text=row.pop('shipyard_description')))
        return row
    edits=[]
    for index,row in named_rows(data.get('edit_ships',[]),'ship',project.ships,'Ship','S'):
        if 'id'in row:raise ValueError('Ship IDs are assigned by the editor; use ship references.')
        edits.append(ship_fields(dict(row,id=index)))
    if any('id'in row for row in new_rows):raise ValueError('New ship IDs are assigned by the editor.')
    changes['ships']=edits
    changes['new_ships']=[ship_fields(dict(row,id=len(project.ships)+i),True)for i,row in enumerate(new_rows)]
    changes['descriptions']=descriptions
    characters=[project.character_record(i)for i in range(120)]
    changes['characters']=[]
    for index,row in named_rows(data.get('characters',[]),'character',characters,'Character','C'):
        if 'skills'in row:
            value=row['skills'];names={name:bit for _,name,bit in SKILLS}
            if not isinstance(value,list)or any(not isinstance(v,str)or v not in names for v in value)or len(set(value))!=len(value):raise ValueError('Skills must be a unique list of exported skill names.')
            row['skills']=sum(names[v]for v in value)
        changes['characters'].append(dict(row,id=index))
    changes['ports']=[dict(row,id=port_rows[index]['id'])for index,row in named_rows(data.get('ports',[]),'port',port_rows,'Port')]
    for section in ('goods','items'):
        changes[section]=[]
        for index,row in named_rows(data.get(section,[]),'port',port_rows,'Port'):
            if section=='goods':
                offers=record_list(row.get('offers'),'offers')
                for offer in offers:offer['good']=good_rows[reference(offer.get('good'),good_rows,'Good')]['id']
                row['offers']=offers
            else:
                if not isinstance(row.get('slots'),list):raise ValueError('Item slots must be a list.')
                row['slots']=[255 if v is None else item_rows[reference(v,item_rows,'Item')]['id']for v in row['slots']]
            changes[section].append(dict(row,port=port_rows[index]['id']))
    changes['gameplay']=copy.deepcopy(data.get('gameplay',{}));changes['randomizers']=copy.deepcopy(data.get('randomizers',{}))
    def fleet_ids(value):
        if isinstance(value,list):return [fleet_ids(v)for v in value]
        return -1 if value is None else reference(value,ship_rows,'Fleet ship','name','S')
    if isinstance(changes['gameplay'],dict)and 'fleet_rules'in changes['gameplay']:changes['gameplay']['fleet_rules']=fleet_ids(changes['gameplay']['fleet_rules'])
    result=dict(format='new-horizons-ai-preset',version=1,base=legacy.fingerprint(project),name=data['name'],description=data.get('description',''),changes=changes)
    # Resolve pixels only after the ordinary adapter has validated every edit.
    return result,pictures
