"""
Queue Sniper — Main GUI application.

Minecraft queue monitoring via Discord self-bot session.
See README.md for installation, ToS warnings, and PyInstaller build steps.
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from typing import Any, Callable, Optional

import customtkinter as ctk

from bot import QueueSniperBot
from config import ConfigManager
from utils import (
    create_tray_icon,
    detect_discord_token,
    ensure_icon_asset,
    play_alert_sound,
    set_windows_startup,
    show_desktop_notification,
)

APP_NAME = "Queue Sniper"
APP_TAGLINE = "Minecraft queue monitor"

COLOR_BG = "#0f0f0f"
COLOR_BG_ALT = "#121212"
COLOR_SURFACE = "#1a1a1a"
COLOR_SURFACE_ALT = "#242424"
COLOR_BORDER = "#2d2d2d"
COLOR_TEXT = "#e8e8e8"
COLOR_TEXT_MUTED = "#8a8a8a"
COLOR_ACCENT = "#3b82f6"
COLOR_ACCENT_DIM = "#1e3a5f"
COLOR_DANGER = "#ef4444"
COLOR_SUCCESS = "#22c55e"
COLOR_WARN = "#f59e0b"
COLOR_START = "#ffffff"
COLOR_START_TEXT = "#0f0f0f"
COLOR_STOP = "#3a3a3a"
COLOR_STOP_TEXT = "#c0c0c0"
COLOR_STOP_HOVER = "#4a4a4a"

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_TAG = (FONT_FAMILY, 10)
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 10)
FONT_STATUS = (FONT_FAMILY, 14, "bold")
FONT_BUTTON = (FONT_FAMILY, 13, "bold")


class BotController:
    def __init__(
        self,
        on_log: Callable[[str], None],
        on_status: Callable[[str, str], None],
        on_tester: Callable[[], None],
    ) -> None:
        self._on_log = on_log
        self._on_status = on_status
        self._on_tester = on_tester
        self._running = False
        self._bot: Optional[QueueSniperBot] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, config: dict[str, Any]) -> None:
        if self._running:
            return
        token = (config.get("token") or "").strip()
        if not token:
            self._on_log("[ERROR] Discord session token is required.")
            self._on_status("OFFLINE", "Not logged in")
            return
        channels = [
            ch for ch in (config.get("channels") or []) if str(ch.get("channel_id", "")).strip()
        ]
        if not channels:
            self._on_log("[WARN] No channel IDs configured.")
            self._on_status("OFFLINE", "No channels")
            return
        self._running = True
        self._on_status("CONNECTING", "Signing in…")
        self._on_log("[INFO] Starting Discord monitor…")
        cfg = dict(config)
        cfg["channels"] = channels
        self._bot = QueueSniperBot(
            config=cfg,
            on_log=self._on_log,
            on_status=self._on_status,
            on_tester=self._on_tester,
        )
        def _run() -> None:
            try:
                assert self._bot is not None
                self._bot.run()
            finally:
                self._running = False

        threading.Thread(target=_run, name="QueueSniperBot", daemon=True).start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._bot:
            try:
                self._bot.stop()
            except Exception:
                pass
        self._on_log("[INFO] Monitor stopped.")
        self._on_status("OFFLINE", "Not logged in")


class AddChannelDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, on_add: Callable[[str, str], None]) -> None:
        super().__init__(parent)
        self.title("Add Channel")
        self.geometry("440x240")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent)
        self.grab_set()
        self._on_add = on_add
        ctk.CTkLabel(self, text="Server / community name", font=FONT_SECTION).pack(
            anchor="w", padx=24, pady=(20, 4)
        )
        self.name_entry = ctk.CTkEntry(self, height=36, fg_color=COLOR_SURFACE)
        self.name_entry.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkLabel(self, text="Discord channel ID", font=FONT_SECTION).pack(
            anchor="w", padx=24, pady=(0, 4)
        )
        self.id_entry = ctk.CTkEntry(self, height=36, fg_color=COLOR_SURFACE)
        self.id_entry.pack(fill="x", padx=24, pady=(0, 14))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24)
        ctk.CTkButton(row, text="Cancel", width=100, fg_color=COLOR_STOP, command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(row, text="Add", width=100, fg_color=COLOR_ACCENT, command=self._submit).pack(
            side="right"
        )

    def _submit(self) -> None:
        name, cid = self.name_entry.get().strip(), self.id_entry.get().strip()
        if name and cid:
            self._on_add(name, cid)
            self.destroy()


class QueueSniperApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ensure_icon_asset()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(APP_NAME)
        self.geometry("1020x700")
        self.minsize(920, 620)
        self.configure(fg_color=COLOR_BG)
        self._cfg = ConfigManager()
        self._bot = BotController(self._append_log, self._set_status, self._on_tester_detected)
        self._tray_icon = None
        self._settings_visible = True
        self._channel_count_label: Optional[ctk.CTkLabel] = None
        self._build_ui()
        self._load_config_into_ui()
        self._append_log("[INFO] Queue Sniper ready.")
        self._append_log("[WARN] Self-bots violate Discord ToS — account ban risk.")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self._build_header()
        self._build_tos_strip()
        self._build_body()
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLOR_BG_ALT, height=64, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=10)
        brand = ctk.CTkFrame(inner, fg_color="transparent")
        brand.pack(side="left")
        ctk.CTkLabel(brand, text="👻", font=(FONT_FAMILY, 26)).pack(side="left", padx=(0, 12))
        titles = ctk.CTkFrame(brand, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text=APP_NAME, font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(titles, text=APP_TAGLINE, font=FONT_TAG, text_color=COLOR_TEXT_MUTED).pack(
            anchor="w"
        )
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        self._channel_count_label = ctk.CTkLabel(
            right, text="0 channels", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED
        )
        self._channel_count_label.pack(side="right", padx=(0, 12))
        ctk.CTkButton(
            right,
            text="⚙",
            width=42,
            height=42,
            font=(FONT_FAMILY, 22),
            fg_color=COLOR_SURFACE,
            command=self._toggle_settings_panel,
        ).pack(side="right")

    def _build_tos_strip(self) -> None:
        strip = ctk.CTkFrame(self, fg_color=COLOR_ACCENT_DIM, height=32, corner_radius=0)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        ctk.CTkLabel(
            strip,
            text="⚠  Discord self-bots may ban your account. Use a throwaway account.",
            font=FONT_SMALL,
            text_color="#93c5fd",
        ).pack(side="left", padx=16)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=6)
        body.grid_rowconfigure(0, weight=1)
        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        left = ctk.CTkFrame(
            parent, fg_color=COLOR_SURFACE, corner_radius=14, border_width=1, border_color=COLOR_BORDER
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card = ctk.CTkFrame(
            left, fg_color=COLOR_SURFACE_ALT, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        card.pack(fill="x", padx=16, pady=(16, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(top, text="STATUS", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.status_dot = ctk.CTkLabel(top, text="●", text_color=COLOR_DANGER)
        self.status_dot.pack(side="right")
        self.status_label = ctk.CTkLabel(card, text="OFFLINE", font=FONT_STATUS, text_color=COLOR_DANGER)
        self.status_label.pack(anchor="w", padx=14)
        self.status_sub_label = ctk.CTkLabel(
            card, text="Not logged in", font=FONT_BODY, text_color=COLOR_TEXT_MUTED
        )
        self.status_sub_label.pack(anchor="w", padx=14, pady=(0, 12))
        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        self.start_btn = ctk.CTkButton(
            btn_row,
            text="START",
            font=FONT_BUTTON,
            height=52,
            fg_color=COLOR_START,
            text_color=COLOR_START_TEXT,
            command=self._on_start,
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.stop_btn = ctk.CTkButton(
            btn_row,
            text="STOP",
            font=FONT_BUTTON,
            height=52,
            fg_color=COLOR_STOP,
            text_color=COLOR_STOP_TEXT,
            command=self._on_stop,
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.stop_btn.configure(state="disabled")
        log_head = ctk.CTkFrame(left, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(4, 6))
        ctk.CTkLabel(log_head, text="ACTIVITY LOG", font=FONT_SECTION, text_color=COLOR_TEXT_MUTED).pack(
            side="left"
        )
        ctk.CTkButton(
            log_head, text="Clear", width=60, height=24, font=FONT_SMALL, command=self._clear_log
        ).pack(side="right")
        self.log_text = ctk.CTkTextbox(
            left,
            font=("Consolas", 10),
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=10,
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.log_text.configure(state="disabled")

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        self.right_panel = ctk.CTkFrame(
            parent, fg_color=COLOR_SURFACE, corner_radius=14, border_width=1, border_color=COLOR_BORDER
        )
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        scroll = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(scroll, text="SETTINGS", font=FONT_SECTION, text_color=COLOR_TEXT_MUTED).pack(
            anchor="w", padx=12, pady=(10, 8)
        )
        self._section(scroll, "DISCORD SESSION TOKEN")
        self.token_entry = ctk.CTkEntry(scroll, show="•", height=40, fg_color=COLOR_SURFACE_ALT)
        self.token_entry.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkButton(
            scroll,
            text="AUTO-DETECT SESSION TOKEN",
            height=36,
            fg_color=COLOR_SURFACE_ALT,
            command=self._on_auto_detect_token,
        ).pack(fill="x", padx=12, pady=(0, 14))
        ch_row = ctk.CTkFrame(scroll, fg_color="transparent")
        ch_row.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(ch_row, text="MONITORED CHANNELS", font=FONT_SECTION).pack(side="left")
        ctk.CTkButton(
            ch_row, text="+ ADD", width=72, height=28, fg_color=COLOR_ACCENT, command=self._open_add_channel
        ).pack(side="right")
        self.channels_frame = ctk.CTkFrame(
            scroll, fg_color=COLOR_SURFACE_ALT, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        self.channels_frame.pack(fill="x", padx=12, pady=(0, 14))
        self._section(scroll, "DETECTION")
        self.keywords_entry = ctk.CTkEntry(scroll, height=36, fg_color=COLOR_SURFACE_ALT)
        self.keywords_entry.pack(fill="x", padx=12, pady=(0, 6))
        self.tester_ids_entry = ctk.CTkEntry(scroll, height=36, fg_color=COLOR_SURFACE_ALT)
        self.tester_ids_entry.pack(fill="x", padx=12, pady=(0, 14))
        self._section(scroll, "AUTO ACTION (optional)")
        self.react_entry = ctk.CTkEntry(scroll, height=36, fg_color=COLOR_SURFACE_ALT)
        self.react_entry.pack(fill="x", padx=12, pady=(0, 6))
        self.join_cmd_entry = ctk.CTkEntry(scroll, height=36, fg_color=COLOR_SURFACE_ALT)
        self.join_cmd_entry.pack(fill="x", padx=12, pady=(0, 14))
        self._section(scroll, "OPTIONS")
        self.patience_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll, text="Patience mode (0.3–1.5s)", variable=self.patience_var, command=self._persist
        ).pack(anchor="w", padx=12, pady=3)
        self.notif_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll, text="Desktop notifications", variable=self.notif_var, command=self._persist
        ).pack(anchor="w", padx=12, pady=3)
        self.sound_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Sound alert", variable=self.sound_var, command=self._persist).pack(
            anchor="w", padx=12, pady=3
        )
        self.headless_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll, text="Headless mode", variable=self.headless_var, command=self._on_headless_toggle
        ).pack(anchor="w", padx=12, pady=(3, 12))

    def _section(self, parent: ctk.CTkFrame, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=FONT_SECTION).pack(anchor="w", padx=12, pady=(4, 6))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=COLOR_BG_ALT, height=44, corner_radius=0)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20)
        self.startup_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner, text="Launch at login (autostart)", variable=self.startup_var, command=self._on_startup_toggle
        ).pack(side="left", pady=8)
        ctk.CTkButton(
            inner, text="Minimize to tray", width=130, height=28, command=self._minimize_to_tray
        ).pack(side="right", pady=8)

    def _refresh_channel_list(self) -> None:
        for w in self.channels_frame.winfo_children():
            w.destroy()
        channels = self._cfg.get("channels") or []
        active = sum(1 for c in channels if str(c.get("channel_id", "")).strip())
        if self._channel_count_label:
            self._channel_count_label.configure(text=f"{active} active / {len(channels)} channel(s)")
        if not channels:
            ctk.CTkLabel(
                self.channels_frame, text="No channels. Click + ADD.", text_color=COLOR_TEXT_MUTED
            ).pack(padx=12, pady=16)
            return
        for idx, ch in enumerate(channels):
            row = ctk.CTkFrame(self.channels_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=6)
            name = ch.get("name", "Unknown")
            cid = str(ch.get("channel_id", "")).strip()
            block = ctk.CTkFrame(row, fg_color="transparent")
            block.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(block, text=name, font=FONT_BODY).pack(anchor="w")
            ctk.CTkLabel(
                block,
                text=f"ID: {cid}" if cid else "No ID set",
                font=FONT_SMALL,
                text_color=COLOR_SUCCESS if cid else COLOR_WARN,
            ).pack(anchor="w")
            ctk.CTkButton(
                row,
                text="✕",
                width=34,
                height=34,
                fg_color="transparent",
                hover_color=COLOR_DANGER,
                command=lambda i=idx: self._remove_channel(i),
            ).pack(side="right")

    def _load_config_into_ui(self) -> None:
        d = self._cfg.data
        if d.get("token"):
            self.token_entry.insert(0, d["token"])
        self.patience_var.set(d.get("patience_mode", True))
        self.notif_var.set(d.get("notifications_enabled", True))
        self.sound_var.set(d.get("sound_enabled", True))
        self.headless_var.set(d.get("headless", False))
        self.startup_var.set(d.get("launch_on_startup", False))
        kws = ", ".join(str(k) for k in d.get("tester_keywords") or [])
        self.keywords_entry.insert(0, kws)
        ids = ", ".join(str(i) for i in d.get("tester_user_ids") or [])
        self.tester_ids_entry.insert(0, ids)
        self.react_entry.insert(0, d.get("react_emoji", "") or "")
        self.join_cmd_entry.insert(0, d.get("join_command", "") or "")
        self._refresh_channel_list()
        self._set_status("OFFLINE", "Not logged in")

    def _persist(self) -> None:
        self._cfg.update(
            {
                "token": self.token_entry.get().strip(),
                "patience_mode": self.patience_var.get(),
                "notifications_enabled": self.notif_var.get(),
                "sound_enabled": self.sound_var.get(),
                "headless": self.headless_var.get(),
                "launch_on_startup": self.startup_var.get(),
                "tester_keywords": [p.strip() for p in self.keywords_entry.get().split(",") if p.strip()],
                "tester_user_ids": [
                    p.strip()
                    for p in self.tester_ids_entry.get().replace(";", ",").split(",")
                    if p.strip().isdigit()
                ],
                "react_emoji": self.react_entry.get().strip(),
                "join_command": self.join_cmd_entry.get().strip(),
            }
        )
        self._cfg.save()

    def _open_add_channel(self) -> None:
        AddChannelDialog(self, self._add_channel)

    def _add_channel(self, name: str, channel_id: str) -> None:
        channels = list(self._cfg.get("channels") or [])
        channels.append({"name": name, "channel_id": channel_id})
        self._cfg.set("channels", channels)
        self._cfg.save()
        self._refresh_channel_list()
        self._append_log(f"[INFO] Added: {name}")

    def _remove_channel(self, index: int) -> None:
        channels = list(self._cfg.get("channels") or [])
        if 0 <= index < len(channels):
            removed = channels.pop(index)
            self._cfg.set("channels", channels)
            self._cfg.save()
            self._refresh_channel_list()
            self._append_log(f"[INFO] Removed: {removed.get('name')}")

    def _on_start(self) -> None:
        self._persist()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._bot.start(self._cfg.data)
        if not self._bot.is_running:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            return
        if self._cfg.get("headless"):
            self._minimize_to_tray()

    def _on_stop(self) -> None:
        self._bot.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _on_auto_detect_token(self) -> None:
        self._append_log("[INFO] Scanning for token…")

        def work() -> None:
            self.after(0, lambda: self._finish_detect(detect_discord_token()))

        threading.Thread(target=work, daemon=True).start()

    def _finish_detect(self, token: Optional[str]) -> None:
        if token:
            self.token_entry.delete(0, "end")
            self.token_entry.insert(0, token)
            self._cfg.set("token", token)
            self._cfg.save()
            self._append_log("[INFO] Token detected.")
        else:
            self._append_log("[WARN] Token not found — paste manually.")

    def _on_tester_detected(self) -> None:
        if self._cfg.get("notifications_enabled", True):
            show_desktop_notification(APP_NAME, "Tester detected!")
        if self._cfg.get("sound_enabled", True):
            play_alert_sound(self._cfg.get("custom_sound_path", "") or "")
        self._append_log("[ALERT] Tester detected!")

    def _on_startup_toggle(self) -> None:
        self._cfg.set("launch_on_startup", self.startup_var.get())
        self._cfg.save()
        set_windows_startup(self.startup_var.get())

    def _on_headless_toggle(self) -> None:
        self._persist()

    def _toggle_settings_panel(self) -> None:
        if self._settings_visible:
            self.right_panel.grid_remove()
            self._settings_visible = False
        else:
            self.right_panel.grid()
            self._settings_visible = True

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _append_log(self, message: str) -> None:
        line = f"[{datetime.now():%H:%M:%S}] {message}\n"

        def write() -> None:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.after(0, write)

    def _set_status(self, status: str, subtitle: str) -> None:
        def update() -> None:
            u = status.upper()
            self.status_label.configure(text=u, text_color=COLOR_DANGER)
            self.status_dot.configure(text_color=COLOR_DANGER)
            if u in ("ONLINE", "CONNECTED", "MONITORING"):
                self.status_label.configure(text_color=COLOR_SUCCESS)
                self.status_dot.configure(text_color=COLOR_SUCCESS)
            elif u == "CONNECTING":
                self.status_label.configure(text_color=COLOR_WARN)
                self.status_dot.configure(text_color=COLOR_WARN)
            self.status_sub_label.configure(text=subtitle)

        self.after(0, update)

    def _setup_tray(self) -> None:
        if self._tray_icon is None:
            try:
                self._tray_icon = create_tray_icon(self._show_from_tray, self._quit_app)
            except Exception as exc:
                self._append_log(f"[WARN] Tray: {exc}")

    def _minimize_to_tray(self) -> None:
        self._setup_tray()
        self.withdraw() if self._tray_icon else self.iconify()

    def _show_from_tray(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self) -> None:
        if self._bot.is_running:
            self._bot.stop()
        self._persist()
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def _quit_app(self) -> None:
        self.after(0, self._on_close)


def main() -> None:
    QueueSniperApp().mainloop()


if __name__ == "__main__":
    main()
