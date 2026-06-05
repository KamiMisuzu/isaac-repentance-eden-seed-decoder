from __future__ import annotations 
QWORD_B1F504=47244640257 
DWORD_B1F50C=16 

def shifts_from_qword_dword(qword : int,third : int)-> tuple[int,int,int]:
    return(qword&4294967295,qword>>32&4294967295,third&4294967295)

def mix_qword_dword(seed : int,qword : int,third : int)-> int :
    (s1,s2,s3)=shifts_from_qword_dword(qword,third)
    s=seed&4294967295 
    t=s^s>>s1 
    t=(t^t<<s2&4294967295)&4294967295 
    t=(t^t>>s3)&4294967295 
    return t 

def p988_from_a5(a5 : int)-> int :
    s=int(a5)&4294967295 
    for _ in range(5):
        s=mix_qword_dword(s,QWORD_B1F504,DWORD_B1F50C)
    return s 
