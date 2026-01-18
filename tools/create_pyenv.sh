#!/usr/bin/env bash
# create_pyenv.sh - Install pyenv if missing, then create the 'super' env and install packages
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-${(%):-%x}}"
ROOT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")/.." && pwd)"
ENV_NAME="super"
PYTHON_VERSION="3.11"
PYENV_ROOT="${PYENV_ROOT:-${HOME}/.pyenv}"
IS_SOURCED="false"
if [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "$0" ]]; then
  IS_SOURCED="true"
elif [[ -n "${ZSH_EVAL_CONTEXT:-}" && "${ZSH_EVAL_CONTEXT}" == *:file* ]]; then
  IS_SOURCED="true"
fi

ensure_pyenv() {
  export PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${PATH}"
  if command -v pyenv >/dev/null 2>&1; then
    return
  fi

  echo "pyenv not found. Installing..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://pyenv.run | bash
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://pyenv.run | bash
  else
    echo "[!] Neither curl nor wget found. Install one and rerun."
    exit 1
  fi

  export PYENV_ROOT="${PYENV_ROOT}"
  export PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${PATH}"
  if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
  else
    echo "[!] pyenv installation did not add to PATH. Restart your shell and rerun."
    exit 1
  fi
}

append_pyenv_rc() {
  local rc_file="$1"
  local start_marker="# >>> super_powers pyenv init (create_pyenv.sh)"
  local end_marker="# <<< super_powers pyenv init"

  if [[ ! -f "${rc_file}" ]]; then
    return
  fi
  if rg -qF "${start_marker}" "${rc_file}"; then
    return
  fi

  {
    echo ""
    echo "${start_marker}"
    echo "# Added by ${ROOT_DIR}/tools/create_pyenv.sh"
    echo "export PYENV_ROOT=\"${HOME}/.pyenv\""
    echo "export PATH=\"\\$PYENV_ROOT/bin:\\$PYENV_ROOT/shims:\\$PATH\""
    echo "eval \"\\$(pyenv init -)\""
    echo "${end_marker}"
  } >> "${rc_file}"
  echo "Added pyenv init to ${rc_file}"
}

ensure_rc_config() {
  if [[ -n "${PYENV_ROOT:-}" ]]; then
    return
  fi
  if [[ -n "${ZSH_VERSION:-}" ]]; then
    append_pyenv_rc "${HOME}/.zshrc"
  elif [[ -n "${BASH_VERSION:-}" ]]; then
    append_pyenv_rc "${HOME}/.bashrc"
    append_pyenv_rc "${HOME}/.bash_profile"
  else
    append_pyenv_rc "${HOME}/.profile"
  fi
}

ensure_pyenv

if command -v pyenv >/dev/null 2>&1; then
  ensure_rc_config
  eval "$(pyenv init -)"
  if pyenv virtualenv-init - >/dev/null 2>&1; then
    eval "$(pyenv virtualenv-init -)"
  fi
else
  echo "[!] pyenv is not available on PATH after install. Restart your shell and rerun."
  exit 1
fi

echo "Installing Python ${PYTHON_VERSION} (if needed)..."
pyenv install -s "${PYTHON_VERSION}"

env_exists="false"
if pyenv virtualenvs --bare 2>/dev/null | grep -qx "${ENV_NAME}"; then
  env_exists="true"
elif [[ -d "${PYENV_ROOT}/versions/${ENV_NAME}" ]]; then
  env_exists="true"
fi

if [[ "${env_exists}" != "true" ]]; then
  echo "Creating pyenv virtualenv '${ENV_NAME}'..."
  if ! pyenv virtualenv "${PYTHON_VERSION}" "${ENV_NAME}"; then
    if [[ -d "${PYENV_ROOT}/versions/${ENV_NAME}" ]]; then
      echo "pyenv virtualenv '${ENV_NAME}' already exists."
    else
      echo "[!] Failed to create pyenv virtualenv '${ENV_NAME}'."
      exit 1
    fi
  fi
else
  echo "pyenv virtualenv '${ENV_NAME}' already exists."
fi

current_env="$(pyenv version-name 2>/dev/null || true)"
if [[ "${current_env}" != "${ENV_NAME}" ]]; then
  echo "Activating pyenv environment '${ENV_NAME}'..."
  if ! pyenv shell "${ENV_NAME}" >/dev/null 2>&1; then
    export PYENV_VERSION="${ENV_NAME}"
  fi
fi

PYENV_VERSION="${ENV_NAME}" python -m pip install --upgrade pip

PYENV_VERSION="${ENV_NAME}" bash "${ROOT_DIR}/package_py.sh"

if [[ "${IS_SOURCED}" != "true" ]]; then
  echo "[i] To keep '${ENV_NAME}' active in your current terminal, run:"
  echo "    source ${ROOT_DIR}/tools/create_pyenv.sh"
fi
