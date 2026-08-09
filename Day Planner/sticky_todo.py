import tkinter as tk
from tkinter import font as tkfont
import json
import os
import sys
import uuid
import ctypes
import threading
import calendar as calendar_mod
import webbrowser
from datetime import date, timedelta
from ctypes import wintypes

try:
    import sheets_sync
except Exception:
    sheets_sync = None

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
APP_DIR = os.path.join(os.path.expanduser("~"), ".sticky_todo")
DATA_FILE = os.path.join(APP_DIR, "todos.json")
STATE_FILE = os.path.join(APP_DIR, "window_state.json")
LOG_FILE = os.path.join(APP_DIR, "crash.log")

os.makedirs(APP_DIR, exist_ok=True)

def date_key(d):
    return d.isoformat()


def key_to_date(k):
    y, m, d = (int(p) for p in k.split("-"))
    return date(y, m, d)


def _ordinal(n):
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def format_date_display(d):
    return f"{_ordinal(d.day)} {d.strftime('%B')}"


def log_error(context, exc):
    import traceback
    import datetime
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.datetime.now().isoformat()} [{context}] ---\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass

BG = "#1c1c1e"
BODY_BG = "#212123"
ROW_BG = "#26262a"
ROW_HOVER = "#2f2f34"
ACCENT = "#8a8a92"
ACCENT_FILL = "#6c6c74"
TEXT = "#e7e7ea"
TEXT_DIM = "#6f6f76"
ENTRY_BG = "#242427"
BORDER = "#333336"
CLOSE_HOVER = "#3a3a3e"
SCROLL_THUMB = "#4a4a50"
SCROLL_THUMB_HOVER = "#5c5c63"

CORNER_RADIUS = 14

PRIORITY_LEVELS = ["None", "Low", "Medium", "High", "Urgent"]
PRIORITY_COLORS = {
    "None":   (ROW_BG,    ROW_HOVER),
    "Low":    ("#213228", "#28392f"),
    "Medium": ("#332e1f", "#3c3726"),
    "High":   ("#3a2424", "#452b2b"),
    "Urgent": ("#4a1e1e", "#571f1f"),
}
PRIORITY_ACCENTS = {
    "Low": "#5fae6f",
    "Medium": "#c9b458",
    "High": "#c96a6a",
    "Urgent": "#e0453f",
}


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def try_round_corners(root):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        pref = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref), ctypes.sizeof(pref)
        )
    except Exception:
        pass


def try_exclude_from_show_desktop(root):
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        return hwnd
    except Exception:
        return None


def win32_force_topmost(root):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        HWND_TOPMOST = -1
        SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE = 0x0002, 0x0001, 0x0010
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception:
        pass


def _find_workerw():
    import ctypes
    user32 = ctypes.windll.user32

    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return None

    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, None)

    workerw = ctypes.c_void_p(0)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        nonlocal workerw
        shelldll = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shelldll:
            candidate = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if candidate:
                workerw = ctypes.c_void_p(candidate)
        return True

    user32.EnumWindows(enum_proc, 0)
    return workerw.value if workerw.value else None


def attach_to_desktop(root):
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        root.update_idletasks()
        hwnd = user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        workerw = _find_workerw()
        if not workerw:
            return False
        user32.SetParent(hwnd, workerw)
        return True
    except Exception:
        return False


def detach_from_desktop(root):
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        root.update_idletasks()
        hwnd = user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        user32.SetParent(hwnd, None)
        return True
    except Exception:
        return False


_AUTOSTART_NAME = "StickyTodo"
_AUTOSTART_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _autostart_command():
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    script = os.path.abspath(__file__)
    return f'"{pythonw}" "{script}"'


def is_autostart_enabled():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY_PATH) as key:
            winreg.QueryValueEx(key, _AUTOSTART_NAME)
        return True
    except Exception:
        return False


def set_autostart(enabled):
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY_PATH,
                             0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, _AUTOSTART_NAME, 0, winreg.REG_SZ,
                                   _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, _AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass


class SystemTrayIcon:
    WM_TRAYICON = 0x0400 + 20
    WM_COMMAND = 0x0111
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
    NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
    ID_SHOW, ID_AUTOSTART, ID_QUIT = 1001, 1002, 1003

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uTimeoutOrVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", ctypes.c_byte * 16),
            ("hBalloonIcon", wintypes.HICON),
        ] if sys.platform == "win32" else []

    def __init__(self, app):
        self.app = app
        self.hwnd = None
        self._wndproc_ref = None
        self._class_name = "StickyTodoTrayWnd"

    def create(self):
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            kernel32 = ctypes.windll.kernel32
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE
            hinstance = kernel32.GetModuleHandleW(None)

            user32.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint,
                                               wintypes.WPARAM, wintypes.LPARAM]
            user32.DefWindowProcW.restype = LRESULT
            user32.CreateWindowExW.restype = wintypes.HWND
            user32.LoadIconW.restype = wintypes.HICON

            WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND,
                                          ctypes.c_uint, wintypes.WPARAM,
                                          wintypes.LPARAM)
            self._wndproc_ref = WNDPROC(self._wndproc)

            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ("style", ctypes.c_uint),
                    ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HANDLE),
                    ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE),
                    ("hbrBackground", wintypes.HANDLE),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            wc = WNDCLASS()
            wc.style = 0
            wc.lpfnWndProc = self._wndproc_ref
            wc.hInstance = hinstance
            wc.lpszClassName = self._class_name
            user32.RegisterClassW(ctypes.byref(wc))

            self.hwnd = user32.CreateWindowExW(
                0, self._class_name, "StickyTodoTray", 0,
                0, 0, 0, 0, None, None, hinstance, None)
            if not self.hwnd:
                return False

            nid = self.NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(self.NOTIFYICONDATAW)
            nid.hWnd = self.hwnd
            nid.uID = 1
            nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
            nid.uCallbackMessage = self.WM_TRAYICON
            nid.hIcon = user32.LoadIconW(None, ctypes.c_void_p(32512))
            nid.szTip = "Sticky Todo"
            shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid))
            self._nid = nid
            return True
        except Exception:
            self.hwnd = None
            return False

    def destroy(self):
        if not self.hwnd:
            return
        try:
            ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_DELETE,
                                                      ctypes.byref(self._nid))
        except Exception:
            pass

    def _wndproc(self, hwnd, msg, wparam, lparam):
        user32 = ctypes.windll.user32
        if msg == self.WM_TRAYICON:
            if lparam in (self.WM_LBUTTONUP, self.WM_LBUTTONDBLCLK):
                self.app.root.after(0, self.app.show_from_tray)
            elif lparam == self.WM_RBUTTONUP:
                self.app.root.after(0, self._popup_menu)
            return 0
        if msg == self.WM_COMMAND:
            cmd = wparam & 0xFFFF
            if cmd == self.ID_SHOW:
                self.app.root.after(0, self.app.show_from_tray)
            elif cmd == self.ID_AUTOSTART:
                self.app.root.after(0, self.app.toggle_autostart)
            elif cmd == self.ID_QUIT:
                self.app.root.after(0, self.app.quit_app)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _popup_menu(self):
        user32 = ctypes.windll.user32
        user32.CreatePopupMenu.restype = wintypes.HMENU
        MF_STRING, MF_CHECKED = 0x0, 0x8
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, self.ID_SHOW, "Show Todo")
        autostart_flags = MF_STRING | (MF_CHECKED if is_autostart_enabled() else 0)
        user32.AppendMenuW(menu, autostart_flags, self.ID_AUTOSTART,
                            "Start with Windows")
        user32.AppendMenuW(menu, 0x0800, 0, None)
        user32.AppendMenuW(menu, MF_STRING, self.ID_QUIT, "Quit")

        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        user32.TrackPopupMenu(menu, 0x0, pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, 0, 0, 0)
        user32.DestroyMenu(menu)


class Checkbox(tk.Canvas):
    SIZE = 18

    def __init__(self, master, checked, on_toggle, **kwargs):
        super().__init__(master, width=self.SIZE, height=self.SIZE,
                          bg=kwargs.pop("bg", ROW_BG), highlightthickness=0,
                          bd=0, cursor="hand2", **kwargs)
        self.checked = checked
        self.on_toggle = on_toggle
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self):
        self.delete("all")
        pad = 1.5
        r = 4
        x0, y0, x1, y1 = pad, pad, self.SIZE - pad, self.SIZE - pad
        fill = ACCENT_FILL if self.checked else ""
        outline = ACCENT_FILL if self.checked else ACCENT
        self._round_rect(x0, y0, x1, y1, r, fill=fill, outline=outline, width=1.6)
        if self.checked:
            self.create_line(x0 + 3.5, (y0 + y1) / 2, x0 + 7, y1 - 3.5,
                              fill="#f0f0f2", width=1.8, capstyle="round")
            self.create_line(x0 + 7, y1 - 3.5, x1 - 3, y0 + 3.5,
                              fill="#f0f0f2", width=1.8, capstyle="round")

    def _round_rect(self, x0, y0, x1, y1, r, **kw):
        points = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        self.create_polygon(points, smooth=True, **kw)

    def _toggle(self, _evt=None):
        self.checked = not self.checked
        self._draw()
        self.on_toggle(self.checked)

    def set_bg(self, color):
        self.configure(bg=color)
        self._draw()


class TodoRow(tk.Frame):
    def __init__(self, master, app, todo):
        todo.setdefault("priority", "None")
        base, hover = PRIORITY_COLORS[todo["priority"]]
        super().__init__(master, bg=base)
        self.app = app
        self.todo = todo

        self.checkbox = Checkbox(self, todo["done"], self._on_toggle, bg=base)
        self.checkbox.pack(side="left", padx=(10, 8), pady=8, anchor="n")

        self.label_font = tkfont.Font(family="Segoe UI", size=10,
                                       overstrike=todo["done"])
        self.label = tk.Label(self, text=todo["text"], anchor="w", justify="left",
                               bg=base, fg=self._text_color(),
                               font=self.label_font, wraplength=180)
        self.label.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=8)

        self.delete_btn = tk.Label(self, text="\u2715", bg=base, fg=TEXT_DIM,
                                    font=("Segoe UI", 9), cursor="hand2")
        self.delete_btn.pack(side="right", padx=10, pady=8, anchor="n")

        self._build_priority_menu()

        for widget in (self, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_motion)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Button-3>", self._show_priority_menu)

        self.delete_btn.bind("<Enter>", lambda e: self.delete_btn.configure(fg="#c96a6a"))
        self.delete_btn.bind("<Leave>", lambda e: self.delete_btn.configure(fg=TEXT_DIM))
        self.delete_btn.bind("<Button-1>", self._on_delete)

    def _colors(self):
        return PRIORITY_COLORS[self.todo["priority"]]

    def _text_color(self):
        return TEXT_DIM if self.todo["done"] else TEXT

    def _on_toggle(self, checked):
        self.todo["done"] = checked
        self.label_font.configure(overstrike=checked)
        self.label.configure(fg=self._text_color())
        self.app.save()

    def _on_delete(self, _evt):
        self.app.remove_row(self)

    def _on_enter(self, _evt):
        if self.app.drag_row is None:
            self._set_bg(self._colors()[1])

    def _on_leave(self, _evt):
        if self.app.drag_row is None:
            self._set_bg(self._colors()[0])

    def _set_bg(self, color):
        self.configure(bg=color)
        self.label.configure(bg=color)
        self.delete_btn.configure(bg=color)
        self.checkbox.set_bg(color)

    def update_wrap(self, list_width):
        wrap = max(60, list_width - 90)
        if self.label.cget("wraplength") != wrap:
            self.label.configure(wraplength=wrap)

    def _on_press(self, evt):
        self.app.start_drag(self, evt)

    def _on_motion(self, evt):
        self.app.drag_motion(evt)

    def _on_release(self, evt):
        self.app.end_drag()

    def _build_priority_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=ENTRY_BG, fg=TEXT,
                        activebackground=ROW_HOVER, activeforeground=TEXT, bd=0)
        for level in PRIORITY_LEVELS:
            label = level if level == "None" else f"\u25CF  {level}"
            color = PRIORITY_ACCENTS.get(level, TEXT_DIM)
            menu.add_command(label=label, foreground=color,
                              command=lambda p=level: self._set_priority(p))
        self.priority_menu = menu

    def _show_priority_menu(self, evt):
        self.priority_menu.tk_popup(evt.x_root, evt.y_root)

    def _set_priority(self, level):
        self.todo["priority"] = level
        self._set_bg(self._colors()[0])
        self.app.save()


class CalendarPopup(tk.Toplevel):
    def __init__(self, app, selected_date, on_pick):
        super().__init__(app.root, bg=BG)
        self.app = app
        self.on_pick = on_pick
        self.view_year = selected_date.year
        self.view_month = selected_date.month
        self.selected_date = selected_date

        self.overrideredirect(True)
        self.configure(highlightbackground=BORDER, highlightthickness=1)
        self.attributes("-topmost", True)

        self._position_near_date_label()
        self._build()

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<FocusOut>", lambda e: self.after(120, self._close_if_unfocused))
        self.focus_force()

    def _close_if_unfocused(self):
        try:
            if self.focus_get() is None:
                self.destroy()
        except Exception:
            self.destroy()

    def _position_near_date_label(self):
        lbl = self.app.date_label
        x = lbl.winfo_rootx() - 80
        y = lbl.winfo_rooty() + lbl.winfo_height() + 4
        self.geometry(f"+{max(0, x)}+{y}")

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=8, pady=(8, 4))

        prev_b = tk.Label(header, text="\u2039", bg=BG, fg=ACCENT,
                           font=("Segoe UI", 10), cursor="hand2", width=2)
        prev_b.pack(side="left")
        prev_b.bind("<Button-1>", lambda e: self._change_month(-1))

        next_b = tk.Label(header, text="\u203a", bg=BG, fg=ACCENT,
                           font=("Segoe UI", 10), cursor="hand2", width=2)
        next_b.pack(side="right")
        next_b.bind("<Button-1>", lambda e: self._change_month(1))

        month_name = date(self.view_year, self.view_month, 1).strftime("%B %Y")
        tk.Label(header, text=month_name, bg=BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="top")

        grid = tk.Frame(self, bg=BG)
        grid.pack(padx=8, pady=(0, 8))

        for col, wd in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
            tk.Label(grid, text=wd, bg=BG, fg=TEXT_DIM,
                     font=("Segoe UI", 8), width=3).grid(row=0, column=col, pady=(0, 2))

        cal = calendar_mod.Calendar(firstweekday=0)
        today = date.today()
        row = 1
        for week in cal.monthdayscalendar(self.view_year, self.view_month):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(grid, text="", bg=BG, width=3).grid(row=row, column=col)
                    continue
                d = date(self.view_year, self.view_month, day)
                is_selected = d == self.selected_date
                is_today = d == today
                fg = TEXT
                bg = ACCENT_FILL if is_selected else (ROW_BG if is_today else BG)
                cell = tk.Label(grid, text=str(day), bg=bg, fg=fg, width=3,
                                 font=("Segoe UI", 8, "bold" if is_today else "normal"),
                                 cursor="hand2")
                cell.grid(row=row, column=col, padx=1, pady=1)
                cell.bind("<Button-1>", lambda e, dd=d: self._pick(dd))
                cell.bind("<Enter>", lambda e, c=cell: c.configure(bg=ROW_HOVER))
                cell.bind("<Leave>", lambda e, c=cell, b=bg: c.configure(bg=b))
            row += 1

        today_btn = tk.Label(self, text="Today", bg=BG, fg=ACCENT,
                              font=("Segoe UI", 8, "underline"), cursor="hand2")
        today_btn.pack(pady=(0, 8))
        today_btn.bind("<Button-1>", lambda e: self._pick(date.today()))

    def _change_month(self, delta):
        m = self.view_month + delta
        y = self.view_year
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        self.view_month, self.view_year = m, y
        self._build()

    def _pick(self, d):
        self.on_pick(d)
        self.destroy()


class StickyTodoApp:
    MIN_W, MIN_H = 240, 200

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0.98)

        state = load_json(STATE_FILE, {})
        w = state.get("w", 300)
        h = state.get("h", 420)
        x = state.get("x", 120)
        y = state.get("y", 120)

        try:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            w = max(self.MIN_W, min(int(w), sw))
            h = max(self.MIN_H, min(int(h), sh))
            if not (-50 <= x <= sw - 50) or not (-50 <= y <= sh - 50):
                x, y = 120, 120
        except Exception:
            w, h, x, y = 300, 420, 120, 120

        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.always_on_top = tk.BooleanVar(value=state.get("topmost", True))
        self.root.attributes("-topmost", self.always_on_top.get())

        self.stuck_to_desktop = tk.BooleanVar(value=False)

        self.rows = []
        self.drag_row = None
        self._drag_start_y = 0
        self._resizing = False

        self.current_date = date.today()
        self._sync_timer = None

        self.tray = SystemTrayIcon(self)
        self._tray_active = self.tray.create()

        self._build_titlebar()
        self._build_date_nav()
        self._build_body()
        self._build_entry()
        self._build_context_menu()
        self._build_resize_grip()

        self.root.bind("<FocusOut>", lambda e: self.save_state())
        self.root.protocol_close = self.on_close

        try_round_corners(self.root)
        try_exclude_from_show_desktop(self.root)

        self._start_topmost_watchdog()

        self.load()

    def show_from_tray(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        win32_force_topmost(self.root)

    def toggle_autostart(self):
        set_autostart(not is_autostart_enabled())

    def quit_app(self):
        self.save()
        self.save_state()
        if getattr(self, "_tray_active", False):
            self.tray.destroy()
        self.root.destroy()

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=BG, height=30)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        title = tk.Label(bar, text="Todo", bg=BG, fg=ACCENT,
                          font=("Segoe UI", 9, "bold"))
        title.pack(side="left", padx=12)

        close_btn = tk.Label(bar, text="\u2715", bg=BG, fg=TEXT_DIM,
                              font=("Segoe UI", 10), cursor="hand2")
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#c96a6a"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=TEXT_DIM))
        close_btn.bind("<Button-1>", lambda e: self.on_close())

        for widget in (bar, title):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._do_move)
            widget.bind("<Button-3>", self._show_context_menu)

        self.titlebar = bar

    def _start_move(self, evt):
        self._move_x = evt.x_root - self.root.winfo_x()
        self._move_y = evt.y_root - self.root.winfo_y()

    def _do_move(self, evt):
        x = evt.x_root - self._move_x
        y = evt.y_root - self._move_y
        self.root.geometry(f"+{x}+{y}")

    def _build_date_nav(self):
        bar = tk.Frame(self.root, bg=BG, height=28)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        prev_btn = tk.Label(bar, text="\u2039", bg=BG, fg=ACCENT,
                             font=("Segoe UI", 12), cursor="hand2", width=3)
        prev_btn.pack(side="left")
        prev_btn.bind("<Button-1>", lambda e: self._shift_day(-1))
        prev_btn.bind("<Enter>", lambda e: prev_btn.configure(fg=TEXT))
        prev_btn.bind("<Leave>", lambda e: prev_btn.configure(fg=ACCENT))

        next_btn = tk.Label(bar, text="\u203a", bg=BG, fg=ACCENT,
                             font=("Segoe UI", 12), cursor="hand2", width=3)
        next_btn.pack(side="right")
        next_btn.bind("<Button-1>", lambda e: self._shift_day(1))
        next_btn.bind("<Enter>", lambda e: next_btn.configure(fg=TEXT))
        next_btn.bind("<Leave>", lambda e: next_btn.configure(fg=ACCENT))

        self.date_label = tk.Label(bar, text=format_date_display(self.current_date),
                                    bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold"),
                                    cursor="hand2")
        self.date_label.pack(side="top", expand=True)
        self.date_label.bind("<Button-1>", lambda e: self._open_calendar_popup())
        self.date_label.bind("<Enter>", lambda e: self.date_label.configure(fg=ACCENT))
        self.date_label.bind("<Leave>", lambda e: self.date_label.configure(fg=TEXT))

        self.date_nav_bar = bar

    def _refresh_date_label(self):
        self.date_label.configure(text=format_date_display(self.current_date))

    def _shift_day(self, delta):
        self.switch_date(self.current_date + timedelta(days=delta))

    def switch_date(self, new_date):
        if new_date == self.current_date:
            return
        self.save()
        for row in list(self.rows):
            row.pack_forget()
            row.destroy()
        self.rows = []
        self.current_date = new_date
        self._refresh_date_label()
        self.load(save_starters=False)

    def _open_calendar_popup(self):
        CalendarPopup(self, self.current_date, self.switch_date)

    def _build_context_menu(self):
        menu = tk.Menu(self.root, tearoff=0, bg=ENTRY_BG, fg=TEXT,
                        activebackground=ROW_HOVER, activeforeground=TEXT,
                        bd=0)
        menu.add_checkbutton(label="Always on top", variable=self.always_on_top,
                              command=self._toggle_topmost)
        if sys.platform == "win32":
            menu.add_checkbutton(label="Attach to desktop (behind other windows)",
                                  variable=self.stuck_to_desktop,
                                  command=self._toggle_stuck_to_desktop)
            self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
            menu.add_checkbutton(label="Start with Windows",
                                  variable=self.autostart_var,
                                  command=lambda: set_autostart(self.autostart_var.get()))
        menu.add_separator()
        menu.add_command(label="Jump to today", command=lambda: self.switch_date(date.today()))
        menu.add_command(label="Clear completed", command=self.clear_completed)
        menu.add_separator()
        menu.add_command(label="Sync to Google Sheets now", command=self.sync_to_sheets_now)
        menu.add_command(label="Open Google Sheet", command=self.open_sheet)
        menu.add_separator()
        if getattr(self, "_tray_active", False):
            menu.add_command(label="Hide to tray", command=self.on_close)
            menu.add_command(label="Quit", command=self.quit_app)
        else:
            menu.add_command(label="Close", command=self.on_close)
        self.context_menu = menu

    def _show_context_menu(self, evt):
        self.context_menu.tk_popup(evt.x_root, evt.y_root)

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())
        self.save_state()

    def _start_topmost_watchdog(self):
        self._enforce_topmost()
        self.root.after(400, self._start_topmost_watchdog)

    def _enforce_topmost(self):
        if not self.always_on_top.get():
            return
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass
        win32_force_topmost(self.root)

    def _toggle_stuck_to_desktop(self):
        self._apply_stuck_to_desktop(self.stuck_to_desktop.get())

    def _apply_stuck_to_desktop(self, enable):
        if enable:
            ok = attach_to_desktop(self.root)
            if not ok:
                self.stuck_to_desktop.set(False)
                return
        else:
            detach_from_desktop(self.root)
        self.save_state()

    def _build_body(self):
        outer = tk.Frame(self.root, bg=BODY_BG)
        outer.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=BODY_BG, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Canvas(outer, bg=BODY_BG, width=6, highlightthickness=0, bd=0)
        self.scrollbar.pack(side="right", fill="y")
        self._thumb = None
        self.scrollbar.bind("<Enter>", lambda e: self._draw_thumb(hover=True))
        self.scrollbar.bind("<Leave>", lambda e: self._draw_thumb(hover=False))

        self.list_frame = tk.Frame(self.canvas, bg=BODY_BG)
        self.list_window = self.canvas.create_window((0, 0), window=self.list_frame,
                                                       anchor="nw")

        self.list_frame.bind("<Configure>", self._on_list_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.root.bind_all("<MouseWheel>", self._on_wheel)
        self.root.bind_all("<Button-4>", lambda e: self._on_wheel_linux(-1, e))
        self.root.bind_all("<Button-5>", lambda e: self._on_wheel_linux(1, e))

    def _on_list_configure(self, _evt=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._draw_thumb()

    def _on_canvas_configure(self, evt):
        self.canvas.itemconfig(self.list_window, width=evt.width)
        for row in self.rows:
            row.update_wrap(evt.width)
        self._draw_thumb()

    def _pointer_over_list(self, evt):
        widget = self.root.winfo_containing(evt.x_root, evt.y_root)
        while widget is not None:
            if widget == self.canvas:
                return True
            widget = widget.master
        return False

    def _on_wheel(self, evt):
        if not self._pointer_over_list(evt):
            return
        delta = -1 if evt.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")
        self._draw_thumb()

    def _on_wheel_linux(self, direction, evt):
        if not self._pointer_over_list(evt):
            return
        self.canvas.yview_scroll(direction, "units")
        self._draw_thumb()

    def _draw_thumb(self, hover=False):
        self.scrollbar.delete("all")
        bbox = self.canvas.bbox("all")
        view_h = self.canvas.winfo_height()
        if not bbox or view_h <= 1:
            return
        content_h = max(bbox[3], view_h)
        first, last = self.canvas.yview()
        if last - first >= 0.999:
            return
        bar_h = self.scrollbar.winfo_height() or view_h
        thumb_h = max(24, bar_h * (last - first))
        thumb_y = bar_h * first
        color = SCROLL_THUMB_HOVER if hover else SCROLL_THUMB
        self.scrollbar.create_rectangle(1, thumb_y, 5, thumb_y + thumb_h,
                                         fill=color, outline="", width=0)

    def _build_entry(self):
        wrap = tk.Frame(self.root, bg=BG, height=42)
        wrap.pack(side="bottom", fill="x")
        wrap.pack_propagate(False)

        inner = tk.Frame(wrap, bg=ENTRY_BG, highlightbackground=BORDER,
                          highlightthickness=1)
        inner.pack(fill="x", expand=True, padx=10, pady=8)

        self.entry_var = tk.StringVar()
        entry = tk.Entry(inner, textvariable=self.entry_var, bg=ENTRY_BG,
                          fg=TEXT, insertbackground=TEXT, relief="flat",
                          font=("Segoe UI", 10), bd=0)
        entry.pack(fill="x", padx=8, pady=6)
        entry.bind("<Return>", self._on_add)
        self._placeholder(entry)

    def _placeholder(self, entry, text="Add a task..."):
        entry.insert(0, text)
        entry.configure(fg=TEXT_DIM)

        def on_focus_in(_evt):
            if entry.get() == text:
                entry.delete(0, "end")
                entry.configure(fg=TEXT)

        def on_focus_out(_evt):
            if not entry.get():
                entry.insert(0, text)
                entry.configure(fg=TEXT_DIM)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        self._entry_placeholder = text
        self._entry_widget = entry

    def _on_add(self, _evt=None):
        text = self.entry_var.get().strip()
        if not text or text == self._entry_placeholder:
            return
        self.add_todo(text)
        self._entry_widget.delete(0, "end")

    def _build_resize_grip(self):
        grip = tk.Canvas(self.root, width=14, height=14, bg=BG,
                          highlightthickness=0, bd=0, cursor="size_nw_se")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        for i in range(3):
            off = 3 + i * 4
            grip.create_line(2 + off, 12, 12, 2 + off, fill=ACCENT, width=1)
        grip.bind("<ButtonPress-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._do_resize)
        grip.bind("<ButtonRelease-1>", lambda e: self.save_state())

    def _start_resize(self, evt):
        self._resize_start = (evt.x_root, evt.y_root,
                               self.root.winfo_width(), self.root.winfo_height())

    def _do_resize(self, evt):
        sx, sy, sw, sh = self._resize_start
        w = max(self.MIN_W, sw + (evt.x_root - sx))
        h = max(self.MIN_H, sh + (evt.y_root - sy))
        self.root.geometry(f"{w}x{h}")

    def add_todo(self, text, done=False, priority="None", save=True):
        todo = {"id": uuid.uuid4().hex, "text": text, "done": done, "priority": priority}
        row = TodoRow(self.list_frame, self, todo)
        row.update_wrap(self.canvas.winfo_width() or 260)
        row.pack(side="top", fill="x", pady=(0, 1))
        self.rows.append(row)
        if save:
            self.save()

    def remove_row(self, row):
        row.pack_forget()
        row.destroy()
        self.rows.remove(row)
        self.save()

    def clear_completed(self):
        for row in list(self.rows):
            if row.todo["done"]:
                self.remove_row(row)

    def start_drag(self, row, evt):
        self.drag_row = row
        self._drag_start_y = evt.y_root
        row._set_bg(row._colors()[1])

    def drag_motion(self, evt):
        if self.drag_row is None:
            return
        list_top = self.list_frame.winfo_rooty()
        cursor_y = evt.y_root - list_top

        target_idx = len(self.rows) - 1
        acc = 0
        for i, r in enumerate(self.rows):
            h = r.winfo_height() or 34
            if cursor_y < acc + h / 2:
                target_idx = i
                break
            acc += h + 1
        else:
            target_idx = len(self.rows) - 1

        current_idx = self.rows.index(self.drag_row)
        if target_idx != current_idx:
            self.rows.insert(target_idx, self.rows.pop(current_idx))
            self._repack()

    def end_drag(self):
        if self.drag_row is not None:
            self.drag_row._set_bg(self.drag_row._colors()[0])
            self.drag_row = None
            self.save()

    def _repack(self):
        for r in self.rows:
            r.pack_forget()
        for r in self.rows:
            r.pack(side="top", fill="x", pady=(0, 1))

    def _load_all_data(self):
        raw = load_json(DATA_FILE, {})
        if isinstance(raw, list):
            raw = {date_key(date.today()): raw} if raw else {}
        return raw

    def save(self):
        all_data = self._load_all_data()
        rows_data = [{"text": r.todo["text"], "done": r.todo["done"],
                      "priority": r.todo.get("priority", "None")} for r in self.rows]
        key = date_key(self.current_date)
        if rows_data:
            all_data[key] = rows_data
        else:
            all_data.pop(key, None)
        save_json(DATA_FILE, all_data)
        self._schedule_sheet_sync(all_data)

    def load(self, save_starters=True):
        all_data = self._load_all_data()
        data = all_data.get(date_key(self.current_date), [])
        for item in data:
            self.add_todo(item.get("text", ""), item.get("done", False),
                           item.get("priority", "None"), save=False)
        if not data and not all_data and save_starters:
            self.add_todo("Drag to reorder", False, "None", save=False)
            self.add_todo("Right-click to set a priority", False, "None", save=False)
            self.save()

    def _schedule_sheet_sync(self, all_data):
        if sheets_sync is None or not sheets_sync.is_configured():
            return
        if self._sync_timer is not None:
            self._sync_timer.cancel()
        self._sync_timer = threading.Timer(4.0, self._run_sheet_sync, args=(all_data,))
        self._sync_timer.daemon = True
        self._sync_timer.start()

    def _run_sheet_sync(self, all_data):
        try:
            sheets_sync.push_data(all_data)
        except Exception as e:
            log_error("sheets sync", e)

    def sync_to_sheets_now(self):
        if sheets_sync is None or not sheets_sync.is_configured():
            from tkinter import messagebox
            messagebox.showinfo(
                "Google Sheets not set up",
                "Add your Google credentials first - see SHEETS_SETUP.md "
                f"next to this app, or drop credentials.json into:\n{APP_DIR}")
            return
        threading.Thread(target=self._run_sheet_sync,
                          args=(self._load_all_data(),), daemon=True).start()

    def open_sheet(self):
        if sheets_sync is None:
            return
        url = sheets_sync.get_sheet_url()
        if url:
            webbrowser.open(url)
        else:
            from tkinter import messagebox
            messagebox.showinfo("No sheet yet", "Sync at least once first.")

    def save_state(self):
        state = {
            "w": self.root.winfo_width(),
            "h": self.root.winfo_height(),
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
            "topmost": self.always_on_top.get(),
            "stuck_to_desktop": self.stuck_to_desktop.get(),
        }
        save_json(STATE_FILE, state)

    def on_close(self):
        self.save()
        self.save_state()
        if getattr(self, "_tray_active", False):
            self.root.withdraw()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = StickyTodoApp()

        def _log_callback_exception(exc_type, exc_value, exc_tb):
            log_error("tk callback", exc_value)
        app.root.report_callback_exception = _log_callback_exception
        app.run()
    except Exception as e:
        log_error("startup", e)
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _err_root = _tk.Tk()
            _err_root.withdraw()
            _mb.showerror(
                "Sticky Todo failed to start",
                f"{type(e).__name__}: {e}\n\n"
                f"Full details were written to:\n{LOG_FILE}"
            )
        except Exception:
            pass
        raise
