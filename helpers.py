import __main__
from platform import uname, system

if system() == "Windows":
    from pangsh_win import *
elif system() == "Linux":
    from pangsh_unix import *
else:
    print("Your OS is not supported by pangshell.")
    exit(1)

def_stdout = stdout


MAIN_DIR = os.path.dirname(os.path.realpath(__file__))


def IgnoreReturn(x):
    """ Explicitly ignore return valuie.
        
        If a return is ignored without this,
        there may be a bug. """


keywords = [
    "ls",   "echo",
    "cd",   "type",
    "rl",   "sudo",
    "rm",   "touch",
    "del",  "title",
    "cls",  "uptime",
    "exit", "neofetch",

    "@echo",
]

keywords.sort()  # sort alphabetically for easier autofill

# Constants

RED = (255, 0, 0)
GREEN = (0, 205, 0)
BLUE = (55, 125, 190)
PURPLE = (159, 60, 230)


def rgb(string: str, rgb: tuple[int, int, int]) -> str:
    return "\u001b[38;2;{};{};{}m{}\u001B[0m".format(*rgb, string)


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

    return "{}{}{} {}".format(months[date_.month], " " if date_.day > 9
                              else "  ", date_.day, date_.year)


def format_size(size: int) -> str:
    if not size:
        return "0 b"

    # 1000**exponent == 1 s.f. of size
    exponent = floor(log(size, 1000))
    name = ["b", "kb", "mb", "gb", "tb", "pb",
            "eb", "zb", "yb", "bb"][exponent]

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


def clear_out(inp_len: int, old_pos: int) -> str:
    return " " * (inp_len - old_pos) + "\b \b" * (inp_len)


def remove_word(s: str, pos: int) -> str:
    index = s.rfind(" ", 0, pos)

    if index == -1:
        return s[pos:]
    return s[:index] + s[pos:]


_ls_buf = ""
_ls_files = _ls_dirs = 0


def ls_thread(extension: str, iterator) -> None:
    global _ls_buf, _ls_files, _ls_dirs

    for entry in iterator:
        if not entry.name.endswith(extension):
            continue

        formatted_date = format_date(entry.stat().st_mtime)

        if entry.is_file():
            _ls_buf += rgb(formatted_date, GREEN) \
                + " File: " \
                + rgb("{:>9} ".format(format_size(entry.stat().st_size)), RED) \
                + rgb(entry.name, BLUE) + "\n"
            _ls_files += 1
        elif entry.is_dir():
            _ls_buf += rgb(formatted_date, GREEN) \
                + " Dir:            " \
                + rgb(entry.name, BLUE) + "\n"
            _ls_dirs += 1


def threaded_ls(extension: str, path: str | None = None) -> str:
    global _ls_buf, _ls_files, _ls_dirs

    dir_list = list(os.scandir(path))
    entries = len(dir_list)
    dir_list_left = dir_list[:entries >> 1]
    dir_list_right = dir_list[entries >> 1:]
    del dir_list

    t1 = Thread(target=ls_thread, args=(extension, dir_list_left))
    t2 = Thread(target=ls_thread, args=(extension, dir_list_right))
    del dir_list_left, dir_list_right

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    ls_buf = _ls_buf
    ls_files = _ls_files
    ls_dirs = _ls_dirs

    _ls_buf = ""
    _ls_files = _ls_dirs = 0
    return ls_buf + "\n - Files: {}\n - Directories: {}\n".format(ls_files, ls_dirs)


def input_width() -> int:
    """ Returns the amount of characters the user can input. """
    return get_console_width() - (len(gcwd()) + 4)


class Scanner:
    def __init__(self) -> None:
        self.autofill_cycle = False
        self.autofill_count = 0
        self.pos = 0
        self.prev_input = []
        self.prev_count = 0
        self.inp = ""

    def getch(self) -> int:
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

        if self.pos >= len(self.inp):
            self.inp = self.inp[:-1]
            return

        self.inp = self.inp[:self.pos] + self.inp[self.pos+1:]

    def move_cursor(self, n: int) -> None:
        self.pos += n
        move_cursor(n, 0)
    
    def autofill_prev(self, n: int) -> None:
        clear = clear_out(len(self.inp), self.pos)

        self.prev_count += n
        
        self.inp = self.prev_input[self.prev_count]
        self.pos = len(self.inp)
        stdout.write(clear + self.inp)
    
    def move_cursor_word(self, right: bool) -> None:
        if right:
            n = self.inp.find(" ", self.pos + 1, len(self.inp))
            
            if n == -1:
                n = len(self.inp)
        else:
            n = self.inp.rfind(" ", 0, self.pos)
            
            if n == -1:
                n = 0
        
        n -= self.pos
        
        self.move_cursor(n)
     
    def handle_special_char(self) -> None:
        ch = self.getch()

        if ch == 75 and self.pos > 0:                                             # RIGHT ARROW
            self.move_cursor(-1)
        elif ch == 77 and self.pos < len(self.inp):                               # LEFT ARROW
            self.move_cursor(1)
        elif ch == 72 and self.prev_count > 0:                                    # UP ARROW
            self.autofill_prev(-1)
        elif ch == 80 and self.prev_count < (len(self.prev_input) - 1):           # DOWN ARROW
            self.autofill_prev(1)
        elif ch == 115:                                                           # CTRL + LEFT ARROW
            self.move_cursor_word(False)
        elif ch == 116:                                                           # CTRL + RIGHT ARROW
            self.move_cursor_word(True)

    def append_ch(self, ch) -> None:
        self.autofill_count = 0
        self.autofill_cycle = False
        self.pos += 1
        self.inp = self.inp[:(self.pos-1)] + ch \
            + self.inp[(self.pos-1):]

    def scan(self) -> None:
        self.inp = ""
        self.pos = 0
        ch = ""

        while ch not in ("\r", "\n"):
            inp_len = len(self.inp)
            old_pos = self.pos

            if ch == "\b":
                self.backspace()
            elif len(self.inp) > input_width() or not ch:
                pass  # skip if-elif block
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
            if self.inp in self.prev_input:
                self.prev_input.append(self.prev_input.pop(
                    self.prev_input.index(self.inp)))
            else:
                self.prev_input.append(self.inp)
            
            self.prev_count = len(self.prev_input)

        stdout.write("\n")
        stdout.flush()


## Redefine print so file defaults to current stdout, this is for @echo off/on ##
old_print = print


def print(*args, **kwargs) -> None:
    if "file" not in kwargs.keys():
        kwargs["file"] = __main__.stdout

    old_print(*args, **kwargs)
