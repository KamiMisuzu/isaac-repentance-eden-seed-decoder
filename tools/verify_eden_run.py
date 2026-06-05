from __future__ import annotations 
import argparse 
import sys 
from pathlib import Path 
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.collectible_table import ProceduralTable 
from tools.eden_j460 import eden_treasure_indices 
from tools.game_rng import p988_from_a5,start_seed_to_a5 
from tools.seed_codec import seed_to_string 

def main()-> None :
    ap=argparse.ArgumentParser()
    ap.add_argument('--start',type=int,required=True)
    ap.add_argument('--a5',type=int,required=True)
    ap.add_argument('--p988',type=int,required=True)
    ap.add_argument('--v161',type=int,required=True,help='passive slot index(v62)')
    ap.add_argument('--v162',type=int,required=True,help='active slot index(v62)')
    ap.add_argument('--table',type=Path,default=None)
    args=ap.parse_args()
    got_a5=start_seed_to_a5(args.start)
    got_p988=p988_from_a5(args.a5)
    print('RNG')
    print(f'  start_seed={args.start}  ({seed_to_string(args.start)})')
    print(f'  a5:  got={got_a5}  want={args.a5}  ok={got_a5 == args.a5}')
    print(f'  p988: got={got_p988} want={args.p988} ok={got_p988 == args.p988}')
    table=ProceduralTable.load(args.table)
    (i1,i2,rng)=eden_treasure_indices(args.p988,table)
    (id1,id2)=table.indices_to_item_ids(i1,i2)
    want=(args.v161,args.v162)
    got=(i1,i2)
    print('7BC740')
    print(f'  indices: got={got} want={want} ok={got == want or got == want[::-1]}')
    print(f'  itemIds:{id1},{id2} (from table entry[id])')
    print(f'  table.count={table.count}  rng_after={rng}')
if __name__ == "__main__":
    main()
