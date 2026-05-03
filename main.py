#!/usr/bin/env python3
"""
ActionRecorder v1.3 - Record and replay mouse & keyboard actions
- Minimizes while recording/playing (still in taskbar)
- Ctrl+Shift+S hotkey to stop recording or playback anytime
- Auto-focuses the recorded window on playback
"""

import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox
import pyautogui # type: ignore
from pynput import mouse, keyboard # type: ignore
from pynput.keyboard import Controller as KeyboardController, HotKey, Key
from pynput.mouse import Controller as MouseController

try:
    import pygetwindow as gw # type: ignore
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

pyautogui.FAILSAFE = True

# ------------------------------------------------------------
# UI Constants
# ------------------------------------------------------------
UI = {
    'bg':           '#0f0f17',
    'surface':      '#1a1a2e',
    'panel':        '#16213e',
    'border':       '#2a2a4a',
    'fg':           '#e2e2f0',
    'fg_muted':     '#7070a0',
    'accent':       '#7c6cf0',
    'record':       '#e05c5c',
    'record_dim':   '#5a1f1f',
    'play':         '#4caf7d',
    'play_dim':     '#1a4a2e',
    'stop':         '#e0a040',
    'font':         'Segoe UI',
    'mono':         'Consolas',
    'w':            520,
    'h':            540,
}

# ------------------------------------------------------------
# Recorder Engine
# ------------------------------------------------------------
class ActionRecorder:
    def __init__(self):
        self.actions = []
        self.recording = False
        self.playing = False
        self._start_time = None
        self._mouse_listener = None
        self._keyboard_listener = None
        self._kb = KeyboardController()
        self._mouse = MouseController()
        self.active_window = ""
        self._active_window_obj = None

    def _get_active_window(self):
        if HAS_PYGETWINDOW:
            try:
                w = gw.getActiveWindow() # type: ignore
                if w and w.title:
                    self._active_window_obj = w
                    return w.title
            except:
                pass
        self._active_window_obj = None
        return "Unknown"

    def focus_recorded_window(self):
        if not HAS_PYGETWINDOW:
            return
        try:
            if self._active_window_obj:
                self._active_window_obj.activate()
                time.sleep(0.3)
                return
            if self.active_window and self.active_window != "Unknown":
                wins = gw.getWindowsWithTitle(self.active_window) # type: ignore
                if wins:
                    wins[0].activate()
                    time.sleep(0.3)
        except:
            pass

    def start_recording(self):
        self.actions = []
        self.recording = True
        self._start_time = time.time()
        self.active_window = self._get_active_window()

        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop_recording(self):
        self.recording = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

    def _ts(self):
        return time.time() - self._start_time # type: ignore

    def _on_move(self, x, y):
        if self.recording:
            self.actions.append(('move', self._ts(), x, y))

    def _on_click(self, x, y, button, pressed):
        if self.recording:
            self.actions.append(('click', self._ts(), x, y, button, pressed))

    def _on_scroll(self, x, y, dx, dy):
        if self.recording:
            self.actions.append(('scroll', self._ts(), x, y, dx, dy))

    def _on_press(self, key):
        if self.recording:
            self.actions.append(('key_press', self._ts(), key))

    def _on_release(self, key):
        if self.recording:
            self.actions.append(('key_release', self._ts(), key))

    def play(self, repeat=1, speed=1.0, on_done=None):
        if not self.actions:
            return
        self.playing = True

        def _run():
            for _ in range(repeat):
                if not self.playing:
                    break
                prev_time = 0
                for action in self.actions:
                    if not self.playing:
                        break
                    delay = (action[1] - prev_time) / speed
                    if delay > 0:
                        time.sleep(delay)
                    prev_time = action[1]
                    self._replay(action)
            self.playing = False
            if on_done:
                on_done()

        threading.Thread(target=_run, daemon=True).start()

    def _replay(self, action):
        try:
            kind = action[0]
            if kind == 'move':
                self._mouse.position = (action[2], action[3])
            elif kind == 'click':
                self._mouse.position = (action[2], action[3])
                if action[5]:
                    self._mouse.press(action[4])
                else:
                    self._mouse.release(action[4])
            elif kind == 'scroll':
                self._mouse.position = (action[2], action[3])
                self._mouse.scroll(action[4], action[5])
            elif kind == 'key_press':
                self._kb.press(action[2])
            elif kind == 'key_release':
                self._kb.release(action[2])
        except:
            pass

    def stop_playback(self):
        self.playing = False

    def duration(self):
        if not self.actions:
            return 0.0
        return self.actions[-1][1]

    def count(self):
        return len(self.actions)


# ------------------------------------------------------------
# UI Helpers
# ------------------------------------------------------------
def mk_btn(parent, text, color, command, state=tk.NORMAL):
    return tk.Button(
        parent, text=text, command=command, state=state, # type: ignore
        bg=color, fg='white', activebackground=color,
        font=(UI['font'], 10, 'bold'),
        relief=tk.FLAT, bd=0, padx=16, pady=10,
        cursor='hand2', disabledforeground='#555577'
    )

def mk_label(parent, text, size=10, color=None, bold=False, mono=False, bg=None):
    return tk.Label(
        parent, text=text,
        bg=bg or UI['bg'], fg=color or UI['fg'],
        font=(UI['mono'] if mono else UI['font'], size, 'bold' if bold else 'normal')
    )


# ------------------------------------------------------------
# Main App
# ------------------------------------------------------------
class ActionRecorderApp:
    def __init__(self, root):
        self.root = root
        self.recorder = ActionRecorder()
        self._tick_id = None
        self._hotkey_listener = None

        root.title("ActionRecorder")
        root.resizable(False, False)
        root.configure(bg=UI['bg'])
        self._center(UI['w'], UI['h'])
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self._set_state('idle')
        self._start_hotkey_listener()

    def _center(self, w, h):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _build(self):
        # ── Header ──────────────────────────────────────────
        header = tk.Frame(self.root, bg=UI['surface'], pady=18)
        header.pack(fill=tk.X)

        tk.Label(header, text="⏺ ActionRecorder",
                 bg=UI['surface'], fg=UI['accent'],
                 font=(UI['font'], 20, 'bold')).pack()
        tk.Label(header, text="Record. Replay. Automate.",
                 bg=UI['surface'], fg=UI['fg_muted'],
                 font=(UI['font'], 9)).pack(pady=(2, 0))

        # ── Hotkey hint ─────────────────────────────────────
        tk.Label(header, text="Ctrl+Shift+S — stop recording or playback anytime",
                 bg=UI['surface'], fg=UI['accent'],
                 font=(UI['font'], 8, 'bold')).pack(pady=(4, 0))

        # ── Status Card ─────────────────────────────────────
        card = tk.Frame(self.root, bg=UI['panel'], padx=16, pady=12)
        card.pack(fill=tk.X, padx=16, pady=(14, 0))

        top_row = tk.Frame(card, bg=UI['panel'])
        top_row.pack(fill=tk.X)

        self._dot = tk.Label(top_row, text="●", bg=UI['panel'],
                             fg=UI['fg_muted'], font=(UI['font'], 13))
        self._dot.pack(side=tk.LEFT)

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(top_row, textvariable=self._status_var,
                 bg=UI['panel'], fg=UI['fg'],
                 font=(UI['font'], 10, 'bold')).pack(side=tk.LEFT, padx=8)

        self._win_var = tk.StringVar(value="")
        tk.Label(card, textvariable=self._win_var,
                 bg=UI['panel'], fg=UI['fg_muted'],
                 font=(UI['mono'], 8),
                 wraplength=460, justify='left').pack(anchor='w', pady=(5, 0))

        stats = tk.Frame(card, bg=UI['panel'])
        stats.pack(fill=tk.X, pady=(8, 0))

        self._count_var = tk.StringVar(value="Actions: 0")
        self._dur_var = tk.StringVar(value="Duration: 0.0s")

        for var in (self._count_var, self._dur_var):
            tk.Label(stats, textvariable=var,
                     bg=UI['panel'], fg=UI['fg_muted'],
                     font=(UI['font'], 9)).pack(side=tk.LEFT, padx=(0, 20))

        # ── Record Section ───────────────────────────────────
        self._section(self.root, "RECORDING")

        rec_btns = tk.Frame(self.root, bg=UI['bg'])
        rec_btns.pack(fill=tk.X, padx=16)

        self._rec_btn = mk_btn(rec_btns, "⏺  Record", UI['record'], self._start_rec)
        self._rec_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        self._stop_rec_btn = mk_btn(rec_btns, "⏹  Stop Recording", UI['fg_muted'], self._stop_rec, tk.DISABLED)
        self._stop_rec_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── Playback Options ─────────────────────────────────
        opts = tk.Frame(self.root, bg=UI['panel'], padx=16, pady=12)
        opts.pack(fill=tk.X, padx=16, pady=(14, 0))

        mk_label(opts, "PLAYBACK OPTIONS", size=8, color=UI['fg_muted'], bg=UI['panel']).pack(anchor='w', pady=(0, 8))

        rr = tk.Frame(opts, bg=UI['panel'])
        rr.pack(fill=tk.X, pady=(0, 8))
        mk_label(rr, "Repeat", size=9, bg=UI['panel']).pack(side=tk.LEFT)
        self._repeat_var = tk.IntVar(value=1)
        tk.Spinbox(rr, from_=1, to=9999, textvariable=self._repeat_var,
                   width=6, bg=UI['surface'], fg=UI['fg'],
                   buttonbackground=UI['border'], relief=tk.FLAT,
                   font=(UI['font'], 9)).pack(side=tk.LEFT, padx=8)
        mk_label(rr, "times", size=9, color=UI['fg_muted'], bg=UI['panel']).pack(side=tk.LEFT)

        sr = tk.Frame(opts, bg=UI['panel'])
        sr.pack(fill=tk.X)
        mk_label(sr, "Speed", size=9, bg=UI['panel']).pack(side=tk.LEFT)
        self._speed_var = tk.DoubleVar(value=1.0)
        self._speed_lbl = tk.StringVar(value="1.00×")
        tk.Scale(sr, from_=0.25, to=4.0, resolution=0.25,
                 orient=tk.HORIZONTAL, variable=self._speed_var,
                 bg=UI['panel'], fg=UI['fg'],
                 troughcolor=UI['border'], activebackground=UI['accent'],
                 highlightthickness=0, showvalue=False,
                 length=240, command=self._speed_changed).pack(side=tk.LEFT, padx=8)
        tk.Label(sr, textvariable=self._speed_lbl,
                 bg=UI['panel'], fg=UI['accent'],
                 font=(UI['font'], 9, 'bold'), width=6).pack(side=tk.LEFT)

        # ── Play Section ─────────────────────────────────────
        self._section(self.root, "PLAYBACK")

        play_btns = tk.Frame(self.root, bg=UI['bg'])
        play_btns.pack(fill=tk.X, padx=16)

        self._play_btn = mk_btn(play_btns, "▶  Play", UI['play'], self._start_play, tk.DISABLED)
        self._play_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        self._stop_play_btn = mk_btn(play_btns, "⏹  Stop Playback", UI['fg_muted'], self._stop_play, tk.DISABLED)
        self._stop_play_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── Tip ──────────────────────────────────────────────
        tk.Label(self.root,
                 text="💡 Move mouse to top-left corner to emergency stop playback.",
                 bg=UI['bg'], fg=UI['fg_muted'],
                 font=(UI['font'], 8)).pack(pady=(12, 0))

    def _section(self, parent, text):
        tk.Label(parent, text=text,
                 bg=UI['bg'], fg=UI['fg_muted'],
                 font=(UI['font'], 8, 'bold')).pack(anchor='w', padx=16, pady=(14, 6))

    def _speed_changed(self, val):
        self._speed_lbl.set(f"{float(val):.2f}×")

    # ── Hotkey ───────────────────────────────────────────────
    def _start_hotkey_listener(self):
        def on_hotkey():
            # Called from hotkey thread — use root.after to be thread safe
            self.root.after(0, self._hotkey_triggered)

        def listen():
            with keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+s': on_hotkey
            }) as h:
                self._hotkey_listener = h
                h.join()

        threading.Thread(target=listen, daemon=True).start()

    def _hotkey_triggered(self):
        if self.recorder.recording:
            self._stop_rec()
        elif self.recorder.playing:
            self._stop_play()

    # ── Minimize / Restore ───────────────────────────────────
    def _minimize(self):
        self.root.iconify()

    def _restore(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ── States ───────────────────────────────────────────────
    def _set_state(self, state):
        has_recording = self.recorder.count() > 0

        if state == 'idle':
            self._dot.config(fg=UI['play'] if has_recording else UI['fg_muted'])
            self._rec_btn.config(state=tk.NORMAL, bg=UI['record'])
            self._stop_rec_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])
            self._play_btn.config(state=tk.NORMAL if has_recording else tk.DISABLED,
                                  bg=UI['play'] if has_recording else UI['fg_muted'])
            self._stop_play_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])

        elif state == 'recording':
            self._dot.config(fg=UI['record'])
            self._rec_btn.config(state=tk.DISABLED, bg=UI['record_dim'])
            self._stop_rec_btn.config(state=tk.NORMAL, bg=UI['stop'])
            self._play_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])
            self._stop_play_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])

        elif state == 'playing':
            self._dot.config(fg=UI['play'])
            self._rec_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])
            self._stop_rec_btn.config(state=tk.DISABLED, bg=UI['fg_muted'])
            self._play_btn.config(state=tk.DISABLED, bg=UI['play_dim'])
            self._stop_play_btn.config(state=tk.NORMAL, bg=UI['record'])

    # ── Recording ────────────────────────────────────────────
    def _start_rec(self):
        self._minimize()
        self.root.after(300, self._begin_recording)

    def _begin_recording(self):
        self.recorder.start_recording()
        self._set_state('recording')
        self._status_var.set("Recording...  (Ctrl+Shift+S to stop)")
        self._win_var.set(f"Active window: {self.recorder.active_window}")
        self._tick()

    def _tick(self):
        if self.recorder.recording:
            self._count_var.set(f"Actions: {self.recorder.count()}")
            self._dur_var.set(f"Duration: {self.recorder.duration():.1f}s")
            self._tick_id = self.root.after(200, self._tick)

    def _stop_rec(self):
        if self._tick_id:
            self.root.after_cancel(self._tick_id)
        self.recorder.stop_recording()
        c = self.recorder.count()
        d = self.recorder.duration()
        self._count_var.set(f"Actions: {c}")
        self._dur_var.set(f"Duration: {d:.1f}s")
        self._set_state('idle')
        if c > 0:
            self._status_var.set(f"Recorded {c} actions ({d:.1f}s) — ready!")
        else:
            self._status_var.set("No actions recorded.")
            self._win_var.set("")
        self._restore()

    # ── Playback ─────────────────────────────────────────────
    def _start_play(self):
        if not self.recorder.actions:
            messagebox.showwarning("Nothing to play", "Record something first!")
            return
        repeat = self._repeat_var.get()
        speed = self._speed_var.get()
        self._set_state('playing')
        self._status_var.set(f"Playing ×{repeat} at {speed:.2f}× speed...  (Ctrl+Shift+S to stop)")
        self._minimize()
        self.root.after(300, lambda: self._begin_playback(repeat, speed))

    def _begin_playback(self, repeat, speed):
        self.recorder.focus_recorded_window()
        self.recorder.play(repeat=repeat, speed=speed, on_done=self._play_done)

    def _play_done(self):
        self.root.after(0, self._finish_play)

    def _finish_play(self):
        self._set_state('idle')
        self._status_var.set("Playback finished! ✅")
        self._restore()

    def _stop_play(self):
        self.recorder.stop_playback()
        self._set_state('idle')
        self._status_var.set("Playback stopped.")
        self._restore()

    def _on_close(self):
        self.recorder.stop_recording()
        self.recorder.stop_playback()
        self.root.destroy()
        sys.exit(0)


# ------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ActionRecorderApp(root)
    root.mainloop()