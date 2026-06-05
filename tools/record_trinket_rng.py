from __future__ import annotations 
import argparse 
import sys 
from pathlib import Path 
ROOT=Path(__file__).resolve().parent.parent 
sys.path.insert(0,str(ROOT))
from tools.trinket_eden import record_trinket_rng_cache,resolve_trinket_pool_path 

def main()-> None :
    ap=argparse.ArgumentParser()
    ap.add_argument('start_seed',type=int,help='Frida seed=… u32 or 0x…')
    ap.add_argument('rng409',type=int,help='Frida pool_rng409=…')
    ap.add_argument('--init113548',type=int,default=None,help='game+113548 at 6F5320_enter(optional; else derived from rng409)')
    ap.add_argument('--pool',type=Path,default=None)
    ap.add_argument('--profile',type=str,default='a524593562a57eb5',help='data/profiles/<id>/ when--pool omitted')
    args=ap.parse_args()
    pool=resolve_trinket_pool_path(args.pool)
    if pool is None :
        pool=ROOT/'data'/'profiles'/args.profile/'trinket_pool.json'
    if not pool.is_file():
        ap.error(f'pool not found:{pool}')
    u32=args.start_seed&4294967295 
    rng=args.rng409&4294967295 
    record_trinket_rng_cache(pool,u32,rng,init113548=args.init113548)
    print(f"Wrote{u32}-> rng409={rng} in{pool.parent/ 'trinket_rng_by_seed.json'}")
    if args.init113548 is not None :
        print(f'  init113548={args.init113548& 4294967295}')
if __name__ == "__main__":
    main()
