from __future__ import annotations 
import sys 
from pathlib import Path 
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.eden_vanilla import match_gold,roll_eden_loadout 
from tools.rng import expand_start_seed 
from tools.seed_codec import string_to_seed 
GOLD=[('BGDM 9DPK',107593840,107,(58,531)),('VVDX T9MP',3509077760,150,(719,471)),('A3BW PYXX',162289967,None,(383,257)),('4WNT QT20',3681970362,133,(136,46)),('YBDL FXSF',2947145011,None,(484,118))]

def main()-> None :
    import argparse 
    p=argparse.ArgumentParser(description='Vanilla Eden sim from start seed')
    p.add_argument('seed',nargs='?',help='e.g. "BGDM 9DPK" or uint32')
    p.add_argument('--verify-gold',action='store_true')
    p.add_argument('--max-pre',type=int,default=4000)
    args=p.parse_args()
    if args.verify_gold or not args.seed :
       
        for(text,u32,tri,items)in GOLD :
            print(f'{text} ({u32})')
            print(f'  log: trinket{tri}  treasure{items}')
            hit=match_gold(u32,items,tri,max_pre=args.max_pre)
            if hit :
                (si,pre,got)=hit 
                print(f'  MATCH stream={si} pre_advance={pre}->{got.treasures} tri{got.trinket}')
            else :
                print("  NO MATCH")
            print()
        return 
    s=args.seed.strip()
    if s.isdigit():
        u32=int(s)&4294967295 
        label=str(u32)
    else :
        label=s.upper()
        decoded=string_to_seed(label)
        if decoded is None :
            print('invalid seed string')
            sys.exit(1)
        u32=decoded 
    streams=expand_start_seed(u32)
    print(f'seed{label}->{u32}')
    print(f'37 streams[0..2]:{streams[0]},{streams[1]},{streams[2]}')
    got=roll_eden_loadout(streams[0],pre_advance=0,third_treasure=False)
    print(f"stream0: treasures={got.treasures}")
if __name__ == "__main__":
    main()
