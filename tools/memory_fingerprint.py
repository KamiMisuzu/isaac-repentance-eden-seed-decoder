from __future__ import annotations 
import struct 
from dataclasses import dataclass 
from typing import TYPE_CHECKING 
if TYPE_CHECKING :
    from tools.win_process_mem import ProcessMem 
from tools.win_process_mem import iter_regions,module_base 
MEM_PRIVATE=131072 
MEM_MAPPED=262144 
IDA_IMAGE_BASE=4194304 
IDA_GAME_GLOBAL_VA=13047416 
IDA_CONFIG_GLOBAL_VA=13047452 
CONFIG_PROC_TABLE_START=173060 
CONFIG_PROC_TABLE_END=173064 

def _rva(ida_va : int)-> int :
    return ida_va-IDA_IMAGE_BASE 
TRINKET_VEC_START=485*4 
TRINKET_VEC_END=486*4 
TRINKET_AVAIL=488*4 
TRINKET_RNG_SEED=409*4 
TRINKET_RNG_SHR=410*4 
TRINKET_RNG_SHL=411*4 
TRINKET_RNG_FIN=412*4 
TRINKET_MIN_TAIL=TRINKET_AVAIL+8 
PROC_ENTRY_TYPE=0 
PROC_ENTRY_ID=4 
PROC_ENTRY_FLAG47=47*4 

@dataclass 
class ScanHit :
    score : int 
    address : int 
    extra : dict 

def _u32(buf : bytes,off : int)-> int|None :
    if off+4 >len(buf):
        return None 
    return struct.unpack_from('<I',buf,off)[0]

def _ptr(buf : bytes,off : int,ptr_size : int)-> int|None :
    if ptr_size ==8 :
        if off+8 >len(buf):
            return None 
        return struct.unpack_from('<Q',buf,off)[0]
    if off+4 >len(buf):
        return None 
    return struct.unpack_from('<I',buf,off)[0]

def score_trinket_pool_buf(buf : bytes,pool_off : int,ptr_size : int)-> int :
    if pool_off+TRINKET_MIN_TAIL >len(buf):
        return 0 
    vs=_ptr(buf,pool_off+TRINKET_VEC_START,ptr_size)
    ve=_ptr(buf,pool_off+TRINKET_VEC_END,ptr_size)
    if vs is None or ve is None or vs ==0 or(ve ==0):
        return 0 
    if ptr_size ==4 and(vs <65536 or ve <65536 or vs >=2147352576):
        return 0 
    span=ve-vs 
    if span <=0 or span%8 !=0 :
        return 0 
    n=span//8 
    if n <60 or n >450 :
        return 0 
    score=40 
    avail=_u32(buf,pool_off+TRINKET_AVAIL)
    if avail is not None and avail <=n+8 :
        score+=8 
    shr=_u32(buf,pool_off+TRINKET_RNG_SHR)
    shl=_u32(buf,pool_off+TRINKET_RNG_SHL)
    fin=_u32(buf,pool_off+TRINKET_RNG_FIN)
    if shr ==1 and shl ==5 and(fin ==19):
        score+=15 
    elif shr ==3 and shl ==23 and(fin ==25):
        score+=10 
    return score 

def score_trinket_pool_live(pm : ProcessMem,pool_addr : int)-> int :
    vs=pm.read_ptr(pool_addr+TRINKET_VEC_START)
    ve=pm.read_ptr(pool_addr+TRINKET_VEC_END)
    if vs is None or ve is None or(not _valid_ptr(vs,pm))or(not _valid_ptr(ve,pm)):
        return 0 
    span=ve-vs 
    if span <=0 or span%8 !=0 :
        return 0 
    n=span//8 
    if n <60 or n >450 :
        return 0 
    score=40 
    avail=pm.read_u32(pool_addr+TRINKET_AVAIL)
    if avail is not None and avail <=n+8 :
        score+=8 
    shr=pm.read_u32(pool_addr+TRINKET_RNG_SHR)
    shl=pm.read_u32(pool_addr+TRINKET_RNG_SHL)
    fin=pm.read_u32(pool_addr+TRINKET_RNG_FIN)
    if shr ==1 and shl ==5 and(fin ==19):
        score+=15 
    elif shr ==3 and shl ==23 and(fin ==25):
        score+=10 
    sample=min(n,28)
    ok=0 
    for i in range(sample):
        ep=vs+i*8 
        raw=pm.read_u32(ep)
        if raw is None or raw >320 :
            continue 
        b=pm.read(ep+4,2)
        if not b or len(b)<2 :
            continue 
        if b[0]<=1 and b[1]<=1 :
            ok+=1 
    if ok <sample*0.55 :
        return 0 
    score+=ok*2 
    return score 

def _resolve_game_ptr(pm : ProcessMem)-> int|None :
    (base,_)=module_base(pm.pid)
    slot=base+_rva(IDA_GAME_GLOBAL_VA)
    p=pm.read_ptr(slot)
    if p and _valid_ptr(p,pm):
        return p 
    return None 

def _resolve_config_ptr(pm : ProcessMem)-> int|None :
    (base,_)=module_base(pm.pid)
    slot=base+_rva(IDA_CONFIG_GLOBAL_VA)
    p=pm.read_ptr(slot)
    if p and _valid_ptr(p,pm):
        return p 
    return None 

def find_trinket_pool_via_globals(pm : ProcessMem,*,min_score : int=55)-> ScanHit|None :
    game=_resolve_game_ptr(pm)
    if not game :
        return None 
    bands=((GAME_POOL_OFF_HINT-8192,GAME_POOL_OFF_HINT+8192,8),(524288,1310720,16))
    best : ScanHit|None=None 
    for(lo,hi,step)in bands :
        for off in range(lo,hi,step):
            if off <0 :
                continue 
            pool=game+off 
            sc=score_trinket_pool_live(pm,pool)
            if sc <min_score :
                continue 
            if best is None or sc >best.score :
                best=ScanHit(score=sc,address=pool,extra={'method':'global','gameOff': off})
        if best and best.score >=70 :
            break 
    return best 

def find_proc_table_via_globals(pm : ProcessMem,*,min_score : int=70)-> tuple[ScanHit|None,int,int]:
    cfg=_resolve_config_ptr(pm)
    if not cfg :
        return(None,0,0)
    st=pm.read_ptr(cfg+CONFIG_PROC_TABLE_START)
    en=pm.read_ptr(cfg+CONFIG_PROC_TABLE_END)
    if not st or not en :
        return(None,0,0)
    sc=score_proc_vector_live(pm,st,en)
    if sc <min_score :
        return(None,0,0)
    return(ScanHit(score=sc,address=cfg+CONFIG_PROC_TABLE_START,extra={'method':'global'}),st,en)

def read_trinket_pool(pm : ProcessMem,pool_addr : int,start_seed : int|None=None)-> dict :
    vs=pm.read_ptr(pool_addr+TRINKET_VEC_START)
    ve=pm.read_ptr(pool_addr+TRINKET_VEC_END)
    if vs is None or ve is None :
        raise ValueError('invalid trinket pool vectors')
    n=(ve-vs)//8 
    entries=[]
    for i in range(n):
        ep=vs+i*8 
        raw=pm.read_u32(ep)or 0 
        b=pm.read(ep+4,2)or b'\x00\x00'
        entries.append({'i': i,'raw': raw&4294967295,'flag4': b[0]!=0,'flag5': b[1]!=0})
    return{'startSeed': start_seed,'rng409':(pm.read_u32(pool_addr+TRINKET_RNG_SEED)or 0)&4294967295,'rngShr': pm.read_u32(pool_addr+TRINKET_RNG_SHR)or 1,'rngShl': pm.read_u32(pool_addr+TRINKET_RNG_SHL)or 5,'rngFin': pm.read_u32(pool_addr+TRINKET_RNG_FIN)or 19,'available':(pm.read_u32(pool_addr+TRINKET_AVAIL)or 0)&4294967295,'count': n,'entries': entries,'poolAddr': hex(pool_addr)}

def score_proc_vector_live(pm : ProcessMem,start : int,end : int)-> int :
    if not _valid_ptr(start,pm)or not _valid_ptr(end,pm):
        return 0 
    span=end-start 
    if span <=4 or span%pm.ptr_size !=0 :
        return 0 
    count=span//pm.ptr_size 
    if count <500 or count >950 :
        return 0 
    score=35 
    if pm.read_ptr(start)==0 :
        score+=5 
    matched=0 
    typed=0 
    sample=min(count-1,36)
    step=pm.ptr_size 
    for i in range(1,sample+1):
        ep=pm.read_ptr(start+i*step)
        if ep is None :
            return 0 
        if ep ==0 :
            continue 
        if not _valid_ptr(ep,pm):
            return 0 
        ty=pm.read_u32(ep+PROC_ENTRY_TYPE)
        id_=pm.read_u32(ep+PROC_ENTRY_ID)
        f47=pm.read_u32(ep+PROC_ENTRY_FLAG47)
        if ty is None or id_ is None or f47 is None :
            return 0 
        if ty not in(1,3,4):
            continue 
        typed+=1 
        if 1 <=id_ <=800 and f47 <=3 :
            matched+=1 
        if id_ ==i :
            matched+=1 
    if typed <sample*0.45 :
        return 0 
    score+=min(50,matched)
    return score 

def read_proc_table(pm : ProcessMem,start : int,end : int)-> dict :
    step=pm.ptr_size 
    count=(end-start)//step 
    entries : list[dict|None]=[None]
    for i in range(1,count):
        ep=pm.read_ptr(start+i*step)
        if ep is None or ep ==0 :
            entries.append(None)
            continue 
        entries.append({'type': pm.read_u32(ep+PROC_ENTRY_TYPE)or 0,'id': pm.read_u32(ep+PROC_ENTRY_ID)or 0,'flag47': pm.read_u32(ep+PROC_ENTRY_FLAG47)or 0})
    return{'count': count,'entries': entries,'vectorAddr': hex(start)}

def _valid_ptr(v : int,pm : ProcessMem)-> bool :
    if v ==0 :
        return False 
    if pm.ptr_size ==4 :
        return 65536 <=v <=2147352576 
    return 65536 <=v <=140737488355327 

def _find_trinket_pool_heap_scan(pm : ProcessMem,*,step : int=8,min_score : int=70,max_regions : int=0)-> ScanHit|None :
    best : ScanHit|None=None 
    nreg=0 
    for reg in iter_regions(pm):
        nreg+=1 
        if max_regions and nreg >max_regions :
            break 
        if reg.mtype not in(MEM_PRIVATE,MEM_MAPPED):
            continue 
        if reg.size >64*1024*1024 :
            continue 
        chunk=2*1024*1024 
        off=0 
        while off <reg.size :
            take=min(chunk,reg.size-off)
            base=reg.base+off 
            buf=pm.read(base,take)
            off+=take 
            if not buf or len(buf)<TRINKET_MIN_TAIL :
                continue 
            limit=len(buf)-TRINKET_MIN_TAIL 
            for po in range(0,limit,step):
                sc=score_trinket_pool_buf(buf,po,pm.ptr_size)
                if sc <55 :
                    continue 
                addr=base+po 
                live=score_trinket_pool_live(pm,addr)
                if live <min_score :
                    continue 
                if best is None or live >best.score :
                    best=ScanHit(score=live,address=addr,extra={'method':'heap_scan','region': hex(reg.base)})
    return best 

def find_trinket_pool(pm : ProcessMem,*,step : int=8,min_score : int=70,max_regions : int=0)-> ScanHit|None :
    hit=find_trinket_pool_via_globals(pm,min_score=min(55,min_score))
    if hit is not None :
        return hit 
    return _find_trinket_pool_heap_scan(pm,step=step,min_score=min_score,max_regions=max_regions)

def find_proc_table(pm : ProcessMem,*,min_score : int=75)-> tuple[ScanHit|None,int,int]:
    g=find_proc_table_via_globals(pm,min_score=min(70,min_score))
    if g[0]is not None :
        return g 
    best : ScanHit|None=None 
    best_start=0 
    best_end=0 
    pair_size=pm.ptr_size*2 
    for reg in iter_regions(pm):
        if reg.mtype not in(MEM_PRIVATE,MEM_MAPPED):
            continue 
        if reg.size >32*1024*1024 :
            continue 
        chunk=1024*1024 
        off=0 
        while off <reg.size :
            take=min(chunk,reg.size-off)
            base=reg.base+off 
            buf=pm.read(base,take)
            off+=take 
            if not buf or len(buf)<pair_size :
                continue 
            limit=len(buf)-pair_size 
            step_sz=pm.ptr_size 
            for o in range(0,limit,step_sz):
                st=_ptr(buf,o,pm.ptr_size)
                en=_ptr(buf,o+pm.ptr_size,pm.ptr_size)
                if st is None or en is None or st ==0 or(en ==0):
                    continue 
                if not _valid_ptr(st,pm)or not _valid_ptr(en,pm):
                    continue 
                span=en-st 
                if span <500*step or span >950*step or span%step !=0 :
                    continue 
                sc=score_proc_vector_live(pm,st,en)
                if sc <min_score :
                    continue 
                if best is None or sc >best.score :
                    best=ScanHit(score=sc,address=base+o,extra={})
                    best_start=st 
                    best_end=en 
    if best is None :
        return(None,0,0)
    return(best,best_start,best_end)
GAME_START_SEED_OFF=113544 
GAME_POOL_OFF_HINT=108352 

def guess_start_seed(pm : ProcessMem,pool_addr : int)-> int|None :
    for delta in(GAME_POOL_OFF_HINT,GAME_POOL_OFF_HINT-4096,GAME_POOL_OFF_HINT+4096):
        game=pool_addr-delta 
        if game <65536 :
            continue 
        s=pm.read_u32(game+GAME_START_SEED_OFF)
        if s and s !=4294967295 :
            return s&4294967295 
    return None 
