#!/usr/bin/env bash
set -euo pipefail
set +x

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if ! command -v claude >/dev/null 2>&1; then
  echo "error: claude executable not found in PATH" >&2
  exit 127
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: ${ENV_FILE} is missing; create it from .env.example and set DEEPSEEK_KEY" >&2
  exit 2
fi

# .env is a trusted local file for this project. Load it in a subshell so only the
# requested key is captured here; do not export the rest of .env to Claude Code.
DEEPSEEK_KEY_VALUE="$({
  set +x
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  printf '%s' "${DEEPSEEK_KEY:-}"
})"

if [[ -z "${DEEPSEEK_KEY_VALUE}" ]]; then
  echo "error: DEEPSEEK_KEY is empty in ${ENV_FILE}" >&2
  exit 2
fi

cd "${REPO_ROOT}"

# Use the current official DeepSeek Anthropic-compatible endpoint. The [1m]
# suffix is used so Claude Code accounts for the model's 1M context window.
# All Claude roles are intentionally mapped to V4 Flash for this worker.
exec env \
  -u DEEPSEEK_KEY \
  ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" \
  ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_KEY_VALUE}" \
  ANTHROPIC_MODEL="deepseek-v4-flash[1m]" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash[1m]" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash[1m]" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash[1m]" \
  CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash[1m]" \
  CLAUDE_CODE_EFFORT_LEVEL="max" \
  CLAUDE_CODE_AUTO_COMPACT_WINDOW="786432" \
  claude "$@"
