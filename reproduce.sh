#!/usr/bin/env bash
# Regenerate every result and figure from the Cleveland file. Fixed seeds. About 15 to 25 minutes on 2 CPU cores.
# Needs data/processed.cleveland.data (in the repo) and: pip install -r requirements.txt matplotlib
set -euo pipefail
cd "$(dirname "$0")"
# python3 train.py --cleveland-only      # optional: retrains and overwrites portal/model_weights.json (parity tests pin it)
python3 evaluate.py                        # 20x5-fold CV, bootstrap CIs      -> artifacts/validation.json
python3 benchmark.py                       # model-family comparison          -> stdout
python3 rigor.py                           # optimism, sample size, DCA, conformal -> artifacts/rigor.json
python3 selective_escalation.py            # triage experiment                -> artifacts/escalation.json
python3 make_figures.py                    # figures                          -> docs/figures, portal/img/research
echo "done. See docs/PAPER.md"
# Optional, needs the multi-site file (not in the repo):
#   python3 external_validation.py --data data/heart_disease_uci.csv
