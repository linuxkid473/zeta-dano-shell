#!/bin/sh
# Run once on ZETA 1.2.1, from the DanoShell folder:   sh /boot/home/DanoShell/install.sh
# Expects the folder produced by tools/build_dano_shell.py (dano/Tracker, dano/Deskbar, about/lib/libbe.so) copied to /boot/home/DanoShell.
# Nothing in /boot/beos/system is changed here; that only happens when you click "BeOS Mode".
D=/boot/home/DanoShell
S=/boot/beos/system
cd $D || exit 1

size() { wc -c < "$1" | tr -d ' '; }
[ "`size $S/Tracker`" = 12649 ] && [ "`size $S/Deskbar`" = 457813 ] && [ "`size $S/About`" = 258715 ] || {
	echo "Tracker/Deskbar/About in $S do not look like ZETA 1.2.1 (or are already swapped). Nothing done."
	echo "If you are in BeOS Mode already, click ZETA Mode first."
	exit 1
}
for f in dano/Tracker dano/Deskbar about/lib/libbe.so; do
	[ -f $f ] || { echo "missing $D/$f  (run tools/build_dano_shell.py on your computer first)"; exit 1; }
done

echo "Backing up ZETA's own files to $D/zeta ..."
mkdir -p zeta
for f in Tracker Deskbar About; do
	[ -f zeta/$f ] || cat $S/$f > zeta/$f
done

echo "Building the helper programs (needs ZETA's developer tools) ..."
cd src || exit 1
gcc -o ../about/AboutDano aboutdano.cpp -lbe || exit 1
gcc -o ../about/AboutLaunch aboutlaunch.cpp -lbe || exit 1
gcc -o ../dbloc dbloc.cpp -lbe || exit 1
gcc -o "../ZETA Mode" zmode.c || exit 1
gcc -o "../BeOS Mode" bmode.c || exit 1
cd ..
cat about/AboutLaunch > dano/About

cp "ZETA Mode" "BeOS Mode" /boot/home/Desktop/
chmod +x switch.sh killteam.sh restore-zeta-shell.sh
echo
echo "Done. Two new icons are on your Desktop: \"BeOS Mode\" and \"ZETA Mode\"."
echo "Double-click BeOS Mode to switch (the desktop restarts for ~10 s). ZETA Mode switches back."
