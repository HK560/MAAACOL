"""
GameInputController and SessionTracker for Ace Combat Online
Windows SendInput with hardware scan codes.
"""

import ctypes
from ctypes import wintypes
import random
import time
from typing import Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput),
    ]


class WindowsInput(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii", InputUnion),
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

KEY_MAP = {
    "tab": 0x09,
    "space": 0x20,
    "esc": 0x1B,
    "escape": 0x1B,
    "enter": 0x0D,
    "return": 0x0D,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "w": 0x57,
    "a": 0x41,
    "s": 0x53,
    "d": 0x44,
    "f": 0x46,
    "z": 0x5A,
    "x": 0x58,
    "c": 0x43,
    "t": 0x54,
}


class GameInputController:
    """虚幻引擎原生硬件级按键控制器"""

    GAME_WINDOW_CLASS = "UnrealWindow"
    GAME_WINDOW_TITLE = "ACE COMBAT 8 : WINGS OF THEVE"

    @classmethod
    def get_game_hwnd(cls) -> Optional[int]:
        h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)

        hwnd = user32.FindWindowW(cls.GAME_WINDOW_CLASS, cls.GAME_WINDOW_TITLE)
        if not hwnd:
            hwnd = user32.FindWindowW(None, cls.GAME_WINDOW_TITLE)
        return hwnd if hwnd else None

    @classmethod
    def ensure_foreground(cls) -> bool:
        hwnd = cls.get_game_hwnd()
        if not hwnd:
            return False

        current_fg = user32.GetForegroundWindow()
        if current_fg != hwnd:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.08)
        return True

    @classmethod
    def send_key(cls, key_name: str, hold_duration: float = 0.08) -> bool:
        key_name = key_name.lower().strip()
        vk_code = KEY_MAP.get(key_name)
        if not vk_code:
            print(f"[GameInput] Unknown key name: {key_name}")
            return False

        cls.ensure_foreground()

        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        extra = ctypes.c_ulong(0)

        # 按下键位
        down_union = InputUnion()
        down_union.ki = KeyBdInput(
            vk_code, scan_code, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra)
        )
        inp_down = WindowsInput(INPUT_KEYBOARD, down_union)
        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(WindowsInput))

        time.sleep(hold_duration)

        # 抬起键位
        up_union = InputUnion()
        up_union.ki = KeyBdInput(
            vk_code,
            scan_code,
            KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP,
            0,
            ctypes.pointer(extra),
        )
        inp_up = WindowsInput(INPUT_KEYBOARD, up_union)
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(WindowsInput))

        return True


class TdmSessionTracker:
    """TDM 运行会话统计跟踪器"""

    def __init__(self):
        self.start_time = time.time()
        self.completed_rounds = 0
        self.max_rounds = 10
        self.max_minutes = 60
        self.is_stopped = False

    def reset(self, max_rounds: int = 10, max_minutes: int = 60):
        self.start_time = time.time()
        self.completed_rounds = 0
        self.max_rounds = max_rounds
        self.max_minutes = max_minutes
        self.is_stopped = False

    def increment_round(self):
        self.completed_rounds += 1
        elapsed_min = (time.time() - self.start_time) / 60.0
        print(
            f"[TdmSession] Round {self.completed_rounds} completed. Elapsed: {elapsed_min:.1f} min."
        )

    def check_stop_condition(self) -> bool:
        if self.is_stopped:
            return True

        if self.max_rounds > 0 and self.completed_rounds >= self.max_rounds:
            print(
                f"[TdmSession] Max rounds reached: {self.completed_rounds}/{self.max_rounds}."
            )
            self.is_stopped = True
            return True

        if self.max_minutes > 0:
            elapsed_min = (time.time() - self.start_time) / 60.0
            if elapsed_min >= self.max_minutes:
                print(
                    f"[TdmSession] Max minutes reached: {elapsed_min:.1f}/{self.max_minutes} min."
                )
                self.is_stopped = True
                return True

        return False


session_tracker = TdmSessionTracker()
