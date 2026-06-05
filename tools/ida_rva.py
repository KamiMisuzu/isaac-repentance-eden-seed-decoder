from __future__ import annotations 
IDA_IMAGE_BASE=4194304 

def rva_from_source(ida_va : int)-> int :
    return ida_va-IDA_IMAGE_BASE 

def runtime_from_module_base(module_base : int,ida_va : int)-> int :
    return module_base+rva_from_source(ida_va)
IDA_VA={'7EF420': 8320032,'6E17C0': 7215040,'6DAE40': 7188032,'733610': 7550480,'4218E0': 4331744,'73E0A0': 7594144,'802980': 8399232}
if __name__ == "__main__":
    base=3997696 
    print(f'module.base= 0x{base: X}, IDA_IMAGE_BASE= 0x{IDA_IMAGE_BASE: X}\n')
    for(name,va)in IDA_VA.items():
        rva=rva_from_source(va)
        print(f'sub_{name}: IDA 0x{va: X}-> RVA 0x{rva: X}-> runtime 0x{runtime_from_module_base(base, va): X}')
