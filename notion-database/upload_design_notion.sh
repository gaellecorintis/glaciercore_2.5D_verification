#!/usr/bin/env bash
# Upload a finished design's simulation results to the Notion project database.
#
# Requires the Notion_API repo (cloned by utils/gcp_setup/basic_setup_gcp.sh)
# and Notion credentials in the repo-root .env (see .env.example).
# Edit the design metadata below for the design you are uploading.
set -euo pipefail
cd "$(dirname "$0")"

# --- locations -------------------------------------------------------------
NOTION_API="${NOTION_API:-$HOME/Notion_API}"
SIMULATION_DIR="${SIMULATION_DIR:-$HOME/neutron_NT2502/simulations/SC_reference_150um}"
RESULTS_JSON="$SIMULATION_DIR/simulation_result/simulation_results_dim.json"
PARAMS_JSON="$SIMULATION_DIR/settings_sim.json"

# --- design metadata (edit per design) -------------------------------------
NAME_OF_DESIGN="SC_reference_150um"
TYPE_OF_DESIGN="S-C"
IO="2I-1O"
CUSTOMER="NEUTRON"
PROJECT="NT2502"
TECHNOLOGY="Cold Plate"
EMOJI="🎨"
AUTHOR="alessandro.pase@corintis.com"
NOTES="Reference design given by the customer. 150µm channel width and 150µm fin width."

# --- preflight checks ------------------------------------------------------
UPSERT="$NOTION_API/design_database_filling/notion_upsert_simresults.py"
[[ -f "$UPSERT" ]] || { echo "[notion] ERROR: Notion_API script not found: $UPSERT" >&2
    echo "[notion]   Clone github.com/Corintis/Notion_API (see utils/gcp_setup)." >&2; exit 1; }
for f in "$RESULTS_JSON" "$PARAMS_JSON"; do
    [[ -f "$f" ]] || { echo "[notion] ERROR: missing input '$f'" >&2; exit 1; }
done

echo "[notion] design   : $NAME_OF_DESIGN ($CUSTOMER / $PROJECT)"
echo "[notion] results  : $RESULTS_JSON"
python "$UPSERT" \
    --results-json "$RESULTS_JSON" \
    --params-json  "$PARAMS_JSON" \
    --name "$NAME_OF_DESIGN" \
    --type "$TYPE_OF_DESIGN" \
    --io "$IO" \
    --customer "$CUSTOMER" \
    --project "$PROJECT" \
    --technology "$TECHNOLOGY" \
    --emoji "$EMOJI" \
    --author "$AUTHOR" \
    --notes "$NOTES"
echo "[notion] Done."
