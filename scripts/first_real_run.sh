#!/usr/bin/env bash
# First real run of the pipeline on a Mac or Linux machine with internet access.
# Fetches all four source lists, chunks them, and bundles a small report to send back.
# Run from the repository root:  bash scripts/first_real_run.sh
set -euo pipefail

PY="${PYTHON:-python3}"
"$PY" --version
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e ".[dev]"
[ -f .env ] || cp .env.example .env

L="sources/ie_student.toml sources/us_student.toml sources/cu_denver.toml sources/ucd.toml"
mkdir -p report
echo "== fetch ==" | tee report/fetch.txt
dishaa-fetch --sources $L 2>&1 | tee -a report/fetch.txt || true
echo "== chunk ==" | tee report/chunk.txt
dishaa-chunk --sources $L 2>&1 | tee -a report/chunk.txt || true
for id in cud-health-dates-costs cud-elp ucd-fee-deadlines ucd-fees-noneu-ug-2026-27 student-faq us-sits-working; do
  dishaa-chunk --sources $L --show "$id" > "report/show_$id.txt" 2>&1 || true
done
for c in data/raw/*/manifest.json; do cp "$c" "report/manifest_$(basename "$(dirname "$c")").json"; done
zip -qr dishaa_first_run_report.zip report
echo
echo "Done. Send me: dishaa_first_run_report.zip (in this folder)."
