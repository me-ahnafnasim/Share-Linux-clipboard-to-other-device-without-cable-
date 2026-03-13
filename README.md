# Share-Linux-clipboard-to-other-device-without-cable-

## Clipboard Relay Setup

The Linux clipboard server is intended to run with `systemd` and listen on port `52341`.

Current local API shape:

```text
http://127.0.0.1:52341/api/clipboard
```

For another device on the same network:

```text
http://YOUR_LAPTOP_IP:52341/api/clipboard
```

## Start The Server

Start the system service:

```bash
sudo systemctl start clipboard-relay.service
```

Restart it fresh:

```bash
sudo systemctl restart clipboard-relay.service
```

Enable it on boot:

```bash
sudo systemctl enable clipboard-relay.service
```

Check service status:

```bash
sudo systemctl status clipboard-relay.service --no-pager
```

## Verify The Port

Confirm the server is listening on `52341`:

```bash
ss -ltnp | grep -E ':52341[[:space:]]'
```

Test the local API:

```bash
curl http://127.0.0.1:52341/api/clipboard
```

Expected success output looks like:

```json
{"kind":"text","ok":true,"source":"x11","source_mime":"text/plain","text":"..."}
```

## Find The Laptop IP

Show the current local IP:

```bash
hostname -I
```

Show only the first IPv4 address:

```bash
hostname -I | awk '{print $1}'
```

Important: the laptop IP is usually not fixed. It can change after reconnecting to Wi-Fi, rebooting, or changing networks.

Example:

```text
http://172.22.83.209:52341/api/clipboard
```

## Android Or Phone Access

If local `curl` works on the laptop but the phone cannot connect, check these first:

- the phone and laptop are on the same Wi-Fi
- the phone is using `http://`, not `https://`
- the phone is using the current laptop IP
- port `52341` is allowed through the firewall
- the router is not blocking device-to-device traffic

Open the port with `ufw`:

```bash
sudo ufw allow 52341/tcp
```

Then test from the phone:

```text
http://YOUR_LAPTOP_IP:52341/api/clipboard
```

## Common Problem: Duplicate Server On Port 5000

If you see both `5000` and `52341` listening at the same time, there is usually a second copy of the server running.

Check both ports:

```bash
ss -ltnp | grep -E ':5000[[:space:]]|:52341[[:space:]]'
```

In this project, the most common cause was a user-level `systemd` service at:

```text
~/.config/systemd/user/clipboard-relay.service
```

That user service was configured for `5000`, while the system service was configured for `52341`.

Disable the user service so only the system service remains:

```bash
systemctl --user disable --now clipboard-relay.service
```

Then verify only `52341` is active:

```bash
ss -ltnp | grep -E ':5000[[:space:]]|:52341[[:space:]]'
```

## Common Problem: Wayland Or Display Errors

An error like this:

```text
{"error":"Failed to connect to a Wayland server ... | Error: Can't open display: (null)","ok":false}
```

means the server is running, but it cannot access the desktop clipboard session.

This usually happens when:

- the service starts without `DISPLAY`
- `XDG_RUNTIME_DIR` is missing
- stale Wayland variables point to a socket that does not exist

The launcher script has been updated to provide safer defaults for `systemd` starts, including:

- `XDG_RUNTIME_DIR`
- `XDG_SESSION_TYPE`
- `DISPLAY` for X11 sessions

If needed, inspect the active service environment:

```bash
systemctl show clipboard-relay.service -p Environment
```

Inspect the final applied service config:

```bash
systemctl cat clipboard-relay.service
```

## Quick Recovery

If things stop working, use this sequence:

```bash
systemctl --user disable --now clipboard-relay.service
sudo systemctl restart clipboard-relay.service
ss -ltnp | grep -E ':5000[[:space:]]|:52341[[:space:]]'
curl http://127.0.0.1:52341/api/clipboard
```

Healthy state:

- user service on `5000` is disabled
- system service is active
- only `52341` is listening
- local `curl` returns `{"ok":true,...}`
