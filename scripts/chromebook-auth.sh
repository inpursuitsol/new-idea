#!/bin/bash
# Chromebook / Penguin: fetch branch, venv, copy OAuth JSON, run YouTube login.
set -euo pipefail

REPO_URL="https://github.com/inpursuitsol/new-idea.git"
BRANCH="cursor/pehli-salary-youtube-bbab"
ROOT="${HOME}/new-idea"

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-full git

if [ ! -d "${ROOT}/.git" ]; then
  git clone "${REPO_URL}" "${ROOT}"
fi

cd "${ROOT}"
git remote set-url origin "${REPO_URL}" || true
git fetch origin "${BRANCH}"
git checkout -B "${BRANCH}" "origin/${BRANCH}"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

SECRET=""
for candidate in \
  "${ROOT}/client_secret.json" \
  /mnt/chromeos/MyFiles/Downloads/client_secret.json \
  /mnt/chromeos/MyFiles/Downloads/client_secret_*.json \
  "${HOME}/Downloads/client_secret.json" \
  "${HOME}/Downloads/client_secret_*.json"
do
  for f in $candidate; do
    if [ -f "$f" ]; then
      SECRET="$f"
      break 2
    fi
  done
done

if [ -z "${SECRET}" ]; then
  echo "Could not find client_secret JSON."
  echo "In Chrome OS Files, put the Google download in Downloads, then run:"
  echo "  ls /mnt/chromeos/MyFiles/Downloads"
  echo "The file is usually named client_secret_xxxxx.apps.googleusercontent.com.json"
  exit 1
fi

cp -f "${SECRET}" "${ROOT}/client_secret.json"
echo "Using ${SECRET}"
export PYTHONPATH="${ROOT}"
python -m pehli_salary.cli auth --client-secrets "${ROOT}/client_secret.json" --port 8080
