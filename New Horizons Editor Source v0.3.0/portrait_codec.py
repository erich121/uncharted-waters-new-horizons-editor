"""Bounded Koei decompressor, adapted from Gilmok/UWNHRando (MIT).
See UWNHRando.LICENSE.
"""
def short(v):
    v &= 65535
    return v-65536 if v & 32768 else v

class Decoder:
    def __init__(self, rom): self.rom = rom
    def word(self, data, p): return short(data[p] | data[p+1]<<8)
    def swap(self, a): return short(((a & 255)<<8) | ((a>>8)&255))
    def shift(self, amount):
        a=short(self.bits<<amount); self.bits=a
        needed=amount
        if self.remaining<needed:
            needed-=self.remaining
            a=short((self.word_buffer & ((1<<self.remaining)-1))<<needed)
            self.bits=short(self.bits | a)
            if self.bits & -4 != 508:
                self.word_buffer=self.word(self.rom,self.cursor)
            self.cursor+=2; self.remaining=16
        self.remaining-=needed
        a=(self.word_buffer>>self.remaining)&((1<<needed)-1)
        self.bits=short(self.bits | a)
    def decode(self, offset, max_output=8192):
        rom=self.rom; self.cursor=offset+2; self.remaining=0
        self.bits=self.word_buffer=self.word(rom,offset)
        output=bytearray(); control=0; controls_left=0
        table=41711-512
        for _ in range(max(20000, max_output*2)):
            if controls_left==0:
                control=rom[self.cursor]; self.cursor+=1; controls_left=8
            literal=control & 128; control=(control<<1)&255; controls_left-=1
            if literal:
                output.append(rom[self.cursor]); self.cursor+=1
                if len(output)>max_output: raise ValueError('Decompressed block exceeds expected bounds')
                continue
            a=self.bits
            if a & 32768:
                length=1
            else:
                a=self.swap(a>>1); y=a & 255
                if y:
                    if y<8:
                        a=self.swap(a); a=short(a >> (rom[table+127+y]//2))
                    else: a=rom[table+y]
                    length=a
                    self.shift(rom[table+64+y]//2)
                    a=self.bits
                else:
                    a=self.swap(a); a=(a>>1)|128
                    if a==255: return bytes(output)
                    length=a; self.shift(rom[table+64]//2); a=self.bits
            a=short(a<<1)
            if 0<=a<24576:
                a=self.swap(short(a<<1)); y=a & 255
                dist=rom[table+135+y]
                shift_amount=rom[table+327+(y>>4)]//2
            else:
                carry=1 if a<0 else 0
                a=short(a<<1)
                for i in range(3):
                    next_carry=1 if a & 32768 else 0
                    a=short((a<<1)|carry); carry=next_carry
                y=a & 7
                dist=((self.bits & 4095)|4096)>>(rom[table+336+y]//2)
                shift_amount=rom[table+341+y]//2
            self.shift(shift_amount)
            start=len(output)-dist-1
            if start<0: raise ValueError(f'Invalid back-reference at ROM {offset:x}, output {len(output)}')
            for i in range(length+1): output.append(output[start+i])
            if len(output)>max_output: raise ValueError('Decompressed block exceeds expected bounds')
        raise ValueError('Missing compression terminator')
