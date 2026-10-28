#!/bin/sh
# switch.sh zeta|dano : swap /boot/beos/system/{Tracker,Deskbar,About} between ZETA's and the Dano set, then restart the shell
M=$1
D=/boot/home/DanoShell
[ -d $D/$M ] || { echo "no such mode $M"; exit 1; }
cd /boot/beos/system || exit 1
for f in Tracker Deskbar About; do
	cat $D/$M/$f > $f.swap && chmod +x $f.swap && mv -f $f.swap $f || exit 1
done
mimeset -f Tracker Deskbar About
if [ $M = dano ]; then
	printf '#!/bin/sh\nexec /boot/beos/system/About\n' > /boot/beos/bin/A; chmod +x /boot/beos/bin/A
else
	rm -f /boot/beos/bin/A
fi
for t in `ps | grep "^\(\./\|/boot/beos/system/\)\(Deskbar\|Tracker\) (team" | sed "s/.*(team \([0-9]*\)).*/\1/"`; do
	sh $D/killteam.sh $t
done
sleep 6
ps | grep "(team" | grep -q "Tracker (team" || { /boot/beos/system/Tracker & sleep 4; }
ps | grep "(team" | grep -q "Deskbar (team" || { /boot/beos/system/Deskbar & sleep 4; }
[ $M = dano ] && $D/dbloc
echo "mode $M done"
