# How it works

## 1. Will Dano's shell programs even load on ZETA?

Check by symbols. For each program, list its undefined dynamic symbols and look them up in the exports of ZETA 1.2.1's
libraries (`libbe`, `libroot`, `libtracker`, `libtranslation`, `libzeta`, ...):

| program (Dano CD) | NEEDED | undefined symbols not found in ZETA's libs |
|---|---|---|
| `Tracker` (2.2 MB, self-contained) | libroot, libbe, libtranslation | **0** of 1352 |
| `Deskbar` | libbe, libtracker, libroot | **1** of 708: `TrackerInitIconPreloader__8BPrivatev` |
| `libbe.so` (Dano's) | libroot, libtextencoding, libpng | **0** of 247 |

ZETA is Dano-derived, so the shell programs resolve almost completely. The single miss is a rename: ZETA's
`libtracker` exports the same function as `InitIconPreloader__8BPrivatev`. Same-length-or-shorter renames can be done
in place in the string table of the executable (the undefined symbol's name is only used at lookup time).

**Patch 1 (Deskbar):** `TrackerInitIconPreloader__8BPrivatev` -> `InitIconPreloader__8BPrivatev`, padded with NULs.

Symbol presence is necessary, not sufficient; it worked here because ZETA's class layouts and `app_server` protocol
stayed compatible for these programs. Nothing about this is guaranteed for other ZETA versions.

## 2. Why replace the files instead of running Dano's shell from a private folder?

A private folder works for loading (ZETA looks in `<app folder>/lib` first; the default `LIBRARY_PATH` is
`%A/.:%A/components:%A/lib:~/config/lib:/boot/beos/system/lib`, so a private `libtracker.so` would be found by a
Deskbar in that folder). We tried it: Dano's Tracker and Deskbar started from `/boot/home/...` ran, but ZETA's own
copies kept coming back (something respawns them after they are killed; we did not find out what), so the two shells
fought over the desktop. Replacing the three files in `/boot/beos/system`, with backups, is the version that behaves.
Patch 1 is what lets the Deskbar run against ZETA's own `libtracker` without shipping a second one.

## 3. "About BeOS" did nothing

In Dano, `About BeOS...` in the Deskbar sends the message `'Spls'` (0x53706c73) to the **Tracker**, whose
`TTracker::MessageReceived` calls `run_be_about()` from `libbe`. In Dano's libbe that opens the About window
(`BTrackerTheft::AboutWindow`). In ZETA's libbe, `run_be_about__Fv` is a 7-byte empty function; ZETA's own Deskbar
launches `/boot/beos/system/About` instead (ZETA's Tracker has `TTracker::RunZetaAbout`, which does
`system("/boot/beos/system/About &")`).

**Patch 2 (Tracker):** make that call do what ZETA does.

- The imported symbol `run_be_about__Fv` (17 bytes with its NUL in `.dynstr`, file offset 0x4714a) is renamed to
  `system`, and the bytes after it hold a command string: `system\0/bin/A &\0`. The PLT slot that used to resolve to
  `run_be_about` now resolves to `system`.
- The call site at 0x128761 (`call plt` with no arguments) becomes `lea cmd(%ebx),%eax; push %eax; call plt; jmp tramp`
  (14 bytes of the 15 available), with the shared tail jump put into six bytes of unreachable padding at 0x12877a
  that jump to the function epilogue at 0x128880. The epilogue restores `esp` from `ebp`, so the pushed argument is
  never popped explicitly. `ebx` is the GOT base (`0x12856e + 0x90386` in `MessageReceived`).
- `/bin/A` is a two-line script (written by `switch.sh dano`): `exec /boot/beos/system/About`.

The string had to be short because the only free mapped bytes were the old symbol-name slot.

## 4. The About box itself

Dano's About box is in Dano's `libbe.so`. Loading Dano's libbe into one small program is safe enough:
`aboutdano.cpp` is just `BApplication app(...); run_be_about(); app.Run();`, installed in
`/boot/home/DanoShell/about/` with `lib/libbe.so` (Dano's) beside it, so `%A/lib` picks Dano's copy for that one
process. It talks to ZETA's `app_server` without problems.

ZETA's own `About` (signature `application/x-vnd.yT-About`) is replaced by `aboutlaunch.cpp`, a program that
registers that signature and starts `AboutDano` with `load_image`. The file is rewritten in place so it keeps its
`BEOS:APP_SIG` attribute (new files get theirs back with `mimeset -f`).

## 5. Placing the Deskbar

Dano's Deskbar ignored the position in ZETA's `~/config/settings/Deskbar_settings` and opened top-left.
`dbloc.cpp` calls `BDeskbar::SetLocation(B_DESKBAR_RIGHT_TOP, expanded)`; `switch.sh dano` runs it after the
Deskbar is up.

## 6. Switching

`switch.sh zeta|dano`:

1. for each of Tracker, Deskbar, About: write the mode's copy to `<name>.swap`, `chmod +x`, `mv -f` over the original
   (never overwrite a running executable in place), then `mimeset -f` (signature, type and icon attributes are lost
   with the new inode);
2. create (dano) or remove (zeta) `/boot/beos/bin/A`;
3. kill every thread of the running Tracker and Deskbar teams (`killteam.sh`: ZETA's `kill` wants thread ids,
   and `quit` is just a copy of `ps`);
4. wait, and start Tracker and Deskbar by hand if ZETA did not respawn them (it sometimes does and sometimes does not);
5. in dano mode, run `dbloc`.

The two desktop icons are 3-line C programs that run `switch.sh` in the background (`system("... &")`) so the script
survives the Tracker that launched it.

## 7. Dead ends worth knowing about

- **Renaming `libroot.so` in the Tracker's NEEDED list** to inject a shim library (`libabt.so`) that defines
  `run_be_about`: the patched Tracker silently refused to start. libroot is special for the loader.
  (A Tracker that cannot start leaves you with a desktop but no Tracker; the recovery is in the README.)
- **Running Dano's and ZETA's shells side by side**: both run, windows and desktop icons collide, and ZETA relaunches
  its own copy after you kill them.
- **A private libbe for the Tracker/Deskbar** with `run_be_about` patched: ZETA's stub has 7 bytes; there is no room
  for a call.
- Unverified claim traps: a second instance of a single-launch app does not necessarily exit, so "it exited quietly"
  is not evidence that a patched binary loaded. Compare against a known-good copy instead.

## 8. Practical notes from doing it over SSH

- ZETA's sshd is OpenSSH 3.9: enable `diffie-hellman-group14-sha1`, `ssh-rsa` host and pubkey algorithms in your
  client. It is not started at boot (`sshd` by hand).
- Verify every transfer with `md5sum` on both ends and retry; long transfers over a flaky link get cut.
- To see the screen from outside: a tiny BeAPI program that does `BScreen::GetBitmap` and writes a PPM.
- The machine was in use while this was developed: restart only what you must.
