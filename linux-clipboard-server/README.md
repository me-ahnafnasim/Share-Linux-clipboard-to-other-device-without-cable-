# Clipboard Relay Server

Share your Linux laptop's clipboard over local Wi-Fi so another device, such as an Android phone, can fetch the latest text or image from a browser.

This guide covers:

- how to clone the project from GitHub
- how to find the correct local URL
- how to make the laptop's IP address static
- how to run the server manually
- how to start it automatically with `systemd`
- how to troubleshoot common Fedora issues

## What This Project Does

The server runs on your Linux laptop and exposes a small web app on your local network, usually on port `5000`.

From another device on the same Wi-Fi network, open:

```text
http://YOUR-LAPTOP-IP:5000
```

Example:

```text
http://10.45.87.171:5000
```

## 1. Clone The Project

If this project is hosted on GitHub, clone it first:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
```

If the repository contains multiple apps, locate the server folder and enter it:

```bash
cd apps/linux-clipboard-server
```

To confirm you are in the correct project folder, you should see these files:

```bash
ls
```

Expected files include:

- `clipboard_server.py`
- `run_server.sh`
- `setup.sh`
- `clipboard-relay.service`

## 2. Install Dependencies

On Fedora:

```bash
sudo dnf install -y python3 python3-pip python3-virtualenv xclip wl-clipboard firewalld
```

Create the virtual environment and install Python packages:

```bash
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install flask pillow waitress
chmod +x run_server.sh
```

## 3. Run The Server Manually

Before setting up auto-start, test it manually:

```bash
./run_server.sh
```

If the server starts correctly, it should listen on:

```text
http://0.0.0.0:5000
```

On the laptop itself, test:

```text
http://127.0.0.1:5000
```

## 4. Find The Correct Project URL

The browser URL for other devices is:

```text
http://LAPTOP-IP:5000
```

Get your laptop's current IPv4 address:

```bash
hostname -I
```

or:

```bash
ip -4 addr show scope global
```

Look for an address like:

```text
10.45.87.171
```

If your laptop IP is `10.45.87.171`, the correct URL is:

```text
http://10.45.87.171:5000
```

Important:

- the laptop and phone must be on the same Wi-Fi network
- the port must be `5000` unless you changed `CLIPBOARD_SERVER_PORT`
- if Android says "refused to connect", the server is usually not running yet

## 5. Open Firewall Port 5000

If `firewalld` is enabled, allow the port:

```bash
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## 6. Make The Laptop IP Address Static

If you want the URL to stay the same, make the current Wi-Fi IP static.

First, inspect the active connection:

```bash
nmcli -t -f NAME,UUID,TYPE,DEVICE connection show --active
```

Find the active Wi-Fi connection name and the interface. Example:

```text
Abc:d4da6695-6073-414e-a21c-b089a6a2856c:802-11-wireless:wlp1s0
```

Then gather the current address, gateway, and DNS:

```bash
ip -4 addr show scope global
ip route show default
nmcli -g IP4.DNS device show wlp1s0
```

Example values:

- IP: `10.45.87.171/24`
- Gateway: `10.45.87.85`
- DNS: `10.45.87.85`
- Connection name: `Abc`

Apply them as a static configuration:

```bash
nmcli connection modify 'Abc' \
  ipv4.method manual \
  ipv4.addresses '10.45.87.171/24' \
  ipv4.gateway '10.45.87.85' \
  ipv4.dns '10.45.87.85' \
  ipv4.ignore-auto-dns yes
```

Reconnect the Wi-Fi profile:

```bash
nmcli connection down 'Abc'
nmcli connection up 'Abc'
```

Verify:

```bash
hostname -I
nmcli -f ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns connection show 'Abc'
```

## 7. Start Automatically With systemd

### Recommended On Fedora: Use A User Service

This project depends on desktop clipboard access, so a `systemd --user` service is the safest setup. It starts in your user session and avoids Fedora SELinux issues that often block system services from executing files inside `/home`.

Create the user service directory:

```bash
mkdir -p ~/.config/systemd/user
```

Create `~/.config/systemd/user/clipboard-relay.service`:

```ini
[Unit]
Description=Clipboard Relay Server
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/absolute/path/to/linux-clipboard-server
ExecStart=/absolute/path/to/linux-clipboard-server/run_server.sh
Restart=always
RestartSec=3
Environment=CLIPBOARD_SERVER_HOST=0.0.0.0
Environment=CLIPBOARD_SERVER_PORT=5000
Environment=CLIPBOARD_SERVER_USE_WAITRESS=1
Environment=CLIPBOARD_SERVER_THREADS=4

[Install]
WantedBy=default.target
```

If your project lives at `/home/ahnafnasim/projects/linux-clipboard-server`, the concrete values are:

```ini
[Unit]
Description=Clipboard Relay Server
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ahnafnasim/projects/linux-clipboard-server
ExecStart=/home/ahnafnasim/projects/linux-clipboard-server/run_server.sh
Restart=always
RestartSec=3
Environment=CLIPBOARD_SERVER_HOST=0.0.0.0
Environment=CLIPBOARD_SERVER_PORT=5000
Environment=CLIPBOARD_SERVER_USE_WAITRESS=1
Environment=CLIPBOARD_SERVER_THREADS=4

[Install]
WantedBy=default.target
```

Enable and start it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now clipboard-relay.service
systemctl --user status clipboard-relay.service
```

To keep the user service available even after reboot before you manually open a session, enable linger:

```bash
sudo loginctl enable-linger "$USER"
```

### If You Still Want A System Service

Using the included `clipboard-relay.service` as a system-wide service can fail on Fedora with errors like:

```text
Permission denied
Failed at step EXEC
status=203/EXEC
```

That usually happens because SELinux blocks system services from executing scripts stored in `/home`.

If you want a true system service, move the project to a system path such as `/opt/clipboard-relay`, update the service file to point there, then install it into `/etc/systemd/system`.

For clipboard-driven apps, the user service is usually the better choice.

## 8. Verify It Is Running

Check user service status:

```bash
systemctl --user status clipboard-relay.service
```

Check whether port `5000` is listening:

```bash
ss -ltnp | grep 5000
```

Open the service from another device:

```text
http://YOUR-STATIC-IP:5000
```

## 9. Common Problems

### Android Shows "Refused To Connect"

Usually one of these is true:

- the server is not running
- the phone is on a different Wi-Fi network
- the firewall is blocking port `5000`
- the server crashed during startup

Check:

```bash
systemctl --user status clipboard-relay.service
journalctl --user -u clipboard-relay.service -n 50 --no-pager
ss -ltnp | grep 5000
```

### `clipboard-relay.service` Could Not Be Found

You have not installed the service yet. Create the user service file and run:

```bash
systemctl --user daemon-reload
systemctl --user enable --now clipboard-relay.service
```

### `status=203/EXEC` Or `Permission Denied`

This is a common Fedora issue when trying to run a system service directly from `/home`. Use a `systemd --user` service instead.

### The IP Changes After Reboot

Your Wi-Fi profile is still using DHCP. Re-check the static-IP section and confirm:

```bash
nmcli -f ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns connection show 'YOUR-CONNECTION'
```

You want:

```text
ipv4.method: manual
```

## 10. Useful Commands

Start the user service:

```bash
systemctl --user start clipboard-relay.service
```

Restart the user service:

```bash
systemctl --user restart clipboard-relay.service
```

Stop the user service:

```bash
systemctl --user stop clipboard-relay.service
```

Follow logs:

```bash
journalctl --user -u clipboard-relay.service -f
```

Disable auto-start:

```bash
systemctl --user disable --now clipboard-relay.service
```

## 11. Quick Start Summary

Clone:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO/apps/linux-clipboard-server
```

Install:

```bash
sudo dnf install -y python3 python3-pip python3-virtualenv xclip wl-clipboard firewalld
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install flask pillow waitress
chmod +x run_server.sh
```

Run:

```bash
./run_server.sh
```

Auto-start:

```bash
mkdir -p ~/.config/systemd/user
systemctl --user daemon-reload
systemctl --user enable --now clipboard-relay.service
```

Open from phone:

```text
http://YOUR-LAPTOP-IP:5000
```
