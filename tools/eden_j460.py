from __future__ import annotations 
from pathlib import Path 
from tools.collectible_table import ProceduralTable 
from tools.game_rng import eden_7bc740_pocket,eden_treasure_loop,p988_from_a5,p988_from_start_seed,start_seed_to_a5 
from tools.seed_codec import string_to_seed 
ROOT=Path(__file__).resolve().parents[1]

def player_init_rng_755470(a5 : int)-> int :
    return p988_from_a5(a5)

def eden_treasure_indices(p988 : int,table : ProceduralTable,*,max_iter : int=100)-> tuple[int,int,int]:
    return eden_treasure_loop(p988,table,max_iter=max_iter)

def eden_starting_items(start_seed : int|str,table : ProceduralTable|None=None,*,proc_table_path : str|Path|None=None,trinket_pool_path : str|Path|None=None,p3ec : int|None=None)-> dict :
    if isinstance(start_seed,str):
        u32=string_to_seed(start_seed.strip().upper())
        if u32 is None :
            raise ValueError(f'bad seed string:{start_seed!r}')
    else :
        u32=int(start_seed)&4294967295 
    if table is None :
        table=ProceduralTable.load(proc_table_path)
    a5=start_seed_to_a5(u32)
    p988=p988_from_a5(a5)
    p3ec_val=int(p3ec)&4294967295 if p3ec is not None else p988 
    pool_s=str(trinket_pool_path)if trinket_pool_path else None 
    pocket=eden_7bc740_pocket(p3ec_val,trinket_pool_path=pool_s,start_seed=u32)
    (i1,i2,final_rng)=eden_treasure_indices(p988,table)
    (id1,id2)=table.indices_to_item_ids(i1,i2)
    return {
        "start_seed": u32,
        "a5_113620": a5,
        "p988": p988,
        "pocket_kind": pocket.kind,
        "pocket_trinket_id": pocket.trinket_id,
        "pocket_trinket_pool_idx": pocket.trinket_pool_idx,
        "pocket_card_id": pocket.card_id,
        "pocket_pill_effect": pocket.pill_effect,
        "pocket_roll_seed": pocket.roll_seed,
        "pocket_grant_mode": pocket.grant_mode,
        "index_passive_v161": i1,
        "index_active_v162": i2,
        "collectible1": id1,
        "collectible2": id2,
        "passive_id": id2,
        "active_id": id1,
        "rng_after": final_rng,
        "table_count": table.count,
    }

def verify_frida_golden(*,start_seed : int,a5 : int,p988 : int,items : tuple[int,int],table : ProceduralTable)-> dict :
    got_a5=start_seed_to_a5(start_seed)
    got_p988=p988_from_a5(a5)
    (i1,i2,_)=eden_treasure_indices(p988,table)
    (id1,id2)=table.indices_to_item_ids(i1,i2)
    got_items=(id1,id2)
    alt=(id2,id1)
    return{'a5_match': got_a5 ==a5,'p988_match': got_p988 ==p988,'items_match': got_items ==items or alt ==items,'indices':(i1,i2),'items': got_items}
