from __future__ import annotations 
import json 
from dataclasses import dataclass 
from pathlib import Path 
from typing import Any 
from tools.game_rng import DWORD_9EB880,QWORD_9EB880,start_seed_to_a5 
from tools.rng_consts import mix_qword_dword 
from tools.xorshift32 import invert_mix 
QWORD_ITEMPOOL_EF890=QWORD_9EB880 
DWORD_ITEMPOOL_EF890=DWORD_9EB880 
QWORD_GAME_RNG=QWORD_ITEMPOOL_EF890 
DWORD_GAME_RNG=DWORD_ITEMPOOL_EF890 
QWORD_POOL_INIT=38654705665 
DWORD_POOL_INIT=29 
QWORD_POOL_ROLL=21474836481 
DWORD_POOL_ROLL=19 
QWORD_TRINKET_RETRY=38654705669 
DWORD_TRINKET_RETRY=7 
RNG_DEFAULT_INIT=2857319983 

@dataclass 
class TrinketPoolEntry :
    raw : int 
    flag4 : bool 
    flag5 : bool 

    @classmethod 
    def from_json(cls,o : dict[str,Any])-> TrinketPoolEntry :
        raw=o.get('raw',o.get('i'))
        if raw is None :
            raise KeyError('entry needs raw or i')
        return cls(raw=int(raw)&4294967295,flag4=bool(o.get('flag4',o.get('f4'))),flag5=bool(o.get('flag5',o.get('f5'))))

@dataclass 
class TrinketPoolSnapshot :
    start_seed : int|None 
    rng409 : int 
    rng_shr : int 
    rng_shl : int 
    rng_fin : int 
    entries : list[TrinketPoolEntry]
    available : int|None=None 

    @property 
    def count(self)-> int :
        return len(self.entries)

    @classmethod 
    def from_json(cls,data : dict[str,Any])-> TrinketPoolSnapshot :
        entries=[TrinketPoolEntry.from_json(e)for e in data.get('entries',[])]
        return cls(start_seed=data.get('startSeed'),rng409=int(data['rng409'])&4294967295,rng_shr=int(data.get('rngShr',1)),rng_shl=int(data.get('rngShl',5)),rng_fin=int(data.get('rngFin',19)),entries=entries,available=data.get('available'))

def _parse_pool_json(raw : str)-> dict[str,Any]:
    data : Any=json.loads(raw)
    if isinstance(data,str):
        data=json.loads(data)
    if not isinstance(data,dict):
        raise ValueError('trinket pool JSON must be an object')
    return data 

def load_trinket_pool(path : str|Path)-> TrinketPoolSnapshot :
    p=Path(path)
    data=_parse_pool_json(p.read_text(encoding='utf-8'))
    return TrinketPoolSnapshot.from_json(data)

def resolve_trinket_pool_path(explicit : str|Path|None=None)-> Path|None :
    from tools.profile_store import resolve_trinket_pool_path as _prof 
    p=_prof(Path(explicit)if explicit is not None else None)
    if p :
        return p 
    root=Path(__file__).resolve().parent.parent 
    legacy=root/'data'/'trinket_pool.json'
    return legacy if legacy.is_file()else None 

def save_trinket_pool(snapshot : TrinketPoolSnapshot,path : str|Path)-> None :
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    body={'startSeed': snapshot.start_seed,'rng409': snapshot.rng409,'rngShr': snapshot.rng_shr,'rngShl': snapshot.rng_shl,'rngFin': snapshot.rng_fin,'available': snapshot.available,'count': snapshot.count,'entries':[{'raw': e.raw,'flag4': e.flag4,'flag5': e.flag5}for e in snapshot.entries]}
    if snapshot.start_seed is not None :
        body['startSeed']=snapshot.start_seed 
    p.write_text(json.dumps(body,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def rng7e9020(state : int,shr : int,shl : int,fin : int,bound : int)-> tuple[int,int]:
    s=int(state)&4294967295 
    t=s^s>>shr 
    t=(t^t<<shl&4294967295)&4294967295 
    t=(t^t>>fin)&4294967295 
    if bound >0 :
        return(t,t%bound)
    return(t,0)

def mix_trinket_retry(seed : int)-> int :
    return mix_qword_dword(seed,QWORD_TRINKET_RETRY,DWORD_TRINKET_RETRY)

def itempool_ef890_step(state : int)-> int :
    return mix_qword_dword(state,QWORD_ITEMPOOL_EF890,DWORD_ITEMPOOL_EF890)

def game_rng_6ef890_step(state : int)-> int :
    return itempool_ef890_step(state)

def pool409_after_734f30(seed_a3 : int)-> int :
    return mix_qword_dword(int(seed_a3)&4294967295,QWORD_POOL_INIT,DWORD_POOL_INIT)

def trinket_a3_from_init113548(init113548 : int)-> int :
    s=int(init113548)&4294967295 
    s=itempool_ef890_step(s)
    return itempool_ef890_step(s)

def trinket_rng409_from_init113548(init113548 : int)-> int :
    return pool409_after_734f30(trinket_a3_from_init113548(init113548))

def trinket_a3_from_rng409(rng409 : int)-> int :
    from tools.rng_consts import shifts_from_qword_dword 
    (shr,shl,fin)=shifts_from_qword_dword(QWORD_POOL_INIT,DWORD_POOL_INIT)
    return invert_mix(int(rng409)&4294967295,shr,shl,fin)

def trinket_init113548_from_rng409(rng409 : int)-> int :
    from tools.rng_consts import shifts_from_qword_dword 
    a3=trinket_a3_from_rng409(rng409)
    (shr,shl,fin)=shifts_from_qword_dword(QWORD_ITEMPOOL_EF890,DWORD_ITEMPOOL_EF890)
    return invert_mix(invert_mix(a3,shr,shl,fin),shr,shl,fin)

@dataclass 
class TrinketSeedRng :
    rng409 : int 
    init113548 : int|None=None 

    def to_json(self)-> int|dict[str,int]:
        if self.init113548 is None :
            return int(self.rng409)&4294967295 
        return{'rng409': int(self.rng409)&4294967295,'init113548': int(self.init113548)&4294967295}

    @classmethod 
    def from_json_val(cls,v : Any)-> TrinketSeedRng :
        if isinstance(v,dict):
            rng=int(v['rng409'])&4294967295 
            init=v.get('init113548')
            return cls(rng409=rng,init113548=int(init)&4294967295 if init is not None else None)
        rng=int(v)&4294967295 
        return cls(rng409=rng,init113548=trinket_init113548_from_rng409(rng))

def trinket_rng_cache_path(pool_path : str|Path)-> Path :
    p=Path(pool_path)
    return p.parent/'trinket_rng_by_seed.json'

def load_trinket_rng_cache(pool_path : str|Path)-> dict[int,TrinketSeedRng]:
    path=trinket_rng_cache_path(pool_path)
    if not path.is_file():
        return{}
    data=json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data,str):
        data=json.loads(data)
    return{int(k)&4294967295 : TrinketSeedRng.from_json_val(v)for(k,v)in data.items()}

def save_trinket_rng_cache(pool_path : str|Path,cache : dict[int,TrinketSeedRng])-> None :
    path=trinket_rng_cache_path(pool_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    body={str(k): cache[k].to_json()for k in sorted(cache)}
    path.write_text(json.dumps(body,indent=2)+'\n',encoding='utf-8')

def record_trinket_rng_cache(pool_path : str|Path,start_seed : int,rng409 : int,*,init113548 : int|None=None)-> None :
    u32=int(start_seed)&4294967295 
    rng=int(rng409)&4294967295 
    init=int(init113548)&4294967295 if init113548 is not None else trinket_init113548_from_rng409(rng)
    cache=load_trinket_rng_cache(pool_path)
    cache[u32]=TrinketSeedRng(rng409=rng,init113548=init)
    save_trinket_rng_cache(pool_path,cache)

def trinket_init113548_from_start_seed(start_seed : int)-> int :
    return start_seed_to_a5(int(start_seed)&4294967295)

def trinket_rng409_for_start_seed(start_seed : int,*,pool_path : str|Path|None=None,init113548 : int|None=None,use_cache : bool=False)-> int|None :
    u32=int(start_seed)&4294967295 
    if init113548 is not None :
        return trinket_rng409_from_init113548(init113548)
    derived=trinket_init113548_from_start_seed(u32)
    if derived is not None :
        return trinket_rng409_from_init113548(derived)
    if use_cache and pool_path is not None :
        ent=load_trinket_rng_cache(pool_path).get(u32)
        if ent is not None :
            if ent.init113548 is not None :
                calc=trinket_rng409_from_init113548(ent.init113548)
                if calc ==ent.rng409 :
                    return calc 
            return ent.rng409 
    return None 

def trinket_rng409_for_eden(start_seed : int,pool : TrinketPoolSnapshot|None,*,pool_path : str|Path|None=None,rng409_override : int|None=None,use_cache : bool=False)-> tuple[int,str]:
    u32=int(start_seed)&4294967295 
    if rng409_override is not None :
        return(int(rng409_override)&4294967295,'override')
    computed=trinket_rng409_for_start_seed(u32,pool_path=pool_path,use_cache=use_cache)
    if computed is not None :
        src='cache'if use_cache else 'seed'
        return(computed,src)
    if pool and pool.start_seed is not None :
        if u32 ==int(pool.start_seed)&4294967295 :
            return(pool.rng409,'dump')
    return(0,'missing')

def roll_trinket_733ca0(pool : TrinketPoolSnapshot,rng409 : int|None=None)-> tuple[int,int]:
    n=pool.count 
    if n <=0 :
        raise ValueError('empty trinket pool')
    (shr,shl,fin)=(pool.rng_shr,pool.rng_shl,pool.rng_fin)
    state=int(rng409 if rng409 is not None else pool.rng409)&4294967295 
    (state,idx)=rng7e9020(state,shr,shl,fin,n)
    v5=state 
    max_tries=max(1,n>>1)
    for _ in range(max_tries):
        if 0 <=idx <n :
            ent=pool.entries[idx]
            if ent.flag4 and ent.flag5 :
                return(int(ent.raw)&32767,idx)
        v5=mix_trinket_retry(v5)
        idx=v5%n if n else 0 
    (state,idx)=rng7e9020(state,shr,shl,fin,n)
    for off in range(n):
        j=(idx+off)%n 
        ent=pool.entries[j]
        if ent.flag4 and ent.flag5 :
            return(int(ent.raw)&32767,j)
    return(int(pool.entries[idx].raw)&32767,idx)

def predict_eden_trinket_id(start_seed : int,pool_path : str|Path,*,rng409_override : int|None=None,use_cache : bool=False)-> tuple[int,int,int,str]:
    pool=load_trinket_pool(pool_path)
    (rng,src)=trinket_rng409_for_eden(start_seed,pool,pool_path=pool_path,rng409_override=rng409_override,use_cache=use_cache)
    if src =='missing':
        return(None,None,0,src)
    (tid,idx)=roll_trinket_733ca0(pool,rng)
    return(tid,idx,rng,src)
