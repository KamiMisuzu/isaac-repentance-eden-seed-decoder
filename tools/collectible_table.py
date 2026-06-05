from __future__ import annotations 
import json 
from dataclasses import dataclass 
from pathlib import Path 
from typing import Callable 
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DUMP=ROOT/'data'/'procedural_collectibles.json'

@dataclass(frozen=True)
class CollectibleEntry :
    type_id : int 
    item_id : int 
    flag47 : int 

    @property 
    def is_passive_slot(self)-> bool :
        return self.type_id ==3 

    @property 
    def blocked(self)-> bool :
        return self.flag47&1 !=0 

@dataclass 
class ProceduralTable :
    entries : list[CollectibleEntry|None]

    @classmethod 
    def from_frida_dump(cls,data : dict)->'ProceduralTable':
        rows=data.get('entries')or data.get('out')
        if rows is None :
            raise ValueError("dump needs 'entries' array")
        entries : list[CollectibleEntry|None]=[]
        for row in rows :
            if row is None :
                entries.append(None)
            elif isinstance(row,dict):
                entries.append(CollectibleEntry(int(row['type']),int(row['id']),int(row.get('flag47',row.get('f47',0)))))
            else :
                entries.append(CollectibleEntry(int(row[0]),int(row[1]),int(row[2])if len(row)>2 else 0))
        return cls(entries)

    @classmethod 
    def load(cls,path : Path|str|None=None)->'ProceduralTable':
        p=Path(path)if path else DEFAULT_DUMP 
        if not p.is_file():
            raise FileNotFoundError(f'missing{p} — run Eden once with eden_hook.js and rpc.exports.dumpProcTable()')
        raw=p.read_text(encoding='utf-8').strip()
        if raw.startswith('"')and raw.endswith('"'):
            raw=json.loads(raw)
        data=json.loads(raw)if isinstance(raw,str)else raw 
        return cls.from_frida_dump(data)

    @property 
    def count(self)-> int :
        return len(self.entries)

    def get(self,v62 : int)-> CollectibleEntry|None :
        if v62 <0 or v62 >=len(self.entries):
            return None 
        return self.entries[v62]

    def entry_ok_factory(self,*,assume_unlocked : bool=True)-> Callable[...,bool]:

        def entry_ok(v62 : int,want_passive : bool|None=None)-> bool :
            ent=self.get(v62)
            if ent is None :
                return False 
            if ent.blocked :
                return False 
            if not assume_unlocked :
                return False 
            if want_passive is None :
                return True 
            if want_passive :
                return ent.is_passive_slot 
            return not ent.is_passive_slot 
        return entry_ok 

    def indices_to_item_ids(self,v161 : int,v162 : int)-> tuple[int,int]:
        a=self.get(v161)
        b=self.get(v162)
        return(a.item_id if a else 0,b.item_id if b else 0)
