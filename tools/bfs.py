#!/usr/bin/env python3
"""Minimal read-only BFS (BeOS filesystem) reader: list tree, extract files.
usage: bfsls.py IMAGE [ls|cat PATH|extract OUTDIR [substr]]"""
import struct, sys, os

class BFS:
    def __init__(self, path, base=0):
        self.f = open(path, 'rb'); self.base = base
        sb = self.rd(512, 512)
        (self.magic1, self.endian, self.bs, self.bshift) = struct.unpack_from('<IIII', sb, 0x20)
        assert self.magic1 == 0x42465331, hex(self.magic1)
        self.nblocks, self.used = struct.unpack_from('<qq', sb, 0x30)
        self.inode_size, _m2, self.bpag, self.agshift, self.nag = struct.unpack_from('<IIIII', sb, 0x40)
        self.root = struct.unpack_from('<IHH', sb, 0x74)
        self.name = sb[:32].split(b'\0')[0].decode('latin1')

    def rd(self, off, n):
        self.f.seek(self.base + off); return self.f.read(n)

    def blk(self, run):
        ag, st, ln = run
        return (ag << self.agshift) | st

    def inode(self, blockno):
        d = self.rd(blockno * self.bs, self.inode_size)
        assert struct.unpack_from('<I', d, 0)[0] == 0x3bbe0ad9, (blockno, d[:4].hex())
        mode, flags = struct.unpack_from('<ii', d, 20)
        ds = 72
        direct = [struct.unpack_from('<IHH', d, ds + 8 * i) for i in range(12)]
        (maxd,) = struct.unpack_from('<q', d, ds + 96)
        ind = struct.unpack_from('<IHH', d, ds + 104)
        (maxi,) = struct.unpack_from('<q', d, ds + 112)
        dind = struct.unpack_from('<IHH', d, ds + 120)
        (maxdi,) = struct.unpack_from('<q', d, ds + 128)
        (size,) = struct.unpack_from('<q', d, ds + 136)
        return dict(mode=mode, flags=flags, direct=direct, ind=ind, dind=dind, size=size)

    def runs(self, ino):
        out = [r for r in ino['direct'] if r[2]]
        if ino['ind'][2]:
            b = self.rd(self.blk(ino['ind']) * self.bs, ino['ind'][2] * self.bs)
            for i in range(len(b) // 8):
                r = struct.unpack_from('<IHH', b, i * 8)
                if r[2]: out.append(r)
        if ino['dind'][2]:
            b = self.rd(self.blk(ino['dind']) * self.bs, ino['dind'][2] * self.bs)
            for i in range(len(b) // 8):
                ir = struct.unpack_from('<IHH', b, i * 8)
                if not ir[2]: continue
                bb = self.rd(self.blk(ir) * self.bs, ir[2] * self.bs)
                for j in range(len(bb) // 8):
                    r = struct.unpack_from('<IHH', bb, j * 8)
                    if r[2]: out.append(r)
        return out

    def data(self, ino, limit=None):
        n = ino['size'] if limit is None else min(limit, ino['size'])
        buf = bytearray()
        for r in self.runs(ino):
            if len(buf) >= n: break
            buf += self.rd(self.blk(r) * self.bs, r[2] * self.bs)
        return bytes(buf[:n])

    def entries(self, ino):
        t = self.data(ino)
        magic, nsz, levels, dtype, root, free, maxsz = struct.unpack_from('<IiIIqqq', t, 0)
        assert magic == 0x69f6c2e8, hex(magic)
        res = []
        pos = nsz
        while pos + nsz <= len(t):
            node = t[pos:pos + nsz]
            left, right, ovf, cnt, klen = struct.unpack_from('<qqqHH', node, 0)
            if ovf == -1 and cnt:
                keys = 28
                lo = (keys + klen + 7) & ~7
                ends = struct.unpack_from('<%dH' % cnt, node, lo)
                vo = lo + 2 * cnt
                vals = struct.unpack_from('<%dq' % cnt, node, vo)
                prev = 0
                for e, v in zip(ends, vals):
                    res.append((node[keys + prev:keys + e].decode('latin1'), v)); prev = e
            pos += nsz
        return res

    def walk(self, ino, prefix=''):
        for name, v in self.entries(ino):
            if name in ('.', '..'):
                continue
            try:
                i = self.inode(v)
            except AssertionError:
                continue
            isdir = (i['mode'] & 0o170000) == 0o040000
            yield prefix + name, i, isdir
            if isdir:
                yield from self.walk(i, prefix + name + '/')

if __name__ == '__main__':
    fs = BFS(sys.argv[1])
    root = fs.inode(fs.blk(fs.root))
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'ls'
    if cmd == 'ls':
        print('volume', fs.name, 'bs', fs.bs, 'blocks', fs.nblocks)
        for p, i, d in fs.walk(root):
            print('%10d %s%s' % (i['size'], p, '/' if d else ''))
    elif cmd == 'extract':
        out = sys.argv[3]; sub = sys.argv[4] if len(sys.argv) > 4 else ''
        for p, i, d in fs.walk(root):
            if sub not in p: continue
            dst = os.path.join(out, p)
            if d: os.makedirs(dst, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(fs.data(i))
