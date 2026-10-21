"""Build genuine old-schema fixtures without leaking newer fields into them."""
import copy

INTRODUCED={
 'added_ships':2,'fixes':3,'original_availability':4,'portraits':6,
 'character_edits':7,'free_agent_shuffle':7,'gameplay':8,'goods_edits':12,
 'economy_edits':13,'custom_economy':14,'custom_goods':14,'custom_mates':14,
 'custom_captains':14,'custom_ships':15,'custom_items':16,'item_edits':16,
 'item_seed':17,'item_blind':17,'item_special':17,'item_special_only':17,
 'goods_shuffle':18,'shipbuilding_shuffle':19,'library_state':20,
 'ship_descriptions':22,'custom_characters':23,'discovery_rewrites':25,
 'fifty_year_campaign':26,'starting_gold':27,'instant_shipbuilding':28,
 'custom_discoveries':29,'item_price_edits':30,'discovery_easy':30,
}

def legacy_manifest(manifest,version=None):
    if not isinstance(manifest,dict)or manifest.get('format')!='new-horizons-ship-project':return copy.deepcopy(manifest)
    if version is None:version=manifest.get('version')
    result=copy.deepcopy(manifest);result['version']=version
    if type(version)is int and 1<=version<30:
        for field,introduced in INTRODUCED.items():
            if version<introduced:result.pop(field,None)
    return result
