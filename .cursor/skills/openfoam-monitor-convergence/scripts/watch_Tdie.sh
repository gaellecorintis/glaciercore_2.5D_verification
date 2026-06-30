#!/bin/bash
# Watcher EXTERNE (lecture seule) - ne touche pas au run.
# Surveille les snapshots ecrits par le run et extrait Tjmax(die) avant purge.
# Accumule dans postProcessing/die/cellMax(T)/<startTime>/volFieldValue.dat
# Le run garde purgeWrite 3 ; ce script attrape chaque temps tant qu'il existe.

cd /home/gaelle/OpenFOAM/hm27_ne_quarter || exit 1
source /opt/openfoam13/etc/bashrc

POLL=120          # periode de scan (s)
CSV=Tdie_history.csv

extract_done_times() {
  # temps deja presents dans tous les volFieldValue.dat
  grep -ahE '^[0-9]' postProcessing/die/'cellMax(T)'/*/volFieldValue.dat 2>/dev/null \
    | awk '{print $1}' | sort -un
}

while true; do
  # temps dispo sur disque (hors 0)
  avail=$(ls -d processor0/[0-9]* 2>/dev/null | sed 's#processor0/##' | grep -vE '^0$' | sort -un)
  done=$(extract_done_times)
  # nouveaux temps = avail - done
  newt=$(comm -23 <(echo "$avail") <(echo "$done") | paste -sd, -)

  if [ -n "$newt" ]; then
    echo "[$(date +%H:%M:%S)] extraction Tdie pour temps: $newt"
    mpirun -np 24 foamPostProcess -region die -func 'cellMax(T)' -time "$newt" -parallel \
      > /dev/null 2>&1
    echo "[$(date +%H:%M:%S)] extraction Tout (bilan energie) pour temps: $newt"
    mpirun -np 24 foamPostProcess -region fluid -func 'patchAverage(patch=outlet, field=T)' \
      -time "$newt" -parallel > /dev/null 2>&1
  fi

  # reconstruit le CSV maitre Tjmax (dedup par temps)
  echo "iter,T_K,T_C" > "$CSV"
  grep -ahE '^[0-9]' postProcessing/die/'cellMax(T)'/*/volFieldValue.dat 2>/dev/null \
    | awk '{print $1","$2","($2-273.15)}' | sort -t, -k1 -n -u >> "$CSV"

  # reconstruit le CSV bilan energie (Q_out/Q_in %)
  python3 build_qout.py > /dev/null 2>&1

  sleep "$POLL"
done
