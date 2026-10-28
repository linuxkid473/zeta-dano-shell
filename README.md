# zeta-dano-shell

Run the **BeOS R5.1 "Dano" Tracker, Deskbar and About box on ZETA 1.2.1**, and flip between the two with two desktop icons:
**BeOS Mode** and **ZETA Mode**.

ZETA is built from the Dano code base, so Dano's own Tracker and Deskbar load happily against ZETA's `libbe`.
Three small patches make the classic parts (Be menu, "About BeOS") work, and a pair of switcher programs
swap the files in `/boot/beos/system` and restart the desktop shell. Everything is reversible.

Tested on one machine: Dell Inspiron 510m, ZETA 1.2.1 (magnussoft), Dano CD "Exp Nov-15-01".

## What you get in BeOS Mode

- the classic Be-logo **Deskbar** (top right), with the Be menu filled from your `~/config/be` (= ZETA's `ZetaMenu`)
- the Dano **Tracker** (desktop icons, windows, add-ons that don't depend on ZETA's Tracker)
- **About BeOS...** opens Dano's own About box (it lives inside Dano's `libbe.so`, which is loaded privately, only by that one program)

ZETA's own libraries are never replaced. Only three files in `/boot/beos/system` change: `Tracker`, `Deskbar`, `About`.

## Why you must bring your own CD

The Dano programs are Be's files and are **not included** here. You need an image of the BeOS R5.1 "Dano" install CD
(`.cue` + `.bin`). `tools/build_dano_shell.py` reads the three files it needs straight out of the image, checks their
MD5s against the versions the patches were written for, patches two of them, and writes a ready-to-copy folder.
Only the unmodified Dano CD "Exp Nov-15-01" (`Dano_x86.cue/.bin`) is known to work.

## Install

On your computer (Python 3.8+, no extra packages):

```sh
python3 tools/build_dano_shell.py /path/to/Dano_x86.cue out
```

Copy `out/DanoShell` to the ZETA machine as `/boot/home/DanoShell` (FTP, SSH/scp, USB stick, ...).

On ZETA, in a Terminal:

```sh
sh /boot/home/DanoShell/install.sh
```

That backs up ZETA's own `Tracker`, `Deskbar` and `About` into `DanoShell/zeta/`, compiles the small helper programs
(needs ZETA's developer tools: `gcc`), and puts **BeOS Mode** and **ZETA Mode** on your Desktop. Nothing in
`/boot/beos/system` has changed yet.

Double-click **BeOS Mode**. The Tracker and Deskbar restart (about 10 seconds, the desktop flickers). Double-click
**ZETA Mode** to go back. From a Terminal: `sh /boot/home/DanoShell/switch.sh dano` / `switch.sh zeta`.

## If something goes wrong

- Normal undo: click **ZETA Mode**, or `sh /boot/home/DanoShell/restore-zeta-shell.sh`.
- No desktop at all (no Tracker/Deskbar): open a Terminal if you have one, or log in over SSH, and run
  `sh /boot/home/DanoShell/switch.sh zeta`. If the Tracker is simply missing run `/boot/beos/system/Tracker &` then
  `/boot/beos/system/Deskbar &`.
- Worst case: copy `DanoShell/zeta/{Tracker,Deskbar,About}` over the three files in `/boot/beos/system` from another
  OS or a boot CD, then run `mimeset -f` on them.
- Keep SSH (`sshd`) running while you experiment; ZETA does not start it at boot.

## Known limits

- Tested only on ZETA 1.2.1 (files with sizes 12649 / 457813 / 258715 bytes for Tracker / Deskbar / About; `install.sh` checks this).
- Not tested: a cold reboot while in BeOS Mode, Shut Down / Restart from Dano's Be menu, Tracker add-ons written for ZETA's Tracker.
- Dano's Deskbar ignores ZETA's saved position; `dbloc` puts it back to the top right after every switch.
- ZETA-only features of its Deskbar/Tracker (user sessions, its Start-menu layout) are not in BeOS Mode.
- Dano's Tracker lays desktop icons out slightly differently; a few may overlap until you drag them.

How and why it works, with the addresses and the dead ends: [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md).

## Layout

```
tools/build_dano_shell.py   reads the Dano CD image, applies the patches, writes DanoShell/
tools/bfs.py                small read-only BFS (BeOS file system) reader
zeta/install.sh             run on ZETA once: backup, compile helpers, desktop icons
zeta/switch.sh              zeta | dano : swap the three files and restart Tracker + Deskbar
zeta/killteam.sh            kill every thread of a team (ZETA's kill wants thread ids)
zeta/src/                   AboutDano, About launcher, dbloc (Deskbar position), the two Mode icons
```

## Licence

The code in this repository is MIT licensed (see LICENSE). BeOS, Dano, ZETA and their programs belong to their
respective owners; this project contains none of their code and is not affiliated with them.
