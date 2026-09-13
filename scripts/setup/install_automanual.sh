#!/usr/bin/env bash
# Explicit environment installation only; never launches a task or model call.
set -euo pipefail
for proxy_name in $(compgen -e); do
    if [[ "${proxy_name,,}" == *_proxy ]]; then unset "$proxy_name"; fi
done
export NO_PROXY='*' no_proxy='*' PIP_CONFIG_FILE=/dev/null
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${1:-}" != "--install" && "${1:-}" != "--install-text" ]]; then
    echo 'Plan only. Later create a separate environment: conda create -n memory-automanual python=3.9.16'
    echo 'Original full install requires pristine source and is not validated: --install'
    echo 'Do not install upstream dependencies into base or memory-infra. JSON smoke is verified; memory-loop integration is not.'
    echo 'Text-only audited preparation: conda run -n memory-automanual bash scripts/setup/install_automanual.sh --install-text'
    exit 0
fi
python -c 'import sys; assert sys.version_info[:3] == (3, 9, 16), "Use dedicated Python 3.9.16 environment"'
if [[ "${CONDA_DEFAULT_ENV:-}" != "memory-automanual" ]]; then
    echo 'Refusing installation outside memory-automanual' >&2
    exit 1
fi
if [[ "${1:-}" == "--install-text" ]]; then
    python "$project_root/scripts/setup/automanual.py" --check-patched
    command -v x86_64-conda-linux-gnu-g++ >/dev/null || {
        echo 'Install gcc_linux-64=11.2.0 and gxx_linux-64=11.2.0 in memory-automanual first.' >&2
        exit 1
    }
    mkdir -p "$project_root/.runtime/automanual-setup"
    text_log_dir="$(mktemp -d "$project_root/.runtime/automanual-setup/text-XXXXXXXX")"
    python -m pip --isolated install --index-url https://pypi.org/simple \
        -c "$project_root/configs/automanual_alfworld/text-constraints.txt" \
        'pip==24.0' 'setuptools==65.5.0' 'wheel==0.38.4' 'cmake==3.27.9' \
        'cffi==1.17.1' 'numpy==1.23.5' 'gym==0.15.4' 'networkx==2.5' \
        'pyyaml==6.0.2' 'cython==0.29.37' \
        > "$text_log_dir/prerequisites.log" 2>&1
    # Legacy cheapglk ignores mkstemp's return and builds with -Werror. Keep the
    # warning visible without changing its C code or any PDDL environment logic.
    export CPPFLAGS="${CPPFLAGS:-} -Wno-error=unused-result"
    python -m pip --isolated install --index-url https://pypi.org/simple --no-build-isolation \
        -c "$project_root/configs/automanual_alfworld/text-constraints.txt" \
        'spacy==3.7.5' \
        'https://github.com/MarcCote/TextWorld/archive/634f9f91fec732a79dd9e7623675301a53f06623.zip#sha256=bc404d7c193b30fde8d9c2b4af3a9ee74d3b6bf2cc69fc5418814491a472ddd5' \
        'https://github.com/MarcCote/downward/archive/84769171b9d965bf5739eaa7cf6604b0d9697534.zip#sha256=2294c8d5e44fc8fd37d00a8956d0dab3c0dd4bed347f31934eef96245f0dd9c7' \
        > "$text_log_dir/source-dependencies.log" 2>&1
    python -m pip check > "$text_log_dir/pip-check.txt" 2>&1
    echo 'Text dependencies installed. Import bundled ALFWorld via explicit source path; full extras not installed.'
    exit 0
fi
python "$project_root/scripts/setup/automanual.py" --check
runtime_dir="$project_root/.runtime/automanual-setup"
mkdir -p "$runtime_dir"
# A resolved freeze is an installation observation, not an upstream lock. Keep
# logs local: dependency tools may include local index credentials in diagnostics.
trap 'python -m pip freeze > "$runtime_dir/resolved-freeze.txt"' EXIT
python -m pip install \
    'https://github.com/MarcCote/TextWorld/archive/634f9f91fec732a79dd9e7623675301a53f06623.zip' \
    'https://github.com/MarcCote/downward/archive/84769171b9d965bf5739eaa7cf6604b0d9697534.zip' \
    > "$runtime_dir/source-dependencies.log" 2>&1
python -m pip install -r "$project_root/third_party/automanual/alfworld/requirements.txt" \
    > "$runtime_dir/requirements.log" 2>&1
python -m pip install --no-deps "$project_root/third_party/automanual/alfworld" \
    > "$runtime_dir/alfworld-install.log" 2>&1
echo 'Installation completed; no dataset download or task was launched. Phase 0 remains unverified.'
