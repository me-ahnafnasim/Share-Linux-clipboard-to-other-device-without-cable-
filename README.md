# Share Linux Clipboard(image+text) To Other Devices Without Cable


## I Left the Samsung Ecosystem and Built My Own Linux-to-Android Clipboard Sharing Tool

As a Samsung device user, I was deep inside the Samsung ecosystem. To be honest, I did not really enjoy it. On top of that, as a software developer, I work with different frameworks and often need to run projects locally. Over time, my PC started feeling slow, and recently I moved to Linux.

After moving to Linux, I missed one small but very useful feature: clipboard sharing between my laptop and phone, especially for both image and text. I searched for many apps, but I could not find a simple tool that directly shared clipboard images. Some tools can handle text, including KDE Connect in some cases, but I wanted something lightweight, local, and under my control.

So I built my own solution. Today, I am sharing how you can do the same.

## Step 1: How to use it

This project runs a small Flask server on Linux and lets your Android phone access it over local Wi‑Fi.

Start the project:

From the below github link clone the repo in your own machine by using  </br>
i) git clone https://github.com/me-ahnafnasim/Share-Linux-clipboard-to-other-device-without-cable-.git </br>
ii) move to the path where the clone files are by using cd or pwd command and replace (/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server)  </br>

```bash
cd /home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server
chmod +x setup.sh run_server.sh
./setup.sh
systemctl --user enable --now clipboard-relay.service
```

Find your PC IP address:

```bash
hostname -I
```

Then open this on your Android phone:

```text
http://YOUR-PC-IP:5000
```

Now the flow is simple:
- copy text or an image on your Linux PC
- open the page on your phone
- tap `Fetch Clipboard`
- if the clipboard has an image, it shows the preview
- if the clipboard has text, it shows the text

## Step 2: Install it with `systemd`

If you want the tool to keep working in the background, `systemd` is the best option.

Use these commands:

```bash
cd /home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server
chmod +x setup.sh run_server.sh
./setup.sh
mkdir -p ~/.config/systemd/user
cp /home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server/clipboard-relay.service ~/.config/systemd/user/clipboard-relay.service
systemctl --user daemon-reload
systemctl --user enable --now clipboard-relay.service
systemctl --user status clipboard-relay.service --no-pager
```

Why `systemd`:
- it starts automatically
- it keeps the server running in the background
- it can restart the service if it fails

The downside:
- clipboard access on Linux can be tricky, especially on Wayland
- a system-wide service may not be able to access the logged-in user clipboard correctly
- in practice, a `systemctl --user` service works better for clipboard-based tools

## Step 3: How to check logs and remove it

To check service status:

```bash
systemctl --user status clipboard-relay.service --no-pager
```

To see live logs:

```bash
journalctl --user -u clipboard-relay.service -f
```

To restart the service after code changes:

```bash
systemctl --user restart clipboard-relay.service
```

To stop and remove it:

```bash
systemctl --user disable --now clipboard-relay.service
rm ~/.config/systemd/user/clipboard-relay.service
systemctl --user daemon-reload
systemctl --user reset-failed
```

## Step 4: Common errors and how to fix them

### `XDG_RUNTIME_DIR is invalid or not set`
This usually happens when the service cannot access your Wayland session.

Use a user `systemd` service and add the needed environment values.

Open the service file:

```bash
nano ~/.config/systemd/user/clipboard-relay.service
```

Use this content:

```ini
[Unit]
Description=Clipboard Relay Server
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server
ExecStart=/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server/run_server.sh
Restart=always
RestartSec=3
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=WAYLAND_DISPLAY=wayland-0
Environment=CLIPBOARD_SERVER_HOST=0.0.0.0
Environment=CLIPBOARD_SERVER_PORT=5000
Environment=CLIPBOARD_SERVER_USE_WAITRESS=1
Environment=CLIPBOARD_SERVER_THREADS=4

[Install]
WantedBy=default.target
```

Then reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart clipboard-relay.service
journalctl --user -u clipboard-relay.service -f
```

You can confirm your values with:

```bash
echo $XDG_RUNTIME_DIR
echo $WAYLAND_DISPLAY
id -u
```

### `Failed to connect to a Wayland server`
This is usually the same issue as above. The service is running outside the graphical user session. Running it with `systemctl --user` usually fixes it.

### `Refused to connect`
Check these:
- the service is running
- the phone and laptop are on the same Wi‑Fi
- you are opening `http://YOUR-PC-IP:5000`
- your firewall allows port `5000`

Example:

```bash
sudo ufw allow 5000/tcp
```

### Clipboard shows nothing
Make sure your PC clipboard really contains text or an image. Also remember that clipboard behavior may differ between X11 and Wayland.

## Final thought

This project came from a real everyday problem. I wanted a simple way to share clipboard image and text from Linux to Android without relying on a closed ecosystem or heavy third-party tools. The result is lightweight, local, and practical.

If you use Linux and want the same freedom, this setup is a good place to start.
