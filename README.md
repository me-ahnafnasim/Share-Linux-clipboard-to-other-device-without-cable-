# Share-Linux-clipboard-to-other-devices-without-cable


## What This Project Does

This project lets you copy an image on a Linux laptop and open that same image on an Android phone over the same local Wi-Fi network.

The current implementation has two main parts:

- A Linux Flask server that reads the current clipboard image from X11 or Wayland.
- A mobile-friendly web client that opens on Android in Chrome and fetches the latest clipboard image.

When the clipboard contains an image, the server converts it to PNG and exposes it through HTTP. The Android side then opens the web interface and downloads or previews that image.

## Motivation

The goal of this project is to make image transfer from Linux to Android lightweight and fast without:

- USB cables
- cloud upload
- messaging apps
- desktop sync services
- a custom Android APK as a hard requirement

It is useful when you copy screenshots, design references, diagrams, or cropped images on your laptop and want them immediately on your phone.

## Current Architecture

### Linux Side

The Linux server lives in [clipboard_server.py](/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server/clipboard_server.py).

It does the following:

- detects whether the desktop session is Wayland or X11
- reads clipboard image data using `wl-paste` or `xclip`
- converts non-PNG clipboard images to PNG with Pillow
- serves a built-in web UI on port `5000`
- exposes `/api/image` and `/api/status`

### Android Side

The Android-facing web client can be used in two ways:

- directly from the Flask server by opening `http://<laptop-ip>:5000`
- from the standalone static client in [apps/android-web-client](/home/ahnaf-nasim/Pictures/git-pratice/apps/android-web-client)

The web client lets the user:

- fetch the latest clipboard image
- preview it
- download it
- add the page to the home screen in Chrome

## How To Start The Project

### 1. Go to the Linux server folder

```bash
cd /home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server
```

### 2. Install dependencies

Run:

```bash
chmod +x setup.sh
./setup.sh
```

This sets up:

- Python virtual environment
- Flask
- Pillow
- clipboard tools for X11 and Wayland
- firewall rule for port `5000` when supported

### 3. Start the server

Run:

```bash
./.venv/bin/python clipboard_server.py
```

If it starts correctly, you should see output similar to:

```text
Running on http://127.0.0.1:5000
Running on http://<your-laptop-ip>:5000
```

### 4. Find the laptop IP address

Run:

```bash
hostname -I
```

Example:

```text
10.176.148.209
```

### 5. Open it on Android

On the Android phone, open Chrome and go to:

```text
http://<your-laptop-ip>:5000
```

Example:

```text
http://10.176.148.209:5000
```

Important:

- use `http://`, not `https://`
- the phone and laptop must be on the same Wi-Fi network
- the clipboard on Linux must contain an image, not text

## Recommended Daily Workflow

1. Copy an image on your Linux laptop.
2. Make sure the Flask server is already running.
3. Open the project URL on Android.
4. Tap `Fetch Image`.
5. Preview or download the image.

## What Happens Internally

When you tap `Fetch Image`:

1. the browser calls `GET /api/image`
2. the Flask server reads the Linux clipboard
3. the clipboard image is converted to PNG if needed
4. the image is returned with no-cache headers
5. the Android browser displays the latest image

## Important Notes

- This is intended for local network use only.
- Do not expose port `5000` to the public internet.
- The Flask server is a development server, which is acceptable for local personal use but not for public deployment.
- If Android shows `refused to connect`, the server is not running, the IP is wrong, or the firewall is blocking port `5000`.
- If Flask logs a TLS or `Bad request version` error, Android is trying `https://` instead of `http://`.

## Troubleshooting

### Android cannot connect

Check:

```bash
sudo ufw allow 5000/tcp
hostname -I
```

Then open:

```text
http://<laptop-ip>:5000
```

### Android says image not found

That usually means the Linux clipboard is empty or contains text instead of an image.

Copy an image again and retry.

### Wayland clipboard does not work

Check:

```bash
command -v wl-paste
```

### X11 clipboard does not work

Check:

```bash
command -v xclip
```

## Project Files

- [README.md](/home/ahnaf-nasim/Pictures/git-pratice/README.md): main setup and usage instructions
- [PROJECT_GUIDE.md](/home/ahnaf-nasim/Pictures/git-pratice/PROJECT_GUIDE.md): high-level project explanation
- [clipboard_server.py](/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server/clipboard_server.py): Linux backend and built-in web UI
- [setup.sh](/home/ahnaf-nasim/Pictures/git-pratice/apps/linux-clipboard-server/setup.sh): dependency installer and firewall helper
- [apps/android-web-client](/home/ahnaf-nasim/Pictures/git-pratice/apps/android-web-client): standalone web client

## Current Limitation

The current Android path is browser-based, so it previews and downloads images rather than placing them directly into the Android system clipboard as image data. That would require a native Android client.
