from __future__ import annotations 
from dataclasses import dataclass 
from tools.get_collectible import get_collectible_treasure 
from tools.rng import Rng 
PLAYER_SHIFTS=(3,4,17)
CBF_SHIFTS=(1,11,7)

@dataclass 
class EdenRoll :
    trinket : int|None 
    treasures : tuple[int,...]
    rng : Rng 

def _mix_roll(roll : int,s1 : int,s2 : int,s3 : int)-> int :
    x=roll&4294967295 
    x^=x>>s1 
    x^=(x^x>>s1)<<s2 
    x&=4294967295 
    x^=x>>s3 
    return x&4294967295 

def weighted_pick(roll : int,table : list[tuple[int,int]])-> int :
    total=sum((w for(_,w)in table))
    if total <=0 :
        return 0 
    (s1,s2,s3)=CBF_SHIFTS 
    bucket=_mix_roll(roll,s1,s2,s3)%total 
    acc=0 
    for(outcome,weight)in table :
        acc+=weight 
        if bucket <acc :
            return outcome 
    return table[-1][0]

def eden_procedural_table(*,achievement_159 : bool=False)-> list[tuple[int,int]]:
    if achievement_159 :
        return[(7,80)]
    return[(0,10)]

def simulate_eden_loop(rng : Rng,*,loops : int=5,table : list[tuple[int,int]]|None=None,skip_cases : bool=True)-> Rng :
    if table is None :
        table=eden_procedural_table()
    for _ in range(loops):
        roll=rng.next_u32()
        case=weighted_pick(roll,table)
        if skip_cases :
            if case in(0,1,2):
                rng.next_u32()
    return rng 

def roll_treasure(rng : Rng,*,pool_flags : int=1)-> int :
    rng.next_u32()
    seed=rng.next_u32()
    return get_collectible_treasure(seed,pool_flags=pool_flags)

def roll_eden_loadout(player_seed : int,*,pre_advance : int=0,third_treasure : bool=True,trinket_table : list[tuple[int,int]]|None=None)-> EdenRoll :
    rng=Rng(player_seed,*PLAYER_SHIFTS)
    for _ in range(pre_advance):
        rng.next_u32()
    simulate_eden_loop(rng)
    treasures=[roll_treasure(rng)]
    treasures.append(roll_treasure(rng))
    if third_treasure :
        treasures.append(roll_treasure(rng))
    if trinket_table is None :
        trinket_table=[(8,15)]
    roll=rng.next_u32()
    if weighted_pick(roll,trinket_table)==0 :
        rng.next_u32()
        tri_seed=rng.next_u32()
        trinket=_roll_trinket_id(tri_seed)
    else :
        trinket=None 
    return EdenRoll(trinket=trinket,treasures=tuple(treasures),rng=rng)

def _roll_trinket_id(seed : int)-> int :
    rng=Rng(seed,*PLAYER_SHIFTS)
    return rng.next_u32()%200+1 

def match_gold(start_seed : int,want_items : tuple[int,int],want_trinket : int|None,*,max_pre : int=4000)-> tuple[int,int,EdenRoll]|None :
    from tools.rng import expand_start_seed 
    streams=expand_start_seed(start_seed)
    for(si,sub)in enumerate(streams):
        for pre in range(max_pre):
            got=roll_eden_loadout(sub,pre_advance=pre,third_treasure=False)
            items=got.treasures[: 2]
            if items ==want_items or items ==want_items[::-1]:
                if want_trinket is None or got.trinket ==want_trinket :
                    return(si,pre,got)
    return None 
