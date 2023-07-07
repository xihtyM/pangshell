import os
import ctypes
import struct
from datetime import date
from math import log, floor
from dataclasses import dataclass
from signal import signal, SIGINT
from locale import setlocale, LC_ALL
from threading import Thread
from time import sleep
from msvcrt import getwch as getch

from sys import stdout, platform, \
    executable, argv


sigint_paused = False

def sigint_handler(sig, frame):
    global sigint_paused

    if sigint_paused:
        return

    sigint_paused = True
    raise KeyboardInterrupt


signal(SIGINT, sigint_handler)
setlocale(LC_ALL, ".utf-8")

gHandle = ctypes.windll.kernel32.GetStdHandle(
    ctypes.c_long(-11))
ctypes.windll.kernel32.SetConsoleMode(gHandle, 7)

USR_PATH = os.path.normpath(os.path.expanduser("~/"))


def format_path(path: str) -> str:
    if path.startswith(USR_PATH):
        path = "~/" + path.lstrip(USR_PATH)

    return path.replace("\\", "/")


@dataclass
class Uptime:
    secs: int
    mins: int
    hours: int
    days: int


def get_uptime() -> Uptime:
    # https://www.geeksforgeeks.org/getting-the-time-since-os-startup-using-python/

    ticks = ctypes.windll.kernel32 \
        .GetTickCount64()

    ms = int(str(ticks)[:-3])

    mins, sec = divmod(ms, 60)
    hour, mins = divmod(mins, 60)
    days, hour = divmod(hour, 24)

    return Uptime(sec, mins, hour, days)


def get_screen_res() -> str:
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return "{}x{}".format(user32.GetSystemMetrics(0),
                            user32.GetSystemMetrics(1))


def get_console_info() -> tuple:
    csbi = ctypes.create_string_buffer(22)
    res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(
        gHandle, csbi)

    if not res:
        raise

    return struct.unpack("hhhhHhhhhhh", csbi.raw)


def move_cursor(x: int, y: int, relative: bool = True) -> int:
    if relative:
        width, height, curx, cury, *_ = get_console_info()

        move = (x + curx) + ((y + cury) << 16)
    else:
        move = x + (y << 16)

    return ctypes.windll.kernel32. \
        SetConsoleCursorPosition(
            gHandle,
            ctypes.c_ulong(move)
        )


def get_console_width() -> int:
    return get_console_info()[0]
