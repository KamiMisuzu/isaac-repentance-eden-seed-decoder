from __future__ import annotations 
HUD_SLOT_PILL=0 
HUD_SLOT_CARD=1 

def pocket_hud_kind(pocket) -> str:

    kind = getattr(pocket, "kind", None) or (pocket.get("kind") if isinstance(pocket, dict) else None)
    if kind == "trinket":
        return "trinket"
    if kind == "none":
        return "none"
    grant = getattr(pocket, "grant_mode", None)
    if grant is None and isinstance(pocket, dict):
        grant = pocket.get("grant_mode")
    if grant == HUD_SLOT_PILL:
        return "pill"
    if grant == HUD_SLOT_CARD:
        return "card"
    return kind or "none"

def pocket_hud_item_id(pocket) -> int | None:
    kind = getattr(pocket, "kind", None) or (pocket.get("kind") if isinstance(pocket, dict) else None)
    if kind == "trinket":
        return getattr(pocket, "trinket_id", None) if not isinstance(pocket, dict) else pocket.get("trinket_id")
    if kind == "card":
        return getattr(pocket, "card_id", None) if not isinstance(pocket, dict) else pocket.get("card_id")
    if kind == "pill":
        return getattr(pocket, "pill_effect", None) if not isinstance(pocket, dict) else pocket.get("pill_effect")
    if isinstance(pocket, dict):
        return pocket.get("pickup_id")
    return getattr(pocket, "pickup_id", None)
TAROT_CARD_NAMES : dict[int,str]={1 :'The Fool',2 :'The Magician',3 :'The High Priestess',4 :'The Emperor',5 :'The Empress',6 :'The Sun',7 :'The Moon',8 :'The Star',9 :'The Tower',10 :'The Devil',11 :'The Hanged Man',12 :'Death',13 :'Temperance',14 :'The Chariot',15 :'The Lovers',16 :'The Hermit',17 :'The Emperor?',18 :'The Hierophant',19 :'The World',20 :'Judgement',21 :'The World',22 :'The World'}
PILL_EFFECT_NAMES : dict[int,str]={0 :'Bad Gas',1 :'Bad Trip',2 :'Balls of Steel',3 :'Bombs are Key',4 :'Explosive Diarrhea',5 :'Full Health',6 :'Health Down',7 :'Health Up',8 :'I Found Pills',9 :'Puberty',10 :'Pretty Fly',11 :'Range Down',12 :'Range Up',13 :'Speed Down',14 :'Speed Up',15 :'Tears Down',16 :'Tears Up',17 :'Luck Down',18 :'Luck Up',19 :'Telepills',20 :'48 Hour Energy',21 :'Hematemesis',22 :'Horf',23 :'Sunshine',24 :'Vurp',25 :'Golden Pill'}
SOUL_STONE_ID=14 
REVERSED_CARD_FLAG=2048 

def hud_slot_label(grant_mode : int|None)-> str :
    if grant_mode ==HUD_SLOT_PILL :
        return '胶囊位'
    if grant_mode ==HUD_SLOT_CARD :
        return '卡片位(塔罗)'
    return f'slot={grant_mode}'

def _tarot_name(base : int,rev : str)-> str :
    if base ==SOUL_STONE_ID :
        return f'Soul Stone{rev}'
    if base in TAROT_CARD_NAMES :
        return TAROT_CARD_NAMES[base]+rev 
    return f'塔罗 #{base}{rev}'

def _pill_name(base : int,rev : str)-> str :
    if base in PILL_EFFECT_NAMES :
        return PILL_EFFECT_NAMES[base]+rev 
    if base >=56 :
        return f'马药 #{base}{rev}'
    return f'胶囊 #{base}{rev}'

def pickup_display_name(pickup_id : int,grant_mode : int|None=None,*,rng_fn : str|None=None)-> str :
    pid=int(pickup_id)&4294967295 
    base=pid&2047 
    rev=' (Reversed)'if pid&REVERSED_CARD_FLAG else ''
    if rng_fn =='734900':
        return _tarot_name(base,rev)
    if rng_fn =='734180':
        if grant_mode ==HUD_SLOT_CARD :
            return _tarot_name(base,rev)
        return _pill_name(base,rev)
    if grant_mode ==HUD_SLOT_PILL :
        if base in PILL_EFFECT_NAMES :
            return _pill_name(base,rev)
        return _tarot_name(base,rev)
    if grant_mode ==HUD_SLOT_CARD :
        return _tarot_name(base,rev)
    if base in PILL_EFFECT_NAMES :
        return _pill_name(base,rev)
    return _tarot_name(base,rev)

def pocket_item_label(rng_fn : str|None,pickup_id : int,grant_mode : int|None)-> tuple[str,str]:
    pid=int(pickup_id)&4294967295 
    base=pid&2047 
    rev=' (Reversed)'if pid&REVERSED_CARD_FLAG else ''
    if rng_fn =='734900':
        return('卡牌',_tarot_name(base,rev))
    if rng_fn =='734180':
        if grant_mode ==HUD_SLOT_PILL :
            return('胶囊',_pill_name(base,rev))
        if base >=56 or base >22 :
            return('胶囊',_pill_name(base,rev))
        if base in TAROT_CARD_NAMES :
            return('卡牌',_tarot_name(base,rev))
        return('胶囊',_pill_name(base,rev))
    name=pickup_display_name(pickup_id,grant_mode,rng_fn=rng_fn)
    if grant_mode ==HUD_SLOT_CARD :
        return('卡牌',name)
    return('胶囊',name)

def rng_branch_label(kind : str)-> str :
    if kind =='card':
        return '734900(v150奇)'
    if kind =='pill':
        return '734180 pool60(v150偶)'
    return kind 
