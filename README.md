# Queue Sniper

A dark-themed desktop app that monitors Discord channels for Minecraft queue / tester messages and reacts automatically (button click, reaction, or join command).

> **Warning:** Uses a **Discord user token** (self-bot). This **violates Discord Terms of Service** and can **ban your account**. Use a throwaway account only.

**Supported platforms:** Linux Mint (and most Debian/Ubuntu desktops), Windows 10/11.

---

## Features

- Modern dark GUI (CustomTkinter)
- Discord token: paste manually or auto-detect (Discord app / Chrome / Chromium)
- Monitor multiple channel IDs
- Keyword triggers (`tester`, `queue open`, `now testing`, …)
- Optional tester user ID monitoring
- Auto button click, reaction, or custom join command
- Patience mode (0.3–1.5s random delay)
- Desktop notifications and sound alert
- System tray (minimize, show/hide, quit)
- Saves settings to `config.json`
- Launch at login (autostart)
- Headless mode (hide window while running)

---

## Clone from GitHub

```bash
git clone https://github.com/YOUR_USERNAME/Queue-Sniper.git
cd Queue-Sniper
```

Replace `YOUR_USERNAME` with your GitHub username after you publish the repo.

---

## Install on Linux Mint

### 1. System packages

Open a terminal and install Python and libraries used by the GUI and notifications:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv python3-tk \
  libnotify-bin \
  gir1.2-appindicator3-0.1 \
  libayatana-appindicator3-1
```

Optional (for sound alerts):

```bash
sudo apt install -y pulseaudio-utils alsa-utils
```

### 2. Python virtual environment

```bash
cd ~/Queue-Sniper
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the app

```bash
source .venv/bin/activate
python3 main.py
```

### 4. Desktop shortcut (optional)

```bash
chmod +x scripts/run.sh   # if you add a launcher script
```

Or create a menu entry pointing to:

```text
/home/YOU/Queue-Sniper/.venv/bin/python3 /home/YOU/Queue-Sniper/main.py
```

---

## Install on Windows

### 1. Install Python 3.11+

Download from [python.org](https://www.python.org/downloads/) and check **Add Python to PATH**.

### 2. Virtual environment

```powershell
cd C:\path\to\Queue-Sniper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements-windows.txt
```

(`requirements-windows.txt` includes `pywin32` for startup shortcuts.)

### 3. Run

```powershell
python main.py
```

---

## How to use

### First-time setup

1. **Start the app** (`python3 main.py` on Linux, `python main.py` on Windows).
2. **Discord token**
   - Paste your token in **DISCORD SESSION TOKEN**, or  
   - Click **AUTO-DETECT SESSION TOKEN** (Discord desktop or browser must be logged in on this machine).
3. **Add channels**
   - Click **+ ADD**
   - Enter a name (e.g. `Minecraft UHC Community`) and the **channel ID**.
4. **Detection** (settings panel, scroll if needed)
   - Keywords: comma-separated, e.g. `tester, testing, queue open, now testing`
   - Tester user IDs (optional): comma-separated numeric IDs
5. **Auto action** (optional)
   - Reaction emoji (e.g. `✅`) or leave empty for auto-try
   - Join command (e.g. `!join`) if no button is found on the message
6. Click **START** — status should show **MONITORING** when connected.

### Getting a Discord channel ID

1. Discord → **User Settings** → **Advanced** → enable **Developer Mode**
2. Right-click the channel → **Copy Channel ID**

### When a tester is detected

The bot will (after patience delay, if enabled):

1. Try to click a Join/Queue button on the message  
2. Or react with your emoji  
3. Or send your join command  

You get a desktop notification and sound (if enabled).

### Other options

| Option | Description |
|--------|-------------|
| **Patience mode** | Random 0.3–1.5s delay before acting |
| **Desktop notifications** | OS notification on detect |
| **Sound alert** | Beep / system sound |
| **Headless mode** | Hides window when you press START |
| **Launch at login** | Linux: `~/.config/autostart/` · Windows: Startup folder |
| **Minimize to tray** | Runs in system tray; use tray menu to show or quit |
| **Clear** | Clears the activity log |

### Stop

Click **STOP** or quit from the tray menu.

---

## Configuration file

Settings are stored in `config.json` in the project folder (created on first save).

| Key | Description |
|-----|-------------|
| `token` | Discord user token — **keep secret, never commit to GitHub** |
| `channels` | `[{"name": "...", "channel_id": "123..."}]` |
| `tester_keywords` | List of trigger words |
| `tester_user_ids` | List of Discord user IDs |
| `react_emoji` | Emoji for reactions |
| `join_command` | Message to send if no button |
| `patience_mode` | `true` / `false` |
| `patience_min` / `patience_max` | Delay range in seconds |
| `notifications_enabled` | Desktop notifications |
| `sound_enabled` | Sound on detect |
| `headless` | Hide window while running |
| `launch_on_startup` | Autostart at login |

Add to `.gitignore` (already recommended):

```gitignore
config.json
.venv/
__pycache__/
dist/
build/
*.spec
```

---

## Troubleshooting (Linux Mint)

| Problem | Fix |
|---------|-----|
| `No module named 'tkinter'` | `sudo apt install python3-tk` |
| GUI does not start | `sudo apt install python3-tk customtkinter deps` — reinstall venv and `pip install -r requirements.txt` |
| No desktop notifications | `sudo apt install libnotify-bin` — log out/in |
| Tray icon missing | `sudo apt install gir1.2-appindicator3-0.1 libayatana-appindicator3-1` |
| Auto-detect finds no token | Log into Discord in the desktop app or Chrome; or paste token manually |
| `discord.py-self` install fails | Use Python 3.11 or 3.12: `python3.11 -m venv .venv` |
| Invalid token / login failed | Token expired or copied wrong — get a new token |

---

## Build standalone executable

### Linux

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed \
  --name QueueSniper \
  --add-data "assets:assets" \
  main.py
```

Binary: `dist/QueueSniper`

### Windows

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed `
  --name QueueSniper `
  --add-data "assets;assets" `
  main.py
```

Binary: `dist\QueueSniper.exe`

---

## Project structure

```text
Queue-Sniper/
├── main.py                 # GUI
├── bot.py                  # Discord monitor
├── config.py               # config.json
├── utils.py                # token, tray, notifications, autostart
├── requirements.txt        # Linux / cross-platform
├── requirements-windows.txt
├── README.md
└── assets/
    └── icon.png            # auto-created if missing
```

---

## Legal / safety

- Never share your token or upload `config.json` to GitHub.
- Do not use on your main Discord account.
- Server rules may forbid automation even if the tool works technically.

## License

Educational / personal use only. No warranty.
