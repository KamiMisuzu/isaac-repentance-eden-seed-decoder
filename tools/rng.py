from __future__ import annotations 
XOR_INIT=267354109 

def rng_advance(seed : int,shift1 : int,shift2 : int,shift3 : int)-> int :
    from tools.rng_consts import mix_qword_dword 
    qword=shift1&4294967295|(shift2&4294967295)<<32 
    return mix_qword_dword(seed,qword,shift3)

class Rng :
    __slots__=('seed','s1','s2','s3')

    def __init__(self,seed : int,s1 : int=3,s2 : int=13,s3 : int=17):
        self.seed=seed&4294967295 
        (self.s1,self.s2,self.s3)=(s1,s2,s3)

    def copy(self)->'Rng':
        r=Rng(self.seed,self.s1,self.s2,self.s3)
        return r 

    def next_u32(self)-> int :
        self.seed=rng_advance(self.seed,self.s1,self.s2,self.s3)
        return self.seed 

    def next_int(self,bound : int)-> int :
        if bound <=0 :
            return 0 
        return self.next_u32()%bound 

    def next_float(self)-> float :
        return self.next_u32()*2.3283062e-10 

def expand_stream(seed : int)-> int :
    s=seed&4294967295 
    if s ==0 :
        raise ValueError('RNG seed is zero')
    return rng_advance(s,3,13,7)

def expand_start_seed(start : int)-> list[int]:
    seeds : list[int]=[]
    s=start&4294967295 
    for _ in range(37):
        s=expand_stream(s)
        seeds.append(s)
    return seeds 

def player_rng_from_subseed(subseed : int)-> Rng :
    return Rng(subseed,3,4,17)
