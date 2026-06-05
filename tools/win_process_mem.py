from __future__ import annotations 
import ctypes 
import struct 
from ctypes import wintypes 
from dataclasses import dataclass 
from typing import Iterator 
kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
PROCESS_QUERY_INFORMATION=1024 
PROCESS_VM_READ=16 
TH32CS_SNAPPROCESS=2 
TH32CS_SNAPMODULE=8 
TH32CS_SNAPMODULE32=16 
INVALID_HANDLE_VALUE=ctypes.c_void_p(-1).value 
MEM_COMMIT=4096 
PAGE_NOACCESS=1 
PAGE_GUARD=256 
READABLE={2,4,6,32,64,128}

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),('AllocationProtect',wintypes.DWORD),('RegionSize',ctypes.c_size_t),('State',wintypes.DWORD),('Protect',wintypes.DWORD),('Type',wintypes.DWORD)]

class PROCESSENTRY32(ctypes.Structure):
    _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.POINTER(ctypes.c_ulong)),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),('szExeFile',wintypes.CHAR*260)]

class MODULEENTRY32(ctypes.Structure):
    _fields_=[('dwSize',wintypes.DWORD),('th32ModuleID',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),('GlblcntUsage',wintypes.DWORD),('ProccntUsage',wintypes.DWORD),('modBaseAddr',ctypes.POINTER(ctypes.c_byte)),('modBaseSize',wintypes.DWORD),('hModule',wintypes.HMODULE),('szModule',wintypes.CHAR*256),('szExePath',wintypes.CHAR*260)]

@dataclass 
class MemoryRegion :
    base : int 
    size : int 
    protect : int 
    mtype : int 

@dataclass 
class ProcessMem :
    pid : int 
    name : str 
    handle : int 
    ptr_size : int 
    ptr_mask : int 
    is_64 : bool 

    def read(self,address : int,size : int)-> bytes|None :
        buf=ctypes.create_string_buffer(size)
        n=ctypes.c_size_t(0)
        ok=kernel32.ReadProcessMemory(self.handle,ctypes.c_void_p(address),buf,size,ctypes.byref(n))
        if not ok or n.value ==0 :
            return None 
        return buf.raw[: n.value]

    def read_u32(self,address : int)-> int|None :
        b=self.read(address,4)
        if not b or len(b)<4 :
            return None 
        return struct.unpack('<I',b)[0]

    def read_ptr(self,address : int)-> int|None :
        b=self.read(address,self.ptr_size)
        if not b or len(b)<self.ptr_size :
            return None 
        if self.ptr_size ==8 :
            return struct.unpack('<Q',b)[0]
        return struct.unpack('<I',b)[0]

    def close(self)-> None :
        if self.handle :
            kernel32.CloseHandle(self.handle)
            self.handle=0 

def _raise_last_winerr(msg : str)-> OSError :
    err=ctypes.get_last_error()
    raise OSError(err,msg)

def find_pid(exe_name : str='isaac-ng.exe')-> int :
    snap=kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0)
    if snap ==INVALID_HANDLE_VALUE :
        _raise_last_winerr('CreateToolhelp32Snapshot')
    pe=PROCESSENTRY32()
    pe.dwSize=ctypes.sizeof(PROCESSENTRY32)
    target=exe_name.lower()
    pid=0 
    try :
        if not kernel32.Process32First(snap,ctypes.byref(pe)):
            _raise_last_winerr('Process32First')
        while True :
            name=pe.szExeFile.decode('ascii',errors='ignore').lower()
            if name ==target or name.endswith('\\'+target):
                pid=pe.th32ProcessID 
                break 
            if not kernel32.Process32Next(snap,ctypes.byref(pe)):
                break 
    finally :
        kernel32.CloseHandle(snap)
    if not pid :
        raise ProcessLookupError(f'{exe_name} not running')
    return pid 

def module_base(pid : int,module_name : str='isaac-ng.exe')-> tuple[int,int]:
    flags=TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32 
    snap=kernel32.CreateToolhelp32Snapshot(flags,pid)
    if snap ==INVALID_HANDLE_VALUE :
        _raise_last_winerr('CreateToolhelp32Snapshot(module)')
    me=MODULEENTRY32()
    me.dwSize=ctypes.sizeof(MODULEENTRY32)
    base=0 
    size=0 
    target=module_name.lower()
    try :
        if not kernel32.Module32First(snap,ctypes.byref(me)):
            _raise_last_winerr('Module32First')
        while True :
            mod=me.szModule.decode('ascii',errors='ignore').lower()
            if mod ==target :
                base=ctypes.cast(me.modBaseAddr,ctypes.c_void_p).value or 0 
                size=me.modBaseSize 
                break 
            if not kernel32.Module32Next(snap,ctypes.byref(me)):
                break 
    finally :
        kernel32.CloseHandle(snap)
    if not base :
        raise LookupError(f'module{module_name} not found in pid{pid}')
    return(base,size)

def pe_pointer_size(module_base_addr : int,pm : ProcessMem)-> int :
    hdr=pm.read(module_base_addr,512)
    if not hdr or len(hdr)<64 :
        return 4 
    e_lfanew=struct.unpack_from('<I',hdr,60)[0]
    if e_lfanew+6 >=len(hdr):
        return 4 
    machine=struct.unpack_from('<H',hdr,e_lfanew+4)[0]
    return 8 if machine ==34404 else 4 

def open_process(exe_name : str='isaac-ng.exe',pid : int|None=None)-> ProcessMem :
    pid=pid or find_pid(exe_name)
    h=kernel32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,False,pid)
    if not h :
        _raise_last_winerr(f'OpenProcess pid={pid}')
    (base,_)=module_base(pid,exe_name)
    pm=ProcessMem(pid=pid,name=exe_name,handle=h,ptr_size=4,ptr_mask=4294967295,is_64=False)
    ps=pe_pointer_size(base,pm)
    pm.ptr_size=ps 
    pm.ptr_mask=(1<<64)-1 if ps ==8 else 4294967295 
    pm.is_64=ps ==8 
    return pm 

def iter_regions(pm : ProcessMem)-> Iterator[MemoryRegion]:
    addr=0 
    mbi=MEMORY_BASIC_INFORMATION()
    max_addr=1<<64 if pm.is_64 else 1<<32 
    while addr <max_addr :
        ret=kernel32.VirtualQueryEx(pm.handle,ctypes.c_void_p(addr),ctypes.byref(mbi),ctypes.sizeof(mbi))
        if ret ==0 :
            break 
        base=mbi.BaseAddress or 0 
        size=mbi.RegionSize or 0 
        if size ==0 :
            break 
        if mbi.State ==MEM_COMMIT and mbi.Protect not in(PAGE_NOACCESS,PAGE_GUARD)and(mbi.Protect&255 in READABLE)and(size >=4096):
            yield MemoryRegion(base=base,size=size,protect=mbi.Protect,mtype=mbi.Type)
        nxt=base+size 
        if nxt <=addr :
            break 
        addr=nxt 

def is_heap_ptr(v : int,pm : ProcessMem)-> bool :
    if v ==0 :
        return False 
    if pm.ptr_size ==4 :
        return 65536 <=v <=2147352576 
    return 65536 <=v <=140737488355327 

def read_cstring(pm : ProcessMem,addr : int,limit : int=260)-> str :
    b=pm.read(addr,limit)
    if not b :
        return ''
    z=b.find(b'\x00')
    if z >=0 :
        b=b[: z]
    return b.decode('ascii',errors='replace')
