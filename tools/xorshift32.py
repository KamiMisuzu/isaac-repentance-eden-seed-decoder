def _undo_xor_shr(y : int,shift : int)-> int :
    x=y&4294967295 
    for _ in range(32):
        x=(y^x>>shift)&4294967295 
    return x 

def _undo_xor_shl(y : int,shift : int)-> int :
    x=y&4294967295 
    for i in range(32):
        bit=y>>i&1 
        if i >=shift :
            bit^=x>>i-shift&1 
        x=x&~(1<<i)|bit<<i 
    return x&4294967295 

def invert_mix(seed_out : int,shr : int,shl : int,fin : int)-> int :
    s2=_undo_xor_shr(seed_out,fin)
    s1=_undo_xor_shl(s2,shl)
    return _undo_xor_shr(s1,shr)

def forward_mix(s : int,shr : int,shl : int,fin : int)-> int :
    s&=4294967295 
    t=s^s>>shr 
    t=(t^t<<shl&4294967295)&4294967295 
    return(t^t>>fin)&4294967295 
