#!/usr/bin/env bash
set -euo pipefail
for proxy_name in $(compgen -e); do
    if [[ "${proxy_name,,}" == *_proxy ]]; then unset "$proxy_name"; fi
done
export NO_PROXY='*' no_proxy='*' PIP_CONFIG_FILE=/dev/null
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${1:-}" != --install ]]; then
    echo 'Plan only: memory-automanual Python 3.9.16; pinned Skill_Bank dependencies; direct public PyPI; no model calls.'
    exit 0
fi
[[ "${CONDA_DEFAULT_ENV:-}" == memory-automanual ]] || exit 1
python -c 'import sys; assert sys.version_info[:3] == (3,9,16)'
mkdir -p "$project_root/.runtime/automanual-setup"
skill_log_dir="$(mktemp -d "$project_root/.runtime/automanual-setup/skill-XXXXXXXX")"
trap 'python -m pip list --format=json > "$skill_log_dir/packages.json"' EXIT
python -m pip --isolated install --index-url https://pypi.org/simple --retries 0 \
    -c "$project_root/configs/automanual_alfworld/skill-constraints.txt" \
    -r "$project_root/configs/automanual_alfworld/skill-requirements.txt" \
    > "$skill_log_dir/install.log" 2>&1
python -m pip check > "$skill_log_dir/pip-check.txt" 2>&1
echo 'Skill dependencies installed and pip check passed. No API compatibility claimed.'
