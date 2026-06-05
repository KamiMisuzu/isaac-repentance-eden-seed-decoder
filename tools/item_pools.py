from __future__ import annotations 
import re 
import xml.etree.ElementTree as ET 
from pathlib import Path 
ROOT=Path(__file__).resolve().parents[1]
POOL_PATH=ROOT/'itempools.xml'
_POOL_CACHE : dict[str,list[tuple[int,float]]]|None=None 

def load_pools()-> dict[str,list[tuple[int,float]]]:
    global _POOL_CACHE 
    if _POOL_CACHE is not None :
        return _POOL_CACHE 
    tree=ET.parse(POOL_PATH)
    pools : dict[str,list[tuple[int,float]]]={}
    for pool in tree.getroot().findall('Pool'):
        name=pool.attrib['Name'].lower()
        items : list[tuple[int,float]]=[]
        for item in pool.findall('Item'):
            item_id=int(item.attrib['Id'])
            weight=float(item.attrib.get('Weight','1'))
            if weight >0 :
                items.append((item_id,weight))
        pools[name]=items 
    _POOL_CACHE=pools 
    return pools 

def roll_pool(rng_seed : int,pool_name : str,*,s1 : int=3,s2 : int=3,s3 : int=3,max_attempts : int=20)-> int :
    items=load_pools()[pool_name.lower()]
    total=sum((w for(_,w)in items))
    rng=__import__('tools.rng',fromlist=['Rng']).Rng(rng_seed,s1,s2,s3)
    for _ in range(max_attempts):
        r=rng.next_float()*total 
        acc=0.0 
        for(item_id,weight)in items :
            acc+=weight 
            if r <=acc :
                return item_id 
    return items[-1][0]
