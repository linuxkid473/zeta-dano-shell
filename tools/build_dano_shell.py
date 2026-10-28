#!/usr/bin/env python3
"""Build the "Dano shell" folder for ZETA 1.2.1 from YOUR copy of the BeOS R5.1 "Dano" CD.

    python3 tools/build_dano_shell.py Dano_x86.cue OUTDIR
    python3 tools/build_dano_shell.py --bfs data-track.img OUTDIR     (already-extracted raw BFS data track)

It reads Tracker, Deskbar and libbe.so out of the CD image (a read-only BFS reader, tools/bfs.py), applies three
small byte patches, and writes OUTDIR/DanoShell/ ready to copy to /boot/home/DanoShell on ZETA. No Be binaries
are shipped with this project, which is why you have to supply the CD image.

Patches (see docs/HOW-IT-WORKS.md):
  Deskbar  symbol TrackerInitIconPreloader -> InitIconPreloader   (name ZETA's libtracker uses)
  Tracker  "About BeOS": run_be_about() is an empty stub in ZETA's libbe, so the call site runs system("/bin/A &")
"""
import argparse
import hashlib
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bfs  # noqa: E402

# md5 of the files on the Dano CD that the patches were written for, and of the results
WANT = {
    'Deskbar': 'd65edf7bf61960e880652e8b764279a7',
    'Tracker': 'a4e1e5d7aeab95a67d3fad39a6a26a0a',
    'libbe.so': 'fedc4bd99f709c1c5ada019016fd17c7',
}
RESULT = {
    'Deskbar': '12ac205650bb811962a73550d9fbd057',
    'Tracker': '9827b5c80ee0db87a12daa9d96d66543',
}


def md5(b):
    return hashlib.md5(b).hexdigest()


class CookedBFS(bfs.BFS):
    """BFS reader over a MODE1/2352 raw CD track: logical byte offsets skip the 16-byte header of every sector."""

    def __init__(self, path, base):
        self.f = open(path, 'rb')
        self.raw_base = base
        self.base = 0
        self._init_sb()

    def _init_sb(self):
        sb = self.rd(512, 512)
        (self.magic1, self.endian, self.bs, self.bshift) = struct.unpack_from('<IIII', sb, 0x20)
        assert self.magic1 == 0x42465331, 'not a BFS volume (magic %x)' % self.magic1
        self.nblocks, self.used = struct.unpack_from('<qq', sb, 0x30)
        self.inode_size, _m2, self.bpag, self.agshift, self.nag = struct.unpack_from('<IIIII', sb, 0x40)
        self.root = struct.unpack_from('<IHH', sb, 0x74)
        self.name = sb[:32].split(b'\0')[0].decode('latin1')

    def rd(self, off, n):
        out = bytearray()
        while n > 0:
            sec, o = divmod(off, 2048)
            self.f.seek(self.raw_base + sec * 2352 + 16 + o)
            take = min(n, 2048 - o)
            out += self.f.read(take)
            off += take
            n -= take
        return bytes(out)


def open_image(args):
    if args.bfs:
        return bfs.BFS(args.image)
    path = args.image
    if path.lower().endswith('.cue'):
        text = open(path, errors='replace').read()
        binf = re.search(r'FILE\s+"([^"]+)"', text).group(1)
        idx = re.findall(r'TRACK\s+(\d+)\s+(\S+).*?INDEX\s+01\s+(\d+):(\d+):(\d+)', text, re.S)
        data = [t for t in idx if t[1].startswith('MODE1')]
        t2 = idx[1] if len(idx) > 1 else idx[0]
        mm, ss, ff = int(t2[2]), int(t2[3]), int(t2[4])
        sector = (mm * 60 + ss) * 75 + ff
        binpath = os.path.join(os.path.dirname(path), binf)
        return CookedBFS(binpath, sector * 2352)
    sys.exit('give the .cue file of the Dano CD (or --bfs with a raw BFS image)')


def find(fs, want):
    root = fs.inode(fs.blk(fs.root))
    for p, ino, isdir in fs.walk(root):
        if p == want:
            return fs.data(ino)
    sys.exit('not found on the CD: ' + want)


def patch_deskbar(d):
    d = bytearray(d)
    old = b'TrackerInitIconPreloader__8BPrivatev\0'
    new = b'InitIconPreloader__8BPrivatev\0'
    n = d.count(old)
    assert n == 2, n
    return bytes(d.replace(old, new + b'\0' * (len(old) - len(new))))


def patch_tracker(d):
    d = bytearray(d)
    n0 = len(d)
    # 1. the dynstr slot of the imported symbol run_be_about__Fv becomes "system" plus a command string
    slot = [m.start() for m in re.finditer(rb'run_be_about__Fv\0', d)][0]
    new = b'system\0' + b'/bin/A &\0'
    d[slot:slot + 17] = new + b'\0' * (17 - len(new))
    cmd = slot + 7
    # 2. the "Spls" case of TTracker::MessageReceived: call plt(run_be_about) -> push cmd; call plt(system)
    got = 0x12856e + 0x90386           # ebx inside MessageReceived (PIC base)
    site, plt, tramp, tail = 0x128761, 0x88ec4, 0x12877a, 0x128880
    assert d[site:site + 5] == bytes.fromhex('e85e07f6ff')
    code = bytearray()
    code += b'\x8d\x83' + struct.pack('<I', (cmd - got) & 0xffffffff)          # lea cmd(%ebx),%eax
    code += b'\x50'                                                             # push %eax
    code += b'\xe8' + struct.pack('<i', plt - (site + len(code) + 5))           # call plt (now "system")
    code += b'\xeb' + struct.pack('<b', tramp - (site + len(code) + 2))         # jmp short to the padding below
    assert len(code) <= 15
    d[site:site + len(code)] = code
    assert d[tramp:tramp + 6] == bytes.fromhex('8db600000000')                  # unreachable padding
    d[tramp:tramp + 5] = b'\xe9' + struct.pack('<i', tail - (tramp + 5))        # jmp to the function epilogue
    assert len(d) == n0
    return bytes(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('out')
    ap.add_argument('--bfs', action='store_true', help='IMAGE is a raw BFS image, not a .cue')
    ap.add_argument('--force', action='store_true', help='continue even if the CD files are not the expected ones')
    args = ap.parse_args()

    fs = open_image(args)
    print('volume:', fs.name)
    src = {
        'Deskbar': find(fs, 'beos/system/Deskbar'),
        'Tracker': find(fs, 'beos/system/Tracker'),
        'libbe.so': find(fs, 'beos/system/lib/libbe.so'),
    }
    for k, v in src.items():
        ok = md5(v) == WANT[k]
        print('%-9s %8d bytes  md5 %s  %s' % (k, len(v), md5(v), 'ok' if ok else 'UNEXPECTED'))
        if not ok and not args.force:
            sys.exit('This is not the BeOS R5.1 "Dano" CD the patches were written for (use --force to try anyway).')

    deskbar = patch_deskbar(src['Deskbar'])
    tracker = patch_tracker(src['Tracker'])
    for k, v in (('Deskbar', deskbar), ('Tracker', tracker)):
        ok = md5(v) == RESULT[k]
        print('patched %-8s md5 %s  %s' % (k, md5(v), 'ok' if ok else 'differs from the tested build'))

    out = os.path.join(args.out, 'DanoShell')
    for sub in ('dano', 'about/lib'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    open(os.path.join(out, 'dano/Deskbar'), 'wb').write(deskbar)
    open(os.path.join(out, 'dano/Tracker'), 'wb').write(tracker)
    open(os.path.join(out, 'about/lib/libbe.so'), 'wb').write(src['libbe.so'])
    zeta = os.path.join(os.path.dirname(HERE), 'zeta')
    for f in os.listdir(zeta):
        p = os.path.join(zeta, f)
        if os.path.isdir(p):
            shutil.copytree(p, os.path.join(out, f), dirs_exist_ok=True)
        else:
            shutil.copy(p, out)
    print('\nWrote', out)
    print('Copy that folder to /boot/home/DanoShell on the ZETA machine, then run:  sh /boot/home/DanoShell/install.sh')


if __name__ == '__main__':
    main()
