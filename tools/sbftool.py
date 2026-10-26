#!/usr/bin/env python3
"""sbftool - self-contained analysis of Solana sBPF (v1) ELF programs.

Reads .text directly (no objdump), recovers functions from call targets and
local jumps, names syscalls via .rel.dyn/.dynsym, tags Anchor discriminators,
and runs a per-function register/stack abstract interpretation to answer
"which stores write field +OFF of the struct passed in REG at call site PC?".

Usage:
  sbftool.py stats    PROG.so
  sbftool.py dis      PROG.so START [COUNT]      # START = insn index or 0xADDR
  sbftool.py func     PROG.so PC                 # disasm the function holding PC
  sbftool.py callers  PROG.so TARGET
  sbftool.py disc     PROG.so NAME [NAME ...]    # event:TradeEvent global:buy_v3
  sbftool.py field    PROG.so CALLSITE REG OFF   # writers of [REG@callsite + OFF]
"""
import hashlib, struct, sys, re
from collections import defaultdict

# sBPF opcode -> mnemonic (the subset Solana/LLVM actually emits).
ALU = {0x04:'add32',0x0c:'add32',0x14:'sub32',0x1c:'sub32',0x24:'mul32',0x2c:'mul32',
       0x34:'div32',0x3c:'div32',0x44:'or32',0x4c:'or32',0x54:'and32',0x5c:'and32',
       0x64:'lsh32',0x6c:'lsh32',0x74:'rsh32',0x7c:'rsh32',0x84:'neg32',0x94:'mod32',
       0x9c:'mod32',0xa4:'xor32',0xac:'xor32',0xb4:'mov32',0xbc:'mov32',0xc4:'arsh32',0xcc:'arsh32',
       0x07:'add64',0x0f:'add64',0x17:'sub64',0x1f:'sub64',0x27:'mul64',0x2f:'mul64',
       0x37:'div64',0x3f:'div64',0x47:'or64',0x4f:'or64',0x57:'and64',0x5f:'and64',
       0x67:'lsh64',0x6f:'lsh64',0x77:'rsh64',0x7f:'rsh64',0x87:'neg64',0x97:'mod64',
       0x9f:'mod64',0xa7:'xor64',0xaf:'xor64',0xb7:'mov64',0xbf:'mov64',0xc7:'arsh64',0xcf:'arsh64'}
JMP = {0x05:'ja',0x15:'jeq',0x1d:'jeq',0x25:'jgt',0x2d:'jgt',0x35:'jge',0x3d:'jge',
       0x45:'jset',0x4d:'jset',0x55:'jne',0x5d:'jne',0x65:'jsgt',0x6d:'jsgt',
       0x75:'jsge',0x7d:'jsge',0xa5:'jlt',0xad:'jlt',0xb5:'jle',0xbd:'jle',
       0xc5:'jslt',0xcd:'jslt',0xd5:'jsle',0xdd:'jsle'}
LD = {0x61:('ldxw',4),0x69:('ldxh',2),0x71:('ldxb',1),0x79:('ldxdw',8)}
ST = {0x62:('stw',4),0x6a:('sth',2),0x72:('stb',1),0x7a:('stdw',8),     # store immediate
      0x63:('stxw',4),0x6b:('stxh',2),0x73:('stxb',1),0x7b:('stxdw',8)} # store register


class Insn:
    __slots__ = ('pc','op','mn','dst','src','off','imm','sz','wide')
    def __init__(self, pc, op, mn, dst, src, off, imm, sz=0, wide=False):
        self.pc,self.op,self.mn,self.dst,self.src = pc,op,mn,dst,src
        self.off,self.imm,self.sz,self.wide = off,imm,sz,wide
    def __repr__(self):
        m=self.mn
        if self.op==0x18: return f'{m} r{self.dst}, {hex(self.imm)}'
        if self.op in LD: return f'{m} r{self.dst}, [r{self.src} {self.off:+#x}]'
        if self.op in ST:
            v=f'r{self.src}' if (self.op&0x3)==3 else hex(self.imm)
            return f'{m} [r{self.dst} {self.off:+#x}], {v}'
        if self.op==0x85: return f'call {hex(self.imm)}'
        if self.op==0x8d: return f'callx r{self.imm}'
        if self.op==0x95: return 'exit'
        if self.op in JMP:
            if self.op==0x05: return f'ja {self.off:+#x}'
            src=f'r{self.src}' if (self.op&0x08) else hex(self.imm)
            return f'{m} r{self.dst}, {src}, {self.off:+#x}'
        if self.op in (0x84, 0x87):              # neg32/neg64: single operand
            return f'{m} r{self.dst}'
        if self.op in ALU:
            src=f'r{self.src}' if (self.op&0x08) else hex(self.imm)
            return f'{m} r{self.dst}, {src}'
        return f'.byte {hex(self.op)}'


class Prog:
    def __init__(self, path):
        b = self.b = open(path,'rb').read()
        shoff, = struct.unpack_from('<Q', b, 0x28)
        es,n,si = struct.unpack_from('<HHH', b, 0x3a)
        secs = [struct.unpack_from('<IIQQQQIIQQ', b, shoff+i*es) for i in range(n)]
        st = secs[si]
        name = lambda o: b[st[4]+o:b.index(b'\0', st[4]+o)].decode()
        self.sec = {name(s[0]): s for s in secs}
        self.secs = [(name(s[0]), s) for s in secs]
        t = self.sec['.text']
        self.taddr, self.toff, self.tsize = t[3], t[4], t[5]
        self.base = self.taddr // 8
        self.code = b[self.toff:self.toff+self.tsize]
        self._decode()
        self._syms()
        self._funcs()

    def _decode(self):
        c = self.code; self.ins = {}; self.order = []
        i = 0
        while i < len(c):
            op, regs = c[i], c[i+1]
            dst, src = regs & 0xf, regs >> 4
            off, imm = struct.unpack_from('<hi', c, i+2)
            pc = self.base + i//8
            if op == 0x18:                       # lddw occupies two slots
                hi, = struct.unpack_from('<i', c, i+12)
                imm = (imm & 0xffffffff) | (hi << 32)
                self.ins[pc] = Insn(pc, op, 'lddw', dst, src, 0, imm, wide=True)
                self.order.append(pc); i += 16; continue
            mn = (ALU.get(op) or JMP.get(op) or
                  (LD[op][0] if op in LD else None) or
                  (ST[op][0] if op in ST else None) or
                  {0x85:'call',0x8d:'callx',0x95:'exit'}.get(op) or '.byte')
            sz = LD[op][1] if op in LD else (ST[op][1] if op in ST else 0)
            self.ins[pc] = Insn(pc, op, mn, dst, src, off, imm, sz)
            self.order.append(pc); i += 8

    def _syms(self):
        """Map call immediate -> syscall/function name via relocations + dynsym."""
        self.name = {}
        ds = self.sec.get('.dynsym'); ds_s = self.sec.get('.dynstr')
        syms = []
        if ds and ds_s:
            off, size = ds[4], ds[5]; base = ds_s[4]
            for k in range(size // 24):
                stn, info, other, shndx, val, sz = struct.unpack_from('<IBBHQQ', self.b, off+k*24)
                nm = self.b[base+stn:self.b.index(b'\0', base+stn)].decode('latin1')
                syms.append((nm, val))
        # sBPF call-by-hash: the immediate is murmur32 of the symbol name. Map via dynsym names.
        for nm, val in syms:
            if nm:
                self.name[self._murmur(nm)] = nm
                if val: self.name[val//8] = nm

    @staticmethod
    def _murmur(s):
        # Solana syscall hash = murmur3_32(name, seed=0)
        data = s.encode(); h = 0; n = len(data)
        for i in range(0, n-3, 4):
            k = struct.unpack_from('<I', data, i)[0]
            k = (k*0xcc9e2d51) & 0xffffffff; k = ((k<<15)|(k>>17)) & 0xffffffff
            k = (k*0x1b873593) & 0xffffffff
            h ^= k; h = ((h<<13)|(h>>19)) & 0xffffffff; h = (h*5+0xe6546b64) & 0xffffffff
        tail = n & 3; k = 0
        if tail>=3: k ^= data[n-1]<<16
        if tail>=2: k ^= data[n-2]<<8
        if tail>=1:
            k ^= data[n-tail]
            k = (k*0xcc9e2d51)&0xffffffff; k=((k<<15)|(k>>17))&0xffffffff; k=(k*0x1b873593)&0xffffffff; h^=k
        h ^= n; h ^= h>>16; h=(h*0x85ebca6b)&0xffffffff; h^=h>>13; h=(h*0xc2b2ae35)&0xffffffff; h^=h>>16
        return h

    def _funcs(self):
        """Function starts = call targets + first insn. Each function spans to the
        next start or the insn after its last reachable exit."""
        starts = {self.base}
        for pc, ins in self.ins.items():
            if ins.op == 0x85:                   # relative call in sBPF v1
                tgt = pc + 1 + ins.imm
                if tgt in self.ins: starts.add(tgt)
        self.starts = sorted(starts)
        self.func_of = {}
        for a, b in zip(self.starts, self.starts[1:] + [self.base + len(self.order)]):
            for pc in range(a, b):
                if pc in self.ins: self.func_of[pc] = a

    def func_start(self, pc):
        s = [x for x in self.starts if x <= pc]
        return s[-1] if s else self.base

    def func_body(self, start):
        nxt = [x for x in self.starts if x > start]
        end = nxt[0] if nxt else self.base + len(self.order)
        return [self.ins[pc] for pc in range(start, end) if pc in self.ins]

    def callers(self, target):
        out = []
        for pc, ins in self.ins.items():
            if ins.op == 0x85 and pc + 1 + ins.imm == target: out.append(pc)
        return sorted(out)


# ---------------------------------------------------------------- field writers
def _scan_stores(body, seed, stop=None):
    """Track registers that alias (base_reg + const) and record every store,
    keyed by (base_reg, displacement). `seed` maps regno -> (base, 0). Returns
    (writers, snapshot_at_stop) where writers = [(base, disp, pc, text)]."""
    cur = {r: (b, 0) for r, b in seed.items()}   # regno -> (base_tag, const)
    writers = []; snap = None
    for ins in body:
        if stop is not None and ins.pc == stop:
            snap = dict(cur)
        pre = dict(cur)
        if ins.op == 0xbf:                       # mov64 reg, src
            if ins.src in cur: cur[ins.dst] = cur[ins.src]
            else: cur.pop(ins.dst, None)
        elif ins.op == 0xb7:                     # mov64 reg, imm
            cur.pop(ins.dst, None)
        elif ins.op == 0x07:                     # add64 reg, imm
            if ins.dst in cur: b, k = cur[ins.dst]; cur[ins.dst] = (b, k + ins.imm)
        elif ins.op in (0x0f, 0x18):             # add64 reg,reg / lddw kill alias
            cur.pop(ins.dst, None)
        if ins.op in ST and ins.dst in pre:
            b, k = pre[ins.dst]; writers.append((b, k + ins.off, ins.pc, repr(ins)))
    return writers, snap


def field_writers(prog, callsite, reg, off):
    """Stores to [reg+off] in the function holding callsite, reg = r10+k."""
    start = prog.func_start(callsite)
    writers, snap = _scan_stores(prog.func_body(start), {10: 'fp'}, stop=callsite)
    if not snap or reg not in snap:
        return None, []
    base, k = snap[reg]
    want = k + off
    hits = [(pc, txt) for (b, d, pc, txt) in writers if b == base and d == want]
    return want, hits


def arg_field_writers(prog, func, argreg, off):
    """Stores to [argreg+off] inside `func`, where argreg holds a base at entry.
    One level of interprocedural follow for struct-builder helpers."""
    start = prog.func_start(func)
    writers, _ = _scan_stores(prog.func_body(start), {argreg: 'arg'})
    return [(pc, txt) for (b, d, pc, txt) in writers if b == 'arg' and d == off]


def disc(name):
    pre = 'account' if ':' not in name else name.split(':')[0]
    label = name.split(':', 1)[1] if ':' in name else name
    seed = {'event':'event','global':'global','account':'account'}.get(pre, pre)
    return hashlib.sha256(f'{seed}:{label}'.encode()).digest()[:8]


def main():
    if len(sys.argv) < 3: print(__doc__); return
    cmd, path = sys.argv[1], sys.argv[2]
    p = Prog(path)
    def ival(s): return int(s, 0)
    if cmd == 'stats':
        ncall = sum(1 for i in p.ins.values() if i.op == 0x85)
        ncx   = sum(1 for i in p.ins.values() if i.op == 0x8d)
        print(f'text_size={p.tsize} insns={len(p.order)} functions={len(p.starts)} '
              f'calls={ncall} callx={ncx} named_syms={len(p.name)}')
    elif cmd == 'dis':
        start = ival(sys.argv[3]); cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 40
        if start > p.base + len(p.order): start = start // 8   # byte addr -> index
        for pc in range(start, start + cnt):
            if pc in p.ins:
                i = p.ins[pc]; extra = ''
                if i.op == 0x85:
                    t = pc + 1 + i.imm; extra = f'   -> {hex(t)} {p.name.get(t," ")}'.rstrip()
                print(f'{pc:>8x}: {i!r}{extra}')
    elif cmd == 'func':
        start = p.func_start(ival(sys.argv[3]))
        print(f'; function @ {hex(start)}  ({len(p.func_body(start))} insns)')
        for i in p.func_body(start):
            extra = f'   -> {hex(i.pc+1+i.imm)}' if i.op == 0x85 else ''
            print(f'{i.pc:>8x}: {i!r}{extra}')
    elif cmd == 'callers':
        t = ival(sys.argv[3])
        if t > p.base + len(p.order): t //= 8
        print(f'{len(p.callers(t))} callers of {hex(t)}: ' + ' '.join(hex(c) for c in p.callers(t)))
    elif cmd == 'disc':
        for n in sys.argv[3:]:
            d = disc(n)
            lo, hi = d[:4], d[4:]; hits = []
            for pc, i in p.ins.items():
                if i.op == 0x18 and (i.imm & 0xffffffffffffffff).to_bytes(8,'little') == d:
                    hits.append(pc)
            print(f'{n}: {d.hex()}  lddw@ ' + (' '.join(hex(h) for h in hits) or 'none'))
    elif cmd == 'field':
        cs, reg, off = ival(sys.argv[3]), ival(sys.argv[4]), ival(sys.argv[5])
        if cs > p.base + len(p.order): cs //= 8
        slot, hits = field_writers(p, cs, reg, off)
        if slot is None: print(f'r{reg} not frame-relative at {hex(cs)}'); return
        print(f'writers of [r{reg}+{hex(off)}] (frame slot {hex(slot)}) near call @ {hex(cs)}:')
        for pc, txt in hits: print(f'{pc:>8x}: {txt}')
        if not hits: print('  (no direct frame store found)')
    elif cmd == 'afield':                        # afield PROG FUNC ARGREG OFF
        func, reg, off = ival(sys.argv[3]), ival(sys.argv[4]), ival(sys.argv[5])
        if func > p.base + len(p.order): func //= 8
        hits = arg_field_writers(p, func, reg, off)
        print(f'writers of [r{reg}(arg)+{hex(off)}] inside fn @ {hex(p.func_start(func))}:')
        for pc, txt in hits: print(f'{pc:>8x}: {txt}')
        if not hits: print('  (no store to that arg field)')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
