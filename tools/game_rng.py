from __future__ import annotations 
from dataclasses import dataclass 
from tools.rng_consts import DWORD_B1F50C,QWORD_B1F504,mix_qword_dword,p988_from_a5,shifts_from_qword_dword 
QWORD_9EB880=98784247811 
DWORD_9EB880=25 
N_9EB880=15 
QWORD_7BC740_EDEN=21474836481 
DWORD_7BC740_EDEN=19 
QWORD_7E90F0_EDEN=38654705669 
DWORD_7E90F0_EDEN=7 
EDEN_SKIP_V61=frozenset({234,42,60})
QWORD_734180_PILL=12884901891 
DWORD_734180_PILL=29 

def mix_9eb880_step(seed : int)-> int :
    return mix_qword_dword(seed,QWORD_9EB880,DWORD_9EB880)

def start_seed_to_a5(start_seed : int)-> int :
    s=int(start_seed)&4294967295 
    for _ in range(N_9EB880):
        s=mix_9eb880_step(s)
    return s 

def eden_rng_step(seed : int)-> int :
    return mix_qword_dword(seed,QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)

def eden_7e90f0_at_v150(seed : int)-> int :
    return mix_qword_dword(seed,QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)

def eden_7e90f0_step(seed : int)-> int :
    return eden_7e90f0_at_v150(seed)

def mix_734900(seed : int)-> int :
    a=int(seed)&4294967295 
    t=a^a>>2 
    t=(t^(a^a>>2)<<7)&4294967295 
    return(t^t>>9)&4294967295 

def mix_734180_pill(seed : int)-> int :
    return mix_qword_dword(int(seed)&4294967295,QWORD_734180_PILL,DWORD_734180_PILL)
_EDEN_PILL_POOL60_SIZE=22 

def roll_pill_734180(roll_seed : int,*,pool30_pick : list[int]|None=None,pool60_size : int=_EDEN_PILL_POOL60_SIZE)-> int :
    seed=int(roll_seed)&4294967295 
    v7=mix_734180_pill(seed)
    if v7%25 ==0 and pool30_pick :
        from tools.rng import Rng 
        (s1,s2,s3)=shifts_from_qword_dword(QWORD_734180_PILL,DWORD_734180_PILL)
        idx=Rng(v7,s1,s2,s3).next_int(len(pool30_pick))
        return int(pool30_pick[idx])
    v7b=mix_734180_pill(v7)
    n=max(1,int(pool60_size))
    v13=v7b%n+1 
    v7c=mix_734180_pill(v7b)
    if 1 <=v13 <=22 and v7c%7 ==0 :
        v13+=55 
    return int(v13)&4294967295 

def roll_card_734900(roll_seed : int,*,soul_stone_unlock : bool=False,reversed_unlock : bool=False)-> int :
    v1=mix_734900(roll_seed)
    card=v1%13+1 
    v3=mix_734900(v1)
    if soul_stone_unlock and v3%140 ==0 :
        card=14 
    v4=mix_734900(v3)
    if reversed_unlock and v4%70 ==0 :
        card|=2048 
    return card 

@dataclass 
class Eden7bc740Pocket :
    kind : str 
    rng_fn : str|None=None 
    v150 : int|None=None 
    roll_seed : int|None=None 
    pickup_id : int|None=None 
    card_id : int|None=None 
    pill_effect : int|None=None 
    trinket_id : int|None=None 
    trinket_pool_idx : int|None=None 
    grant_mode : int|None=None 
    rng_after : int=0 

def eden_7bc740_pocket(p3ec : int,*,trinket_pool_path : str|None=None,start_seed : int|None=None,trinket_rng409 : int|None=None,trinket_use_cache : bool=False)-> Eden7bc740Pocket :
    v1=int(p3ec)&4294967295 
    v1=eden_rng_step(v1)
    if v1%3 ==0 :
        tri_id : int|None=None 
        tri_idx : int|None=None 
        if trinket_pool_path and start_seed is not None :
            from tools.trinket_eden import predict_eden_trinket_id 
            (tri_id,tri_idx,_,_)=predict_eden_trinket_id(start_seed,trinket_pool_path,rng409_override=trinket_rng409,use_cache=trinket_use_cache)
        return Eden7bc740Pocket(kind='trinket',trinket_id=tri_id,trinket_pool_idx=tri_idx,rng_after=v1)
    v1=eden_rng_step(v1)
    if v1&1 :
        return Eden7bc740Pocket(kind='none',rng_after=v1)
    v150=eden_rng_step(v1)
    roll=eden_7e90f0_at_v150(v150)
    if v150&1 :
        pid=roll_card_734900(roll)
        return Eden7bc740Pocket(kind='card',rng_fn='734900',v150=v150,roll_seed=roll,pickup_id=pid,card_id=pid,grant_mode=0,rng_after=v150)
    effect=roll_pill_734180(roll)
    return Eden7bc740Pocket(kind='pill',rng_fn='734180',v150=v150,roll_seed=roll,pickup_id=effect,pill_effect=effect,grant_mode=1,rng_after=v150)

def eden_pre_trinket_rng(v1 : int)-> int :
    return eden_7bc740_pocket(v1).rng_after 

def p988_from_start_seed(start_seed : int)-> int :
    return p988_from_a5(start_seed_to_a5(start_seed))
PLAYER_RNG_SHIFTS=(3,4,17)

def player_rng_step(seed : int)-> int :
    from tools.rng import rng_advance 
    return rng_advance(seed,*PLAYER_RNG_SHIFTS)

def eden_treasure_loop(p988 : int,table :'ProceduralTable',*,max_iter : int=100)-> tuple[int,int,int]:
    from tools.collectible_table import ProceduralTable 
    if not isinstance(table,ProceduralTable):
        raise TypeError('table must be ProceduralTable')
    if table.count <1 :
        raise ValueError('empty procedural table')
    v60=table.count-1 
    v1=eden_pre_trinket_rng(p988)
    v161=0 
    v162=0 
    for _ in range(max_iter):
        v1=eden_rng_step(v1)
        v61=v1%v60 if v60 else 0 
        if v61 in EDEN_SKIP_V61 :
            continue 
        v62=v61+1 
        ent=table.get(v62)
        if ent is None or ent.blocked :
            continue 
        if ent.is_passive_slot :
            if not v161 :
                v161=v62 
        elif not v162 :
            v162=v62 
        if v161 and v162 :
            break 
    return(v161,v162,v1)
