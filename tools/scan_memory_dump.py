from __future__ import annotations 
import argparse 
import json 
import sys 
from pathlib import Path 
ROOT=Path(__file__).resolve().parent.parent 
sys.path.insert(0,str(ROOT))
from tools.profile_store import PROFILES_DIR,run_memory_extract 

def main()-> None :
    ap=argparse.ArgumentParser(description='Memory scan → data/profiles/')
    ap.add_argument('--exe',default='isaac-ng.exe')
    ap.add_argument('--pid',type=int,default=0)
    ap.add_argument('--profile',type=str,default='',help='subfolder under data/profiles')
    ap.add_argument('-v','--verbose',action='store_true')
    args=ap.parse_args()
    try :
        result=run_memory_extract(profile=args.profile or None,exe=args.exe,pid=args.pid or None)
    except Exception as e :
        print(f'Failed:{e}',file=sys.stderr)
        raise SystemExit(1)from e 
    if args.verbose :
        print(json.dumps(result,indent=2,ensure_ascii=False))
    print(f"Wrote{result['profile_dir']}/")
    print(f"  trinket_pool.json({result['trinket_count']} entries)")
    if result.get('proc'):
        print(f"  proc.json(count={result['proc_count']})")
    for w in result.get('warnings',[]):
        print(f'  !{w}')
if __name__ == "__main__":
    main()
