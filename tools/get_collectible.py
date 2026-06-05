from __future__ import annotations 
from tools.item_pools import load_pools 
from tools.rng import Rng 
POOL_TOTAL_WEIGHT : dict[int,float]={}

def pool_weight_sum(pool_id : int)-> float :
    if pool_id not in POOL_TOTAL_WEIGHT :
        items=load_pools()
        name=list(items.keys())[pool_id]if pool_id <len(items)else 'treasure'
        if pool_id ==0 :
            name='treasure'
        POOL_TOTAL_WEIGHT[pool_id]=sum((w for(_,w)in items.get(name,items['treasure'])))
    return POOL_TOTAL_WEIGHT[pool_id]
POOL_RNG_SHIFTS=(1,11,6)

def pick_from_pool(pool_id : int,roll_seed : int,*,flags : int=1)-> int :
    if pool_id ==0 :
        items=load_pools()['treasure']
    else :
        return 0 
    total=pool_weight_sum(pool_id)
    rng=Rng(roll_seed,*POOL_RNG_SHIFTS)
    r=rng.next_float()*total 
    acc=0.0 
    for(item_id,weight)in items :
        acc+=weight 
        if r <=acc :
            return item_id 
    return items[-1][0]

def get_collectible_treasure(roll_seed : int,*,pool_flags : int=1)-> int :
    return pick_from_pool(0,roll_seed,flags=pool_flags)
