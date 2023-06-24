import os
import ctypes
import struct
from datetime import date
from math import log, floor
from dataclasses import dataclass
from platform import uname, system
from locale import setlocale, LC_ALL

from sys import stdout, platform, \
    executable, argv

try:
    from getch import getch
except ImportError:
    from msvcrt import getwch as getch, kbhit

UNIX = system() == "Linux"
WIN = system() == "Windows"

setlocale(LC_ALL, ".utf-8")
gHandle = ctypes.windll.kernel32.GetStdHandle(
    ctypes.c_long(-11))
ctypes.windll.kernel32.SetConsoleMode(gHandle, 7)
MAIN_DIR = os.path.dirname(os.path.realpath(__file__))

if UNIX:
    libc = ctypes.CDLL('libc.so.6')
    sysinfo_buf = ctypes.create_string_buffer(4096) # generous buffer to hold
                                                    # struct sysinfo

IgnoreReturn = lambda x: None

keywords = [
    "echo", "ls",
    "cd", "type",
    "touch", "exit",
    "cls", "neofetch",
    "uptime", "rm", "rl",
    "title",
]

# Constants

RED = (255, 0, 0)
GREEN = (0, 205, 0)
BLUE = (55, 125, 190)
PURPLE = (159, 60, 230)

USR_PATH = os.path.normpath(os.path.expanduser("~/"))

def rgb(string: str, rgb: tuple[int, int, int]) -> str:
    return "\u001b[38;2;{};{};{}m{}\u001B[0m".format(*rgb, string)

def format_path(path: str) -> str:
    if path.startswith(USR_PATH):
        path = "~/" + path.lstrip(USR_PATH)
    
    return path.replace("\\", "/")

def gcwd() -> str:
    """ Returns formatted current working directory """
    return format_path(os.getcwd())

def gradient(strings: list, start: tuple, end: tuple) -> list:
    res = []
    size = len(strings)
    
    for index, line in enumerate(strings):
        res.append(rgb(line,
           (((start[0] * (size - index)) + (end[0] * index))//size,
            ((start[1] * (size - index)) + (end[1] * index))//size,
            ((start[2] * (size - index)) + (end[2] * index))//size)))
    
    return res

months = {
    1: "Jan",  2: "Feb",
    3: "Mar",  4: "Apr",
    5: "May",  6: "Jun",
    7: "Jul",  8: "Aug",
    9: "Sep",  10: "Oct",
    11: "Nov", 12: "Dec",
}

def format_date(timestamp: float | int) -> str:
    date_ = date.fromtimestamp(timestamp)
    
    return "{}{}{} {}".format(months[date_.month], " " if date_.day > 9 \
                              else "  ", date_.day, date_.year)

def format_size(entry) -> str:
    size: int = entry.stat().st_size
    
    if not size:
        return "0 b"
    
    # 1000**exponent == 1 s.f. of size
    exponent = floor(log(size, 1000))
    name = ["b", "kb", "mb", "gb", "tb", "pb", "eb", "zb", "yb", "bb"][exponent]
    
    return "{} {}".format(round(size / 1000**exponent, 2), name)

def recursive_rm(path: str) -> None:
    if not os.path.isdir(path):
        raise NotADirectoryError("'{}' is not a directory.".format(path))
    
    for entry in os.scandir(path):
        joined_path = os.path.join(path, entry.name)
        
        if entry.is_file():
            print("Removing '{}'.".format(entry.name), end="\r")
            os.remove(joined_path)
            print(" " * len("Removing '{}'.".format(entry.name)), end="\r")
        elif entry.is_dir():
            recursive_rm(joined_path)

    os.rmdir(path)

def normal_rm(path: str) -> None:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "'{}' is not a file or does not exist.".format(path))

    os.remove(path)

@dataclass
class Uptime:
    secs: int
    mins: int
    hours: int
    days: int

# TODO: unix compatibility

if system() == "Windows":
    def get_uptime() -> Uptime:
        # https://www.geeksforgeeks.org/getting-the-time-since-os-startup-using-python/
        
        ticks = ctypes.windll.kernel32 \
                .GetTickCount64()

        ms = int(str(ticks)[:-3])

        mins, sec = divmod(ms, 60)
        hour, mins = divmod(mins, 60)
        days, hour = divmod(hour, 24)

        return Uptime(sec, mins, hour, days)
    
elif system() == "Linux":
    def get_uptime() -> Uptime:
        global sysinfo_buf, libc
        
        if libc.sysinfo(sysinfo_buf) != 0:
            return Uptime(-1, -1, -1, -1)

        ticks = struct.unpack_from('@l', sysinfo_buf.raw)[0]

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
        width, height, curx, cury, wattr, \
        left, top, right, bottom, maxx, maxy = \
            get_console_info()
                
        move = (x + curx) + ((y + cury) << 16)
    else:
        move = x + (y << 16)

    return ctypes.windll.kernel32. \
        SetConsoleCursorPosition(
            gHandle,
            ctypes.c_ulong(move)
        )

def clear_out(inp_len: int, old_pos: int) -> str:
    return " " * (inp_len - old_pos) + "\b \b" * (inp_len)

def kbhit_wait() -> None:
    while not kbhit():
        pass

def remove_word(s: str, pos: int) -> str:
    if s[:pos].rfind(" ") != -1:
        return s[:pos][s[:pos].rfind(" ")]
    return s[pos:]

class Scanner:
    def __init__(self) -> None:
        self.autofill_cycle = False
        self.autofill_count = 0
        self.pos = 0
        self.prev_input = []
        self.prev_count = 0
        self.inp = ""

    def getch(self) -> int:
        kbhit_wait()
        return ord(getch())

    def auto_fill(self) -> None:
        self.pos += 1
        self.autofill_count += 1
        
        if self.inp.rstrip().find(" ") != -1:
            return

        if not self.inp:
            self.autofill_cycle = True
            self.inp = keywords[0]
            return

        if self.autofill_cycle:
            self.inp = keywords[
                self.autofill_count % len(keywords)]
            return

        self.autofill_cycle = False

        valid_kws = [kw for kw in keywords
            if kw.startswith(self.inp[0]) and kw != self.inp]

        if valid_kws:
            self.inp = valid_kws[
                self.autofill_count % len(valid_kws)]

    def backspace(self) -> None:
        if self.pos <= 0:
            return

        self.pos -= 1

        if self.pos == len(self.inp):
            self.inp = self.inp[:-1]
            return

        self.inp = self.inp[:self.pos] + self.inp[self.pos+1:]

    def handle_special_char(self) -> None:
        ch = self.getch()
                
        if ch == 75 and self.pos > 0:
            self.pos -= 1
            move_cursor(-1, 0)
        elif ch == 77 and self.pos < len(self.inp):
            self.pos += 1
            move_cursor(1, 0)
        elif ch in (72, 80) and self.prev_input:
            clear = clear_out(len(self.inp), self.pos)
            
            self.inp = self.prev_input[self.prev_count % len(self.prev_input)]
            self.pos = len(self.inp)
            self.prev_count += 1 if ch == 72 else -1
            
            stdout.write(clear + self.inp)

    def append_ch(self, ch) -> None:
        self.autofill_count = 0
        self.autofill_cycle = False
        self.pos += 1
        self.inp = self.inp[:(self.pos-1)] + ch \
                 + self.inp[(self.pos-1):]

    def scan(self) -> None:
        self.inp = ""
        ch = ""

        while ch != "\r":
            inp_len = len(self.inp)
            old_pos = self.pos
            
            if not ch:
                pass # skip if-elif block
            elif ch == "\b":
                self.backspace()
            elif ch == "\x7f":
                self.inp = remove_word(self.inp, self.pos)
                self.pos += len(self.inp) - inp_len
            elif ch == "\t":
                self.auto_fill()
                self.pos = len(self.inp)
            else:
                self.append_ch(ch)

            stdout.write(
                clear_out(inp_len, old_pos)
              + self.inp + "\b" * (len(self.inp) - self.pos))
            
            stdout.flush()

            ch = self.getch()
            
            if ch in (0, 224):
                self.handle_special_char()
                ch = ""
            else:
                ch = chr(ch)

        if self.inp.strip():
            self.prev_input.append(self.inp)
            self.prev_count = len(self.prev_input) - 1
        
        stdout.write("\n")
        stdout.flush()
