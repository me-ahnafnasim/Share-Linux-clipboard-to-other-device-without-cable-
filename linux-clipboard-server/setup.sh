#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-5000}"
FIREWALL_TOOL="${FIREWALL_TOOL:-auto}"

if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "dnf"
    return
  fi

  if command -v pacman >/dev/null 2>&1; then
    echo "pacman"
    return
  fi

  echo "unsupported"
}

install_dependencies() {
  local pm
  pm="$(detect_package_manager)"

  case "${pm}" in
    apt)
      ${SUDO} apt-get update
      ${SUDO} apt-get install -y python3 python3-pip python3-venv xclip wl-clipboard ufw
      ;;
    dnf)
      ${SUDO} dnf install -y python3 python3-pip python3-virtualenv xclip wl-clipboard firewalld
      ;;
    pacman)
      ${SUDO} pacman -Sy --noconfirm python python-pip python-virtualenv xclip wl-clipboard ufw
      ;;
    *)
      echo "Unsupported package manager. Install manually:"
      echo "  python3 python3-pip flask pillow xclip wl-clipboard"
      exit 1
      ;;
  esac
}

create_virtualenv() {
  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
  fi

  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install flask pillow
}

configure_ufw() {
  if ! command -v ufw >/dev/null 2>&1; then
    return 1
  fi

  ${SUDO} ufw allow "${PORT}/tcp"
  echo "Configured ufw to allow TCP port ${PORT}."
}

configure_firewalld() {
  if ! command -v firewall-cmd >/dev/null 2>&1; then
    return 1
  fi

  ${SUDO} systemctl enable --now firewalld >/dev/null 2>&1 || true
  ${SUDO} firewall-cmd --permanent --add-port="${PORT}/tcp"
  ${SUDO} firewall-cmd --reload
  echo "Configured firewalld to allow TCP port ${PORT}."
}

configure_firewall() {
  case "${FIREWALL_TOOL}" in
    ufw)
      configure_ufw || echo "ufw is not available."
      ;;
    firewalld)
      configure_firewalld || echo "firewalld is not available."
      ;;
    auto)
      configure_ufw || configure_firewalld || echo "No supported firewall tool detected. Configure port ${PORT}/tcp manually."
      ;;
    none)
      echo "Skipping firewall configuration."
      ;;
    *)
      echo "Unknown FIREWALL_TOOL=${FIREWALL_TOOL}. Use auto, ufw, firewalld, or none."
      exit 1
      ;;
  esac
}

show_ip_help() {
  echo "Local IP addresses:"
  hostname -I 2>/dev/null || true
  ip -4 addr show scope global 2>/dev/null | awk '/inet / {print $2}'
}

install_dependencies
create_virtualenv
configure_firewall
show_ip_help

echo
echo "Setup complete."
echo "Run the server with:"
echo "  ./.venv/bin/python clipboard_server.py"
