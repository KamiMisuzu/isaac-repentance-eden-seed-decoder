from __future__ import annotations 
SHIFT_TB : list[tuple[int,int,int]]=[(1,3,10),(1,5,16),(1,5,19),(1,9,29),(1,11,6),(1,11,16),(1,19,3),(1,21,20),(1,27,27),(2,5,15),(2,5,21),(2,7,7),(2,7,9),(2,7,25),(2,9,15),(2,15,17),(2,15,25),(2,21,9),(3,1,14),(3,3,26),(3,3,28),(3,3,29),(3,5,20),(3,5,22),(3,5,25),(3,7,29),(3,13,7),(3,23,25),(3,25,24),(3,27,11),(4,3,17),(4,3,27),(4,5,15),(5,3,21),(5,7,22),(5,9,7),(5,9,28),(5,9,31),(5,13,6),(5,15,17),(5,17,13),(5,21,12),(5,27,8),(5,27,21),(5,27,25),(5,27,28),(6,1,11),(6,3,17),(6,17,9),(6,21,7),(6,21,13),(7,1,9),(7,1,18),(7,1,25),(7,13,25),(7,17,21),(7,25,12),(7,25,20),(8,7,23),(8,9,23),(9,5,1),(9,5,25),(9,11,19),(9,21,16),(10,9,21),(10,9,25),(11,7,12),(11,7,16),(11,17,13),(11,21,13),(12,9,23),(13,3,17),(13,3,27),(13,5,19),(13,17,15),(14,1,15),(14,13,15),(15,1,29),(17,15,20),(17,15,23),(17,15,26)]
STAGE_COUNT=13 

class IsaacRng :
    __slots__=('seed','s1','s2','s3')

    def __init__(self,seed : int,s1 : int,s2 : int,s3 : int):
        self.seed=seed&4294967295 
        (self.s1,self.s2,self.s3)=(s1,s2,s3)

    @classmethod 
    def from_index(cls,seed : int,idx : int)->'IsaacRng':
        (s1,s2,s3)=SHIFT_TB[idx]
        return cls(seed,s1,s2,s3)

    def next(self)-> int :
        n=self.seed 
        n^=n>>self.s1 
        n^=n<<self.s2&4294967295 
        n^=n>>self.s3 
        self.seed=n&4294967295 
        return self.seed 

    def advance(self,k : int)-> int :
        res=self.seed 
        for _ in range(k+1):
            res=self.next()
        return res 

def to_room_seed(stage_seed : int)-> int :
    s=IsaacRng.from_index(stage_seed,35).advance(14)
    return IsaacRng.from_index(s,12).advance(1)

def to_entity_seed(room_spawn_seed : int)-> int :
    s=IsaacRng.from_index(room_spawn_seed,11).advance(6)
    return IsaacRng.from_index(s,35).next()

def init_seed(start_seed : int)-> tuple[int,int]:
    rng=IsaacRng(start_seed,3,23,25)
    stage_seeds=[rng.next()for _ in range(STAGE_COUNT+1)]
    player_init=rng.next()
    entity=to_entity_seed(to_room_seed(stage_seeds[STAGE_COUNT]))
    return(player_init,entity)

def drop_seed(start_seed : int)-> tuple[int,int]:
    (player_init,entity)=init_seed(start_seed)
    prng=IsaacRng(player_init,1,11,16)
    for _ in range(4):
        prng.next()
    return(prng.next(),entity)
