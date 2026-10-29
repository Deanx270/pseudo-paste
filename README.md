# Pseudo Paste

A lightweight, hardware-accurate simulated keyboard typing utility for Windows.

Pseudo Paste imitates manual keyboard typing into any target application. It is specifically designed for environments that disable, block, or distort clipboard pasting, including virtual machines (VirtualBox, VMware), remote desktop consoles (RDP, VNC), web terminals, secure forms, and remote shells.

---

## Features

- **Hardware-Level Keystroke Emulation:** Dispatches physical virtual key codes and scan codes rather than simple clipboard text injection. Accurately preserves indentation, colons, spaces, and newlines.
- **Configurable Line Break Delay:** Dedicated slider (0ms to 2000ms) to add pauses before and after newlines, preventing buffer drops, lost characters, or corrupted indentation in terminals, shells, and virtual machines.
- **Adjustable Typing Speed:** Fine-tune key delay (5ms to 200ms) with presets (Fast, VM Ideal, Natural, Slow).
- **Editor Shortcuts:** Full support for `Ctrl + Backspace` in the input field to delete entire words effortlessly.
- **Global Emergency Stop:** Press `Backspace` or `Esc` on your keyboard from any application to immediately halt typing.
- **Human Jitter Mode:** Optional randomized typing rhythm variation to simulate natural human typing.
- **Caps Lock Detection & Auto-Reset:** Monitors Caps Lock state to prevent case inversion and automatically corrects it prior to typing.
- **Always on Top:** Floating window switch to monitor progress while interacting with other applications.
- **Modern Interface:** Clean, intuitive dark-mode interface built with CustomTkinter.

---

## Getting Started

### Option 1: Standalone Executable (Recommended)
Download `PseudoPaste.exe` from the [Releases](https://github.com/Deanx270/pseudo-paste/releases) page and run it directly. No installation or Python environment is required.

### Option 2: Run from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/Deanx270/pseudo-paste.git
   cd pseudo-paste
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   python pseudo_paste.py
   ```
   *(Or run `run.bat`)*

---

## Usage Tips & Troubleshooting

### Target Window Focus
Set the **Start Delay** (1–15 seconds), click **Start Typing**, and click on your target window (such as your VM or terminal) before the countdown completes.

### Running with Administrator Privileges (UIPI)
Windows enforces User Interface Privilege Isolation (UIPI), which blocks standard applications from sending simulated keystrokes into elevated (Administrator) windows.

If your target application (such as a VirtualBox VM or an administrative command prompt) is running as Administrator, right-click **Pseudo Paste** and select **Run as administrator**.

### Emergency Stop
While typing is in progress, typing can be aborted immediately by:
- Pressing `Backspace` or `Esc` on your keyboard.
- Clicking the red `Stop` button in the Pseudo Paste window.

---

## License

This project is licensed under the [MIT License](LICENSE).
