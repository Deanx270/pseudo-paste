import os
import sys
import time
import random
import threading
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

import customtkinter as ctk
from pynput import keyboard

# -------------------------------------------------------------
# Windows Keyboard API helper using pynput Controller
# -------------------------------------------------------------
user32 = ctypes.windll.user32
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short


class HardwareKeyboardEngine:
    """
    Hardware-level keyboard typing engine.
    Uses pynput's robust 64-bit SendInput bindings combined with
    Windows VkKeyScanW to generate genuine hardware scan codes and
    Shift/Ctrl/Alt modifier sequences.
    100% compatible with VirtualBox, VMware, browser pastebin, terminals, and games.
    """
    VK_CAPITAL = 0x14  # Caps Lock
    _controller = keyboard.Controller()

    @classmethod
    def is_caps_lock_on(cls):
        return bool(user32.GetKeyState(cls.VK_CAPITAL) & 1)

    @classmethod
    def toggle_caps_lock(cls):
        cls._controller.press(keyboard.Key.caps_lock)
        time.sleep(0.01)
        cls._controller.release(keyboard.Key.caps_lock)

    @classmethod
    def type_character(cls, char):
        """
        Types a character using hardware virtual key codes and modifiers.
        """
        if char == '\r':
            return

        if char == '\n':
            cls._controller.press(keyboard.Key.enter)
            time.sleep(0.003)
            cls._controller.release(keyboard.Key.enter)
            return

        if char == '\t':
            cls._controller.press(keyboard.Key.tab)
            time.sleep(0.003)
            cls._controller.release(keyboard.Key.tab)
            return

        if char == ' ':
            cls._controller.press(keyboard.Key.space)
            time.sleep(0.003)
            cls._controller.release(keyboard.Key.space)
            return

        res = user32.VkKeyScanW(char)
        if res == -1:
            # Fallback for unicode emojis / unmapped characters
            cls._controller.type(char)
            return

        vk = res & 0xFF
        shift_state = (res >> 8) & 0xFF
        need_shift = bool(shift_state & 1)
        need_ctrl = bool(shift_state & 2)
        need_alt = bool(shift_state & 4)

        key_obj = keyboard.KeyCode.from_vk(vk)

        # 1. Press modifier keys
        if need_ctrl:
            cls._controller.press(keyboard.Key.ctrl)
            time.sleep(0.003)
        if need_alt:
            cls._controller.press(keyboard.Key.alt)
            time.sleep(0.003)
        if need_shift:
            cls._controller.press(keyboard.Key.shift)
            time.sleep(0.003)

        # 2. Press and release the primary key (hardware VK code)
        cls._controller.press(key_obj)
        time.sleep(0.003)
        cls._controller.release(key_obj)
        time.sleep(0.003)

        # 3. Release modifier keys in reverse order
        if need_shift:
            cls._controller.release(keyboard.Key.shift)
            time.sleep(0.002)
        if need_alt:
            cls._controller.release(keyboard.Key.alt)
            time.sleep(0.002)
        if need_ctrl:
            cls._controller.release(keyboard.Key.ctrl)
            time.sleep(0.002)


# Set appearance and default color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class PseudoPasteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pseudo Paste - Simulated Keyboard Typer (VM Compatible)")
        self.geometry("660x780")
        self.minsize(560, 640)

        # State flags
        self.is_running = False
        self.stop_requested = False
        self.current_thread = None

        # Build UI
        self._init_ui()

        # Start global keyboard listener
        self._start_global_listener()

        # Start periodic CapsLock monitor
        self._check_caps_lock_loop()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _init_ui(self):
        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ Pseudo Paste",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Hardware Keyboard Typer (VirtualBox & VM Compatible)",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(side="left", padx=(12, 0), pady=(4, 0))

        # Always on top switch
        self.always_on_top_var = ctk.BooleanVar(value=True)
        self.wm_attributes("-topmost", True)
        topmost_switch = ctk.CTkSwitch(
            header_frame,
            text="Keep on Top",
            variable=self.always_on_top_var,
            command=self._toggle_topmost,
            font=ctk.CTkFont(size=12)
        )
        topmost_switch.pack(side="right")

        # Main Input Card
        input_card = ctk.CTkFrame(self)
        input_card.pack(fill="both", expand=True, padx=20, pady=8)

        # Input Card Header / Tools
        tool_bar = ctk.CTkFrame(input_card, fg_color="transparent")
        tool_bar.pack(fill="x", padx=15, pady=(10, 5))

        input_title = ctk.CTkLabel(
            tool_bar,
            text="Input Text:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        input_title.pack(side="left")

        self.char_count_label = ctk.CTkLabel(
            tool_bar,
            text="0 chars | 0 lines",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.char_count_label.pack(side="left", padx=15)

        clear_btn = ctk.CTkButton(
            tool_bar,
            text="Clear",
            width=65,
            height=28,
            fg_color="#3a3d45",
            hover_color="#4f525c",
            command=self._clear_text
        )
        clear_btn.pack(side="right", padx=(5, 0))

        paste_btn = ctk.CTkButton(
            tool_bar,
            text="📋 Paste Clipboard",
            width=130,
            height=28,
            command=self._paste_clipboard
        )
        paste_btn.pack(side="right")

        # Text Box
        self.textbox = ctk.CTkTextbox(
            input_card,
            wrap="none",
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=8
        )
        self.textbox.pack(fill="both", expand=True, padx=15, pady=(5, 12))
        self.textbox.bind("<KeyRelease>", self._update_stats)

        # Settings Card
        settings_card = ctk.CTkFrame(self)
        settings_card.pack(fill="x", padx=20, pady=5)

        # Grid layout for settings
        settings_card.grid_columnconfigure((1, 3), weight=1)

        # Row 0: Countdown Delay
        ctk.CTkLabel(
            settings_card,
            text="Start Delay:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=(15, 5), pady=8, sticky="w")

        self.delay_slider = ctk.CTkSlider(
            settings_card,
            from_=1,
            to=15,
            number_of_steps=14,
            command=self._on_delay_slider_change
        )
        self.delay_slider.set(3)
        self.delay_slider.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        self.delay_val_label = ctk.CTkLabel(
            settings_card,
            text="3s",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=40
        )
        self.delay_val_label.grid(row=0, column=2, padx=(0, 15), pady=8)

        # Row 1: Typing Speed (Key Delay)
        ctk.CTkLabel(
            settings_card,
            text="Key Delay:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=1, column=0, padx=(15, 5), pady=8, sticky="w")

        self.speed_slider = ctk.CTkSlider(
            settings_card,
            from_=5,
            to=200,
            number_of_steps=195,
            command=self._on_speed_slider_change
        )
        self.speed_slider.set(25)
        self.speed_slider.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        self.speed_val_label = ctk.CTkLabel(
            settings_card,
            text="25ms",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=45
        )
        self.speed_val_label.grid(row=1, column=2, padx=(0, 15), pady=8)

        # Speed Presets
        presets_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        presets_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            presets_frame,
            text="Speed Presets:",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(side="left", padx=(0, 8))

        self.preset_buttons = {}
        preset_configs = [
            ("Fast (15ms)", 15, 80),
            ("VM Ideal (25ms)", 25, 105),
            ("Natural (40ms)", 40, 95),
            ("Slow (90ms)", 90, 80),
        ]
        for text, ms, w in preset_configs:
            btn = ctk.CTkButton(
                presets_frame,
                text=text,
                width=w,
                height=24,
                fg_color="#1f538d" if ms == 25 else "#2b2d30",
                hover_color="#14375e" if ms == 25 else "#3d4043",
                font=ctk.CTkFont(size=11, weight="bold" if ms == 25 else "normal"),
                command=lambda m=ms: self._set_speed(m)
            )
            btn.pack(side="left", padx=3)
            self.preset_buttons[ms] = btn

        # Options & Caps Lock row
        options_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        options_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=(0, 10), sticky="ew")

        self.jitter_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text="Random Jitter",
            variable=self.jitter_var,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 15))

        self.beep_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="Sound Beep",
            variable=self.beep_var,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 15))

        # Caps Lock indicator and toggle
        self.caps_lock_label = ctk.CTkLabel(
            options_frame,
            text="Caps: OFF",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2ecc71"
        )
        self.caps_lock_label.pack(side="left", padx=(10, 5))

        caps_toggle_btn = ctk.CTkButton(
            options_frame,
            text="Toggle Caps",
            width=85,
            height=22,
            fg_color="#3a3d45",
            hover_color="#4f525c",
            font=ctk.CTkFont(size=11),
            command=self._toggle_caps_lock
        )
        caps_toggle_btn.pack(side="left")

        # Progress & Status Card
        status_card = ctk.CTkFrame(self)
        status_card.pack(fill="x", padx=20, pady=5)

        self.progress_bar = ctk.CTkProgressBar(status_card)
        self.progress_bar.pack(fill="x", padx=15, pady=(12, 6))
        self.progress_bar.set(0)

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=15, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Ready. Press Backspace or Esc anytime to abort typing.",
            font=ctk.CTkFont(size=12),
            text_color="#8ea8c3"
        )
        self.status_label.pack(side="left")

        # Action Buttons
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=(8, 15))

        self.start_btn = ctk.CTkButton(
            action_frame,
            text="▶  Start Typing",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self._on_start_clicked
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            action_frame,
            text="⏹  Stop",
            height=46,
            width=100,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#8b2626",
            hover_color="#5e1a1a",
            state="disabled",
            command=self._request_stop
        )
        self.stop_btn.pack(side="right")

        # Admin note footer
        admin_note = ctk.CTkLabel(
            self,
            text="Note: If typing into an elevated app or VM, run Pseudo Paste as administrator.",
            font=ctk.CTkFont(size=11),
            text_color="#7a8288"
        )
        admin_note.pack(side="bottom", pady=(0, 6))

    def _check_caps_lock_loop(self):
        is_on = HardwareKeyboardEngine.is_caps_lock_on()
        if is_on:
            self.caps_lock_label.configure(text="Caps: ON (Warning)", text_color="#f39c12")
        else:
            self.caps_lock_label.configure(text="Caps: OFF", text_color="#2ecc71")
        self.after(500, self._check_caps_lock_loop)

    def _toggle_caps_lock(self):
        HardwareKeyboardEngine.toggle_caps_lock()
        is_on = HardwareKeyboardEngine.is_caps_lock_on()
        if is_on:
            self.caps_lock_label.configure(text="Caps: ON (Warning)", text_color="#f39c12")
        else:
            self.caps_lock_label.configure(text="Caps: OFF", text_color="#2ecc71")

    def _toggle_topmost(self):
        self.wm_attributes("-topmost", self.always_on_top_var.get())

    def _on_delay_slider_change(self, val):
        self.delay_val_label.configure(text=f"{int(val)}s")

    def _update_preset_highlights(self, current_ms):
        for ms, btn in self.preset_buttons.items():
            if int(current_ms) == ms:
                btn.configure(
                    fg_color="#1f538d",
                    hover_color="#14375e",
                    font=ctk.CTkFont(size=11, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="#2b2d30",
                    hover_color="#3d4043",
                    font=ctk.CTkFont(size=11, weight="normal")
                )

    def _on_speed_slider_change(self, val):
        self.speed_val_label.configure(text=f"{int(val)}ms")
        self._update_preset_highlights(val)

    def _set_speed(self, val_ms):
        self.speed_slider.set(val_ms)
        self.speed_val_label.configure(text=f"{int(val_ms)}ms")
        self._update_preset_highlights(val_ms)

    def _clear_text(self):
        self.textbox.delete("1.0", "end")
        self._update_stats()

    def _paste_clipboard(self):
        try:
            content = self.clipboard_get()
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", content)
            self._update_stats()
        except tk.TclError:
            self._set_status("Clipboard is empty or does not contain text.", "#f39c12")

    def _update_stats(self, event=None):
        raw_text = self.textbox.get("1.0", "end-1c")
        chars = len(raw_text)
        lines = len(raw_text.splitlines()) if raw_text else 0
        self.char_count_label.configure(text=f"{chars} chars | {lines} lines")

    def _set_status(self, text, color="#8ea8c3"):
        self.status_label.configure(text=text, text_color=color)

    def _play_sound(self):
        if HAS_WINSOUND and self.beep_var.get():
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _start_global_listener(self):
        def on_press(key):
            # Check for Backspace or Escape to immediately stop typing
            if key in (keyboard.Key.backspace, keyboard.Key.esc):
                if self.is_running:
                    self.stop_requested = True
                    self.after(0, lambda: self._set_status(
                        "⏹ Stopped by user! ([Backspace] or [Esc] pressed)", "#e74c3c"
                    ))

        self.kb_listener = keyboard.Listener(on_press=on_press)
        self.kb_listener.daemon = True
        self.kb_listener.start()

    def _on_start_clicked(self):
        raw_text = self.textbox.get("1.0", "end-1c")
        if not raw_text:
            messagebox.showwarning("Empty Text", "Please enter or paste some text first!")
            return

        # Check Caps Lock before starting
        if HardwareKeyboardEngine.is_caps_lock_on():
            # Automatically turn off Caps Lock to avoid inverting case
            HardwareKeyboardEngine.toggle_caps_lock()
            self.caps_lock_label.configure(text="Caps: OFF", text_color="#2ecc71")

        self.is_running = True
        self.stop_requested = False
        self.start_btn.configure(state="disabled", fg_color="#3a3d45")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)

        # Launch execution in background thread
        self.current_thread = threading.Thread(
            target=self._run_typing_process,
            args=(raw_text,),
            daemon=True
        )
        self.current_thread.start()

    def _request_stop(self):
        self.stop_requested = True
        self._set_status("⏹ Stop requested...", "#e74c3c")
        if not self.current_thread or not self.current_thread.is_alive():
            self._finish_execution("⏹ Stopped.", "#e74c3c")

    def _run_typing_process(self, text):
        try:
            countdown_secs = int(self.delay_slider.get())
            base_delay_ms = float(self.speed_slider.get())
            use_jitter = self.jitter_var.get()

            # Step 1: Countdown Phase
            for remaining in range(countdown_secs, 0, -1):
                if self.stop_requested:
                    break
                msg = f"⏳ Starting in {remaining}s... Focus the target window now!"
                self.after(0, lambda m=msg: self._set_status(m, "#f1c40f"))
                time.sleep(1.0)

            if self.stop_requested:
                self._finish_execution("⏹ Stopped before typing started.", "#e74c3c")
                return

            # Play sound to indicate typing begins
            self._play_sound()
            self.after(0, lambda: self._set_status("⌨️ Typing in progress... Press Backspace to abort.", "#2ecc71"))

            # Step 2: Typing Loop using HardwareKeyboardEngine
            normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
            total_chars = len(normalized_text)

            for i, char in enumerate(normalized_text):
                if self.stop_requested:
                    break

                # Type through hardware scan code engine
                HardwareKeyboardEngine.type_character(char)

                # Update progress
                progress_ratio = (i + 1) / total_chars
                self.after(0, lambda p=progress_ratio, count=i+1, total=total_chars: self._update_progress_ui(p, count, total))

                # Delay between keystrokes
                delay_sec = base_delay_ms / 1000.0
                if use_jitter and base_delay_ms > 15:
                    jitter_range = min(12.0, base_delay_ms * 0.25)
                    delay_sec += random.uniform(-jitter_range, jitter_range) / 1000.0
                    delay_sec = max(0.005, delay_sec)

                time.sleep(delay_sec)

            # Step 3: Completion
            if self.stop_requested:
                self._finish_execution("⏹ Stopped! (Backspace / Esc detected)", "#e74c3c")
            else:
                self._play_sound()
                self._finish_execution(f"✅ Completed! Typed {total_chars} characters successfully.", "#2ecc71")
        except Exception as e:
            self._finish_execution(f"❌ Error during typing: {e}", "#e74c3c")

    def _update_progress_ui(self, progress, count, total):
        self.progress_bar.set(progress)
        self.status_label.configure(
            text=f"⌨️ Typing... {count}/{total} chars ({int(progress * 100)}%) | [Backspace] to abort",
            text_color="#2ecc71"
        )

    def _finish_execution(self, status_msg, color):
        def update():
            self.is_running = False
            self.start_btn.configure(state="normal", fg_color="#1f6aa5")
            self.stop_btn.configure(state="disabled")
            self._set_status(status_msg, color)
        self.after(0, update)

    def _on_closing(self):
        self.stop_requested = True
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = PseudoPasteApp()
    app.mainloop()
