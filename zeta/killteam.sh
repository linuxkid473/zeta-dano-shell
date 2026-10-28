#!/bin/sh
# killteam.sh TEAMNUM : kill -9 every thread of a team (ZETA's kill wants thread ids)
ps | awk -v t="$1" '/\(team [0-9]+\)/ { on = ($0 ~ "\\(team " t "\\)"); next } on && $1 ~ /^[0-9]+$/ { print $1 }' | while read th; do kill -9 $th 2>/dev/null; done
