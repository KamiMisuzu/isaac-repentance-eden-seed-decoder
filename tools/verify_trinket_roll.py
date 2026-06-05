from __future__ import annotations 
import argparse 
import sys 
from pathlib import Path 
ROOT=Path(__file__).resolve().parent.parent 
sys.path.insert(0,str(ROOT))
from tools.seed_codec import string_to_seed 
from tools.trinket_eden import load_trinket_pool,predict_eden_trinket_id,resolve_trinket_pool_path,roll_trinket_733ca0 

def main()-> None :
    ap=argparse.ArgumentParser()
    ap.add_argument('seed',nargs='?',help='e.g. "V9DC FN03"')
    ap.add_argument('--pool',type=Path,default=None,help='defaults to resolve_trinket_pool_path()')
    ap.add_argument('--want',type=int,default=None,help='expected id(omit to skip check)')
    ap.add_argument('--rng409',type=int,default=None,help='Frida pool_rng409 at 733CA0')
    args=ap.parse_args()
    pool_path=resolve_trinket_pool_path(args.pool)
    if pool_path is None :
        ap.error('no trinket pool; pass--pool or dump to data/profiles/.../trinket_pool.json')
    pool=load_trinket_pool(pool_path)
    if args.seed :
        u32=string_to_seed(args.seed.strip().upper())
        if u32 is None :
            ap.error(f'bad seed{args.seed!r}')
    else :
        u32=pool.start_seed or 0 
    (tid,idx,rng_used,rng_src)=predict_eden_trinket_id(u32,pool_path,rng409_override=args.rng409)
    (tid2,idx2)=roll_trinket_733ca0(pool,pool.rng409)
    print(f'pool:{pool_path} ({pool.count} entries)')
    print(f'startSeed=0x{u32: 08x} rng409={rng_used} (source={rng_src})')
    print(f'roll → id={tid} idx={idx}')
    print(f'roll(dump rng409 only) → id={tid2} idx={idx2}')
    if args.want is not None :
        ok=tid ==args.want 
        print(f"want{args.want}:{('OK' if ok else 'FAIL')}")
        raise SystemExit(0 if ok else 1)
if __name__ == "__main__":
    main()
