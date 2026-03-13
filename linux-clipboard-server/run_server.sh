#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
  echo "Virtual environment is missing. Run ./setup.sh first." >&2
  exit 1
fi

export CLIPBOARD_SERVER_HOST="${CLIPBOARD_SERVER_HOST:-0.0.0.0}"
export CLIPBOARD_SERVER_PORT="${CLIPBOARD_SERVER_PORT:-5000}"
export CLIPBOARD_SERVER_USE_WAITRESS="${CLIPBOARD_SERVER_USE_WAITRESS:-1}"
export CLIPBOARD_SERVER_THREADS="${CLIPBOARD_SERVER_THREADS:-4}"

USER_RUNTIME_DIR="/run/user/$(id -u)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-${USER_RUNTIME_DIR}}"

if [[ -z "${XDG_SESSION_TYPE:-}" ]]; then
  if [[ -n "${WAYLAND_DISPLAY:-}" || -S "${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY:-wayland-0}" ]]; then
    export XDG_SESSION_TYPE="wayland"
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
  else
    export XDG_SESSION_TYPE="x11"
  fi
fi

if [[ "${XDG_SESSION_TYPE}" == "x11" && -z "${DISPLAY:-}" ]]; then
  export DISPLAY=":1"
fi

cd "${SCRIPT_DIR}"
exec "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/clipboard_server.py"
