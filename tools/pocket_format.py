from __future__ import annotations 
from tools.game_rng import Eden7bc740Pocket 
from tools.pocket_lookup import HUD_SLOT_CARD,HUD_SLOT_PILL,pickup_display_name,pocket_item_label 

def format_pocket_lines(pocket : Eden7bc740Pocket)-> list[str]:
    if pocket.kind =='trinket':
        if pocket.trinket_id is not None :
            extra=''
            if pocket.trinket_pool_idx is not None :
                extra=f' pool_idx={pocket.trinket_pool_idx}'
            return[f'  口袋(7BC740): 饰品 id={pocket.trinket_id}{extra}']
        return['  口袋(7BC740): 饰品(需 data/trinket_pool.json+--trinket-pool)']
    if pocket.kind =='none':
        return['  口袋(7BC740): 无']
    pid=pocket.pickup_id 
    if pid is None :
        pid=pocket.card_id if pocket.kind =='card'else pocket.pill_effect 
    if pid is None :
        return[f'  口袋(7BC740):{pocket.kind}']
    (type_lbl,name)=pocket_item_label(pocket.rng_fn,pid,pocket.grant_mode)
    slot_hint=''
    if pocket.grant_mode ==HUD_SLOT_PILL and pocket.rng_fn =='734900':
        slot_hint='（落在胶囊位图标）'
    elif pocket.grant_mode ==HUD_SLOT_CARD and pocket.rng_fn =='734180':
        slot_hint='（落在卡牌位）'
    return[f'  口袋(7BC740):{type_lbl}{name}{slot_hint}']
