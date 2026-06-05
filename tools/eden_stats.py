from __future__ import annotations 
from dataclasses import dataclass,field 
from tools.game_rng import DWORD_7BC740_EDEN,QWORD_7BC740_EDEN,p988_from_a5,start_seed_to_a5 
from tools.rng_consts import mix_qword_dword,shifts_from_qword_dword 
from tools.get_collectible import get_collectible_treasure 
from tools.rng import Rng 
PLAYER_RNG_SHIFTS=(3,4,17)
CBF_SHIFTS=(1,11,7)
STAT_POST_SHIFTS=(2,0,9)
STAT_EXTRA_SHR=14 
BAB690_PROC_IDS=(34,36,41,44,45)
TEMPLATE_VAL1312_RANGE=260.0 
RANGE_GAME_DISPLAY_SCALE=40.0 
RANGE_BAR_BASE=230.0 
RANGE_BAR_SCALE=60.0 
PICKUP_HEART=10 
PICKUP_HALF_SOUL=30 
PICKUP_SOUL=40 
PICKUP_COIN=70 
PICKUP_NICKEL=300 
PICKUP_QUARTER=350 

@dataclass 
class EdenProfile :
    achievement_22 : bool=False 
    achievement_42 : bool=False 
    achievement_76 : bool=False 
    achievement_159 : bool=False 
    achievement_199 : bool=False 
    bonus_red : bool=False 
    bonus_soul : bool=False 
    bonus_black : bool=False 
    bonus_soul2 : bool=False 
    bonus_coin : bool=False 
    coop_eden_streak : bool=False 
    dlc_item_61_tier : int=0 
    has_forgotten_unlock : bool=False 

@dataclass 
class ProcCommand :
    cmd_type : int 
    a3 : int 
    a4 : int 
    rng : int 
    a6 : int=0 

@dataclass 
class EdenPanelHearts :
    red1232 : int=0 
    soul1235 : int=0 
    cap1233 : int=0 

    @property 
    def red_hud(self)-> float :
        return self.red1232/2.0 

@dataclass 
class Eden7bbbd0Rolls :
    red1232 : int=0 
    soul1235 : int=0 
    delta_5460_1365 : float=0.0 
    delta_5452_1363 : float=0.0 
    delta_5456_1364 : float=0.0 
    delta_5464_1366 : float=0.0 
    delta_5468_1367 : float=0.0 
    delta_5472_1368 : float=0.0 
    coin_flag_4956 : int=0 
    bomb_pills_4964 : int=0 
    pickup_bombs_4968 : int=0 

def eden_cap_from_profile(profile : EdenProfile)-> int :
    return 3 if profile.achievement_22 else 15 

def commands_before_first_treasure(cmds : list[ProcCommand])-> list[ProcCommand]:
    out : list[ProcCommand]=[]
    for c in cmds :
        if c.cmd_type ==5 and c.a3 ==100 :
            break 
        out.append(c)
    return out 

def apply_base_panel(cmds : list[ProcCommand],profile : EdenProfile)-> EdenPanelHearts :
    panel=EdenPanelHearts(cap1233=eden_cap_from_profile(profile))
    for c in commands_before_first_treasure(cmds):
        if c.cmd_type !=5 :
            continue 
        pid=c.a3 
        n=c.a4 if c.a4 >0 else 1 
        if pid ==PICKUP_HEART :
            for _ in range(n):
                panel.red1232=min(panel.red1232+2,2)
        elif pid ==PICKUP_HALF_SOUL :
            panel.soul1235+=1 
        elif pid ==PICKUP_SOUL :
            panel.soul1235+=1 
    return panel 

def eden_7bbbd0_base_panel(p988 : int,profile : EdenProfile|None=None)-> EdenPanelHearts :
    profile=profile or EdenProfile()
    p=int(p988)&4294967295 
    v64=mix_qword_dword(p,QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)
    v23=v64&3 
    red=2*v23 
    eden_sh=shifts_from_qword_dword(QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)
    bound=4-v23 if v23 else 4 
    soul=2*Rng(v64,*eden_sh).next_int(bound)
    if red ==0 and soul <=2 :
        soul=4 
    return EdenPanelHearts(red1232=red,soul1235=soul,cap1233=eden_cap_from_profile(profile))

def _eden_cfg_mix(seed : int)-> int :
    return mix_qword_dword(seed&4294967295,QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)

def _eden_cfg_mix_v69_v28(v69 : int,v28 : int)-> int :
    (s1,s2,s3)=shifts_from_qword_dword(QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)
    t=(v69^v28>>s1)&4294967295 
    u=(t^t<<s2&4294967295)&4294967295 
    return(u^u>>s3)&4294967295 

def _eden_stat_rng_step(seed : int)-> int :
    (s1,s2,s3)=shifts_from_qword_dword(QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)
    term=(seed^seed>>s1)&4294967295 
    mid=(term^term<<s2&4294967295)&4294967295 
    return(mid^mid>>s3)&4294967295 

def _u32_to_float01(u : int)-> float :
    return(u&4294967295)*2.3283062e-10 

def eden_7bbbd0_rolls(p988 : int)-> Eden7bbbd0Rolls :
    p=int(p988)&4294967295 
    eden_sh=shifts_from_qword_dword(QWORD_7BC740_EDEN,DWORD_7BC740_EDEN)
    v64=_eden_cfg_mix(p)
    v23=v64&3 
    red=2*v23 
    bound=4-v23 if v23 else 4 
    soul_rng=Rng(v64,*eden_sh)
    soul=2*soul_rng.next_int(bound)
    if red ==0 and soul <=2 :
        soul=4 
    v27=_eden_cfg_mix(soul_rng.seed)
    v69=v27 
    coin_flag=0 
    bomb_pills=0 
    pickup_bombs=0 
    if v27%3 :
        v28=_eden_cfg_mix(v27)
        v69=v28 
        if v28&1 :
            v69=_eden_cfg_mix_v69_v28(v69,v28)
            v29=v69 
            v64=v69 
            rem=v69%3 
            if rem ==2 :
                bomb_pills=Rng(v64,*eden_sh).next_int(2)+1 
                v69=v64 
            elif rem ==1 :
                coin_flag=1 
            else :
                v69=_eden_cfg_mix(v29)
                pickup_bombs=v69%5+1 
    v28=v69 
    v30=_eden_cfg_mix_v69_v28(v69,v28)
    u=_u32_to_float01(v30)
    spd=u+u-1.0 
    v32=v30 
    v68=_eden_cfg_mix_v69_v28(v30,v32)
    tears_small=_u32_to_float01(v68)*0.30000001-0.15000001 
    v36=_eden_stat_rng_step(v68)
    tears_mid=_u32_to_float01(v36)*1.5-0.75 
    v38=_eden_stat_rng_step(v36)
    rng_delta=_u32_to_float01(v38)*120.0-60.0 
    v40=_eden_stat_rng_step(v38)
    shotspeed=_u32_to_float01(v40)*0.5-0.25 
    v42=_eden_stat_rng_step(v40)
    u2=_u32_to_float01(v42)
    luck=u2+u2-1.0 
    return Eden7bbbd0Rolls(red1232=red,soul1235=soul,delta_5460_1365=spd,delta_5452_1363=tears_small,delta_5456_1364=tears_mid,delta_5464_1366=rng_delta,delta_5468_1367=shotspeed,delta_5472_1368=luck,coin_flag_4956=coin_flag,bomb_pills_4964=bomb_pills,pickup_bombs_4968=pickup_bombs)

def range_val1312_to_game_display(val1312 : float)-> float :
    return val1312/RANGE_GAME_DISPLAY_SCALE 

def range_internal_to_game_display(delta_internal : float)-> float :
    return delta_internal/RANGE_GAME_DISPLAY_SCALE 

def range_internal_to_bar_delta(delta_internal : float)-> float :
    return delta_internal/RANGE_BAR_SCALE 

def range_internal_to_val1312(delta_internal : float)-> float :
    return TEMPLATE_VAL1312_RANGE+delta_internal 

def wiki_deltas_dict(rolls : Eden7bbbd0Rolls)-> dict[str,float]:
    rng=rolls.delta_5464_1366 
    return{'damage': rolls.delta_5460_1365,'speed': rolls.delta_5452_1363,'tears': rolls.delta_5456_1364,'range': rng,'rangeGame': range_internal_to_game_display(rng),'rangeBar': range_internal_to_bar_delta(rng),'range1312': range_internal_to_val1312(rng),'shotSpeed': rolls.delta_5468_1367,'luck': rolls.delta_5472_1368}

def format_wiki_deltas_line(rolls : Eden7bbbd0Rolls)-> str :
    d=wiki_deltas_dict(rolls)
    return f"伤害Δ={d['damage']} 移速Δ={d['speed']} 攻速Δ={d['tears']} 射程Δ={d['range']} 面板射程Δ≈{d['rangeGame']:.4f} 弹速Δ={d['shotSpeed']} 幸运Δ={d['luck']}"

def format_range_hud_hint(rolls : Eden7bbbd0Rolls)-> str :
    d=wiki_deltas_dict(rolls)
    tpl_game=range_val1312_to_game_display(TEMPLATE_VAL1312_RANGE)
    post_game=range_val1312_to_game_display(d['range1312'])
    return f"游戏射程≈{post_game:.2f} (模板{tpl_game:.2f}+面板射程Δ≈{d['rangeGame']:.4f}; 即射程1312≈{d['range1312']:.2f}={TEMPLATE_VAL1312_RANGE:.0f}+射程Δ)"

def wiki_deltas_from_p988(p988 : int,*,p3ec : int|None=None)-> tuple[Eden7bbbd0Rolls,dict[str,float]]:
    seed=int(p3ec if p3ec is not None else p988)&4294967295 
    rolls=eden_7bbbd0_rolls(seed)
    return(rolls,wiki_deltas_dict(rolls))

def wiki_deltas_from_start_seed(start_seed : int,*,p3ec : int|None=None)-> tuple[int,int,Eden7bbbd0Rolls,dict[str,float]]:
    u32=int(start_seed)&4294967295 
    a5=start_seed_to_a5(u32)
    p988=p988_from_a5(a5)
    (rolls,wiki)=wiki_deltas_from_p988(p988,p3ec=p3ec)
    return(u32,p988,rolls,wiki)

@dataclass 
class EdenStatsResult :
    start_seed : int 
    a5_113620 : int 
    p988 : int 
    p988_after : int 
    commands : list[ProcCommand]=field(default_factory=list)
    stat_rolls : list[float]=field(default_factory=list)
    treasure_items : list[int]=field(default_factory=list)
    trinket_item : int|None=None 
    panel_base : EdenPanelHearts=field(default_factory=EdenPanelHearts)
    hearts_red : int=0 
    hearts_soul : int=0 
    hearts_black : int=0 
    empty_heart : int=0 
    bombs : int=0 
    keys : int=0 
    coins_pickup : int=0 
    outer_loop_cases : list[int]=field(default_factory=list)
    final_layout_case : int=-1 

def player_rng_from_p988(p988 : int)-> Rng :
    return Rng(p988,*PLAYER_RNG_SHIFTS)

def weighted_pick(roll : int,table : list[tuple[int,int]])-> int :
    total=sum((w for(_,w)in table))
    if total <=0 :
        return 0 
    (s1,s2,s3)=CBF_SHIFTS 
    x=roll&4294967295 
    x^=x>>s1 
    x=(x^(x^x>>s1)<<s2)&4294967295 
    x^=x>>s3 
    bucket=x%total 
    acc=0 
    for(outcome,weight)in table :
        acc+=weight 
        if bucket <acc :
            return outcome 
    return table[-1][0]

def _mix_roll(roll : int,s1 : int,s2 : int,s3 : int)-> int :
    x=roll&4294967295 
    x^=x>>s1 
    x=(x^(x^x>>s1)<<s2)&4294967295 
    x^=x>>s3 
    return x&4294967295 

def eden_outer_pool(profile : EdenProfile)-> list[tuple[int,int]]:
    if profile.achievement_159 :
        return[(7,80)]
    return[(0,10),(5,10),(3,58)]

def default_heart_layout_pool(profile : EdenProfile)-> list[tuple[int,int]]:
    w6=3 if profile.achievement_22 else 15 
    pool : list[tuple[int,int]]=[(1,5),(2,13),(3,13),(4,7),(5,7),(6,w6),(7,15),(8,15)]
    if profile.dlc_item_61_tier <=2 :
        pool=_add_weight(pool,1,5)
    return pool 

def _add_weight(pool : list[tuple[int,int]],kind : int,add : int)-> list[tuple[int,int]]:
    out : list[tuple[int,int]]=[]
    found=False 
    for(k,w)in pool :
        if k ==kind :
            out.append((k,w+add))
            found=True 
        else :
            out.append((k,w))
    if not found :
        out.append((kind,add))
    return out 

def _heart_pool_case37(profile : EdenProfile,case192 : int)-> list[tuple[int,int]]:
    if case192 ==7 :
        w1=4 if profile.achievement_22 else 20 
        return[(1,w1),(2,10),(3,20),(4,5),(5,5),(6,5),(7,5),(8,5)]
    return[(0,35),(1,20),(2,15),(3,30)]

def _enqueue_pickup(cmds : list[ProcCommand],pickup_id : int,rng : Rng)-> None :
    seed=rng.next_u32()
    cmds.append(ProcCommand(5,pickup_id,0,seed,0))

def _roll_treasure(rng : Rng)-> int :
    s1=rng.next_u32()
    s2=rng.next_u32()
    return get_collectible_treasure(s2,pool_flags=1)

def _roll_trinket_pool9(rng : Rng)-> int :
    s=rng.next_u32()
    tr=Rng(s,*PLAYER_RNG_SHIFTS)
    return tr.next_u32()%200+1 

def stat_delta_from_cmd_seed(seed : int,slot : int,*,scale : float=1.0)-> float :
    t=_mix_roll(seed,*STAT_POST_SHIFTS)
    t2=t^t>>3 
    t2=(t2^(t2^t>>3)<<2)&4294967295 
    t2^=t2>>STAT_EXTRA_SHR 
    u=t2*2.3283062e-10 
    delta=u*3.1400001*2.0 
    eden=min(slot*0.05+0.4,1.0)
    return delta*scale*eden 

def _simulate_case37_hearts(cmds : list[ProcCommand],rng : Rng,profile : EdenProfile,inner : list[tuple[int,int]],base_iters : int,case192 : int)-> None :
    v313=max(2,base_iters)
    if profile.bonus_coin :
        _enqueue_pickup(cmds,PICKUP_NICKEL,rng)
    elif profile.bonus_black :
        _enqueue_pickup(cmds,PICKUP_COIN,rng)
    elif profile.bonus_soul2 :
        _enqueue_pickup(cmds,PICKUP_SOUL,rng)
    elif profile.bonus_red :
        _enqueue_pickup(cmds,PICKUP_HEART,rng)
    elif profile.bonus_soul :
        _enqueue_pickup(cmds,PICKUP_HALF_SOUL,rng)
    if profile.achievement_42 :
        v313+=1 
    if profile.achievement_199 :
        v313*=2 
    for _ in range(v313):
        roll=rng.next_u32()
        pick=weighted_pick(roll,inner)
        if pick ==0 :
            n=rng.next_int(3)+1 
            for _ in range(n):
                _enqueue_pickup(cmds,20,rng)
        elif pick ==1 :
            _enqueue_pickup(cmds,PICKUP_HEART,rng)
        elif pick ==2 :
            _enqueue_pickup(cmds,PICKUP_HALF_SOUL,rng)
        elif pick ==3 :
            _enqueue_pickup(cmds,PICKUP_SOUL,rng)
        elif pick ==4 :
            _enqueue_pickup(cmds,PICKUP_COIN,rng)
        elif pick ==5 :
            _enqueue_pickup(cmds,PICKUP_NICKEL,rng)
        elif pick ==6 :
            pass 
        elif pick ==7 :
            _enqueue_pickup(cmds,PICKUP_QUARTER,rng)
        elif pick ==8 :
            _enqueue_pickup(cmds,90,rng)

def simulate_6dae40_eden(p988 : int,profile : EdenProfile|None=None)-> EdenStatsResult :
    profile=profile or EdenProfile()
    rng=player_rng_from_p988(p988)
    cmds : list[ProcCommand]=[]
    outer_cases : list[int]=[]
    if profile.has_forgotten_unlock :
        rng.next_int(2)
    outer=eden_outer_pool(profile)
    loops=5 
    for _ in range(loops):
        roll=rng.next_u32()
        case=weighted_pick(roll,outer)
        outer_cases.append(case)
        if case ==0 :
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,350,0,seed,0))
        elif case ==1 :
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,50,0,seed,0))
        elif case ==2 :
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,60,0,seed,0))
        elif case in(3,7):
            mod=7 if profile.achievement_159 or case ==7 else 4 
            rem=rng.next_int(mod)
            base_iters=rem if rem >2 else 2 
            inner=_heart_pool_case37(profile,case)
            _simulate_case37_hearts(cmds,rng,profile,inner,base_iters,case)
        elif case ==4 :
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,70,0,seed,0))
        elif case ==5 :
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,300,0,seed,0))
    for _ in range(3):
        item=_roll_treasure(rng)
        cmds.append(ProcCommand(5,100,item,rng.next_u32(),0))
    if profile.coop_eden_streak :
        s1=rng.next_u32()
        item=get_collectible_treasure(rng.next_u32(),pool_flags=1|512)
        cmds.append(ProcCommand(5,100,item,s1,0))
    layout=default_heart_layout_pool(profile)
    roll=rng.next_u32()
    final_case=weighted_pick(roll,layout)
    if final_case ==0 :
        s1=rng.next_u32()
        tri=_roll_trinket_pool9(rng)
        cmds.append(ProcCommand(5,100,tri,s1,0))
    elif final_case ==1 :
        cmds.append(ProcCommand(0,1,0,0,0))
    elif final_case ==2 :
        s1=rng.next_u32()
        cmds.append(ProcCommand(85,0,0,s1,0))
        s2=rng.next_u32()
        cmds.append(ProcCommand(85,0,0,s2,0))
    elif final_case ==3 :
        seed=rng.next_u32()
        cmds.append(ProcCommand(4,4,0,seed,0))
    elif final_case ==4 :
        for _ in range(3):
            seed=rng.next_u32()
            cmds.append(ProcCommand(3,43,0,seed,0))
    elif final_case ==5 :
        for _ in range(3):
            seed=rng.next_u32()
            cmds.append(ProcCommand(3,73,0,seed,0))
    elif final_case ==6 :
        seed=rng.next_u32()
        cmds.append(ProcCommand(5,10,3,seed,0))
        if rng.next_int(2)==0 and(not profile.achievement_22):
            seed2=rng.next_u32()
            cmds.append(ProcCommand(5,10,3,seed2,0))
    elif final_case ==7 :
        for _ in range(2):
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,40,3,seed,0))
    elif final_case ==8 :
        for _ in range(2):
            seed=rng.next_u32()
            cmds.append(ProcCommand(5,70,0,seed,0))
    if profile.achievement_76 and profile.dlc_item_61_tier >1 :
        if rng.next_u32()&1 :
            _enqueue_pickup(cmds,PICKUP_HEART,rng)
        else :
            _enqueue_pickup(cmds,PICKUP_COIN,rng)
    return _988_result(p988,rng,cmds,outer_cases,final_case,profile)

def _988_result(p988 : int,rng : Rng,cmds : list[ProcCommand],outer_cases : list[int],final_case : int,profile : EdenProfile)-> EdenStatsResult :
    stat_rolls : list[float]=[]
    empty=bombs=keys=coins=0 
    treasures : list[int]=[]
    trinket : int|None=None 
    stat_slot=0 
    for c in cmds :
        if c.cmd_type ==85 :
            stat_rolls.append(stat_delta_from_cmd_seed(c.rng,stat_slot))
            stat_slot+=1 
        elif c.cmd_type ==0 and c.a3 ==1 :
            empty+=1 
        elif c.cmd_type ==3 and c.a3 ==43 :
            bombs+=1 
        elif c.cmd_type ==4 and c.a3 ==4 :
            keys+=1 
        elif c.cmd_type ==5 and c.a3 ==100 :
            if c.a4 and c.a4 <400 :
                treasures.append(c.a4)
            elif c.a4 >=400 :
                trinket=c.a4 
        elif c.cmd_type ==5 and c.a3 ==70 :
            coins+=1 
    panel=eden_7bbbd0_base_panel(p988,profile)
    return EdenStatsResult(start_seed=0,a5_113620=0,p988=p988,p988_after=rng.seed,commands=cmds,stat_rolls=stat_rolls,treasure_items=treasures,trinket_item=trinket,panel_base=panel,hearts_red=panel.red1232,hearts_soul=panel.soul1235,hearts_black=0,empty_heart=empty,bombs=bombs,keys=keys,coins_pickup=coins,outer_loop_cases=outer_cases,final_layout_case=final_case)

def eden_stats_from_start_seed(start_seed : int,profile : EdenProfile|None=None)-> EdenStatsResult :
    u32=int(start_seed)&4294967295 
    a5=start_seed_to_a5(u32)
    p988=p988_from_a5(a5)
    r=simulate_6dae40_eden(p988,profile)
    r.start_seed=u32 
    r.a5_113620=a5 
    return r 

def summarize_stats(r : EdenStatsResult)-> dict :
    p=r.panel_base 
    return{'p988': r.p988,'p988_after': r.p988_after,'outer_cases': r.outer_loop_cases,'final_layout_case': r.final_layout_case,'stat_roll_count': len(r.stat_rolls),'stat_rolls_rad':[round(x,4)for x in r.stat_rolls],'red1232': p.red1232,'red_hud': p.red_hud,'soul1235': p.soul1235,'cap1233': p.cap1233,'hearts_red': p.red1232,'hearts_soul': p.soul1235,'empty_heart': r.empty_heart,'bombs': r.bombs,'keys': r.keys,'coins_pickup': r.coins_pickup,'treasure_items': r.treasure_items,'command_count': len(r.commands)}
