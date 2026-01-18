#!/bin/bash
# package_py.sh - Install the package into the active Python (pyenv 'super' recommended)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="super"

# Validating environment
if command -v pyenv >/dev/null 2>&1; then
  current_env="$(pyenv version-name)"
  if [[ "${current_env}" != "${ENV_NAME}" ]]; then
    echo "[!] Detected pyenv environment: ${current_env}"
    echo "[!] Recommended env is '${ENV_NAME}'. Consider:"
    echo "    pyenv virtualenv 3.11 ${ENV_NAME}   # once"
    echo "    pyenv activate ${ENV_NAME}"
    echo "Or rerun with PYENV_VERSION=${ENV_NAME} prefixed."
  fi
fi


OPT_DIR="${HOME}/opt"
SPARK_VERSION="4.0.1"
SPARK_TGZ="spark-${SPARK_VERSION}-bin-hadoop3.tgz"
SPARK_DIR="${OPT_DIR}/spark-${SPARK_VERSION}-bin-hadoop3"

ensure_java17() {
  if ! command -v java >/dev/null 2>&1; then
    echo "[!] Java not found on PATH. Install Java 17+ (e.g., via jenv) for Spark tooling."
    return 0
  fi

  local version
  version="$(java -version 2>&1 | head -n1 | sed -E 's/.*version \"([0-9]+)(\.[0-9]+)?.*/\1/')"
  if [[ -z "${version}" || ! "${version}" =~ ^[0-9]+$ ]]; then
    # OpenJDK sometimes outputs to stderr, and format varies.
    # Just a rough check. If we can't parse, warn but continue.
    echo "[!] Unable to strictly parse Java version. Output was: $(java -version 2>&1 | head -n1)"
    return 0
  fi
  # Simple integer check if possible
  if [[ "${version}" =~ ^[0-9]+$ ]] && (( version < 17 )); then
    echo "[!] Java ${version} detected. Spark requires Java 17+ (e.g., 'jenv install openjdk64-17.0.16')."
    return 0
  fi
  echo "Java detected."
}

ensure_spark4() {
  if [[ -d "${SPARK_DIR}" ]]; then
    echo "Spark ${SPARK_VERSION} already present at ${SPARK_DIR}"
    return
  fi

  mkdir -p "${OPT_DIR}"
  local tgz_path="${OPT_DIR}/${SPARK_TGZ}"
  if [[ ! -f "${tgz_path}" ]]; then
    echo "Downloading Spark ${SPARK_VERSION}..."
    curl -fLo "${tgz_path}" "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/${SPARK_TGZ}"
    if [[ $? -ne 0 ]]; then
      echo "[!] Failed to download Spark ${SPARK_VERSION}. Install manually and rerun."
      return 0
    fi
  else
    echo "Using existing ${tgz_path}"
  fi

  echo "Extracting Spark ${SPARK_VERSION} to ${OPT_DIR}"
  tar -xzf "${tgz_path}" -C "${OPT_DIR}" || {
    echo "[!] Failed to extract ${tgz_path}. Install Spark manually."
    return 0
  }
}

ensure_java17
ensure_spark4

echo "Using Python: $(command -v python)"
echo "Installing package in editable mode..."
python -m pip install -e "${SCRIPT_DIR}"
echo "Install complete."
