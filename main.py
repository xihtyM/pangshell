""" command prompt """

from subprocess import run, list2cmdline, \
    CREATE_NEW_CONSOLE, Popen

from socket import gethostname
from enum import Enum, auto
from typing import Any
from helpers import *

try:
    from sys import set_int_max_str_digits
    set_int_max_str_digits((1<<31) - 1)
except ImportError:
    pass

# basic lexical analyser

class TokenType(Enum):
    STRING = auto()
    NUM = auto()
    
    ID = auto()
    KEYWORD = auto()
    VARIABLE = auto()
    END_OF_LINE = auto()
    SEMICOLON = auto()
    
    EQ = auto()
    SET = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    POW = auto()
    
    IADD = auto()
    ISUB = auto()
    IMUL = auto()
    IDIV = auto()
    IMOD = auto()
    IPOW = auto()
    LPAREN = auto()
    RPAREN = auto()
    
    WHITESPACE = auto()

@dataclass
class Token:
    type_: TokenType
    value: int | str

class Lexer:
    def __init__(self, line: str) -> None:
        self.src = line
        self.ind = 0
        self.size = len(self.src)
        
        self.toks: list[Token] = []
    
    def _get(self) -> str:
        """ Increments index and returns previous char. """
        
        self.ind += 1

        if (self.ind - 1) < self.size:
            return self.src[self.ind - 1]
        return ""

    
    def _peek(self) -> str:
        """ Returns current char. """
        if self.ind < self.size:
            return self.src[self.ind]
        
        return ""

    def atom(self, type_: TokenType) -> None:
        self.toks.append(Token(type_, self._get()))

    def identifier(self) -> None:
        raw = self._get()
        
        variable = raw == "$" # check if defining variable
        
        while self._peek() in ".@_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            raw += self._peek()

            if not self._get():
                break
        
        if variable:
            self.toks.append(Token(TokenType.VARIABLE, raw[1:]))
        elif raw in keywords:
            self.toks.append(Token(TokenType.KEYWORD, raw))
        else:
            self.toks.append(Token(TokenType.ID, raw))
    
    def num(self) -> None:
        raw = ""
        fl = False

        while self._peek() and self._peek() in "0123456789":
            raw += self._get()
            
            if not fl and self._peek() == ".":
                raw += self._get()
                fl = True
        
        self.toks.append(Token(TokenType.NUM, int(raw) if not fl else float(raw)))
    
    def string(self) -> None:
        raw = ""
        
        self._get()
        
        while self._peek() != "\"":
            raw += self._peek()
            
            if not self._get():
                raise SyntaxError("EOL before termination of string")
        
        self._get()
        
        self.toks.append(Token(TokenType.STRING, raw))
    
    def ieq(self, cur: str, normal: TokenType, inormal: TokenType) -> None:
        self._get()
                
        if self._peek() == "=":
            self.toks.append(Token(inormal, "{}=".format(cur)))
            self._get()
        else:
            self.toks.append(Token(normal, cur))
    
    def lex(self) -> None:
        while self._peek():
            end = False
            depth = 0
            
            while self._peek() in " \t":
                depth += 1 if self._peek() == " " else 4
                self.ind += 1

                if not self._peek():
                    end = True
                    break
            
            if depth:
                self.toks.append(Token(TokenType.WHITESPACE, depth))
            
            if end:
                break

            cur = self._peek()
            
            if cur in ".@$_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                self.identifier()
            elif cur in "0123456789":
                self.num()
            elif cur == "\"":
                self.string()
            elif cur == "=":
                self.ieq(cur, TokenType.SET, TokenType.EQ)
            elif cur == "+":
                self.ieq(cur, TokenType.ADD, TokenType.IADD)
            elif cur == "-":
                self.ieq(cur, TokenType.SUB, TokenType.ISUB)
            elif cur == "/":
                self.ieq(cur, TokenType.DIV, TokenType.IDIV)
            elif cur == "%":
                self.ieq(cur, TokenType.MOD, TokenType.IMOD)
            elif cur == "(":
                self.atom(TokenType.LPAREN)
            elif cur == ")":
                self.atom(TokenType.RPAREN)
            elif cur == ";":
                self.atom(TokenType.SEMICOLON)
            elif cur == "*":
                self._get()
                
                if self._peek() == "*":
                    self.ieq("**", TokenType.POW, TokenType.IPOW)
                elif self._peek() == "=":
                    self.toks.append(Token(TokenType.IMUL, "*="))
                    self._get()
                else:
                    self.toks.append(Token(TokenType.MUL, "*"))
            else:
                raise SyntaxError("Unrecognised character: {}".format(cur))
        
        self.toks.append(Token(TokenType.END_OF_LINE, ""))


### SRC: ###
# a = 5 * (10 + 20) # 1
# b = 5 - $a        # 2
# echo $b           # 3

### AST syntax: ###
# [
#   Assign(
#     "a",
#     "5 * (10 + 20)" # NOTE: concatenate all tokens until EOL or SEMICOLON - uses eval
#   ),
#   Assign(
#     "b",
#     "5 - {}", # NOTE: {} means a variable
#     variables=["a"] # NOTE: gets replaced by interpreter to self.variables["a"]
#   ),                # and then sent to evaluate_expr function.
#   Keyword(
#     "echo",
#     expr="{}",
#     variables=["b"]
#   )
# ]

@dataclass
class Assign:
    name: str
    expr: str
    variables: list[str] | None = None

@dataclass
class Keyword:
    name: str
    expr: str | list[str]
    variables: list[str] | None = None
    sudo: bool = False

@dataclass
class Program:
    args: str
    variables: list[str] | None = None
    sudo: bool = False

ASTNode = Assign | Keyword | Program

class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self.ast: list[ASTNode] = []
        self.src = lexer.src
        self.ind = 0
        
        if not lexer.toks:
            lexer.lex()
        
        self.toks = lexer.toks
        self.cur = self.toks[self.ind]
    
    def inc(self) -> None:
        try:
            self.ind += 1
            self.cur = self.toks[self.ind]
        except IndexError:
            self.cur = Token(TokenType.END_OF_LINE, "")
    
    def parse_expr(self) -> tuple[str, list | None]:
        expr = ""
        variables = []
        
        while self.cur.type_ not in (
                            TokenType.END_OF_LINE,
                            TokenType.SEMICOLON):
            
            if self.cur.type_ == TokenType.VARIABLE:
                expr += "{}"
                variables.append(self.cur.value)
            elif self.cur.type_ == TokenType.WHITESPACE:
                expr += " " * self.cur.value # depth of whitespace
            elif self.cur.type_ == TokenType.STRING:
                expr += "\"{}\"".format(self.cur.value)
            elif self.cur.type_ == TokenType.ID:
                expr += "\"{}\"".format(self.cur.value)
            else:
                expr += str(self.cur.value)
            
            self.inc()
        
        if not variables:
            return expr.lstrip(), None
        
        return expr.lstrip(), variables
    
    def parse_assign(self) -> None:
        key = None
        
        for x in range(1, self.ind + 1):
            if self.toks[self.ind - x].type_ == TokenType.ID:
                key = self.toks[self.ind - x]
                break
        
        if key is None:
            raise SyntaxError("No identifier to assign a value to.")
        
        self.inc() # skip '=' character
        
        expr, variables = self.parse_expr()
        
        self.ast.append(Assign(key.value, expr, variables))
    
    def parse_keyword(self) -> None:
        keyword = self.cur.value
        
        self.inc()
        
        if keyword in ("echo", "cd", "touch",
                       "type", "title", "del",
                       "@echo"):
            self.ast.append(Keyword(keyword, *self.parse_expr(), self.sudo))
        elif keyword in ("rm", "ls"):
            self.ast.append(Keyword(keyword, *self.parse_expr_no_eval(), self.sudo))
        else:
            self.ast.append(Keyword(keyword, "", None, self.sudo))
        
    def skip_whitespace(self) -> None:
        if self.cur.type_ == TokenType.WHITESPACE:
            self.inc()
    
    def parse_expr_no_eval(self) -> tuple[list[str], list[str]]:
        variables = []
        
        if self.cur.type_ == TokenType.WHITESPACE: # not a program
            self.skip_whitespace()
            args = []
        elif self.cur.type_ == TokenType.VARIABLE:
            args = ["{}"]
            variables.append(self.cur.value)
            self.inc()
        else:
            args = [self.cur.value]
            self.inc()
        
        self.skip_whitespace()
        
        if self.cur.type_ in (TokenType.IADD, TokenType.ISUB,
                                         TokenType.IMUL, TokenType.IDIV,
                                         TokenType.IMOD, TokenType.IPOW):
            self.toks[self.ind] = Token(TokenType.SET, "=")
            
            self.toks.insert(self.ind + 1, Token(TokenType.VARIABLE, args[0]))
            self.toks.insert(self.ind + 2, Token(getattr(TokenType, self.cur.type_._name_[1:]), self.cur.value[:-1]))
            
            self.cur = self.toks[self.ind]
            
        
        if self.cur.type_ == TokenType.SET:
            self.parse_assign()
            return # we dont want to parse the program anymore as it was an assignment either way
        
        while self.cur.type_ not in (
                            TokenType.END_OF_LINE,
                            TokenType.SEMICOLON):
            if self.cur.type_ == TokenType.WHITESPACE:
                self.inc()
                continue
            
            if self.cur.type_ in (TokenType.ID, TokenType.STRING):
                args.append(self.cur.value)
            elif self.cur.type_ == TokenType.SUB:
                self.inc()
                
                if self.cur.type_ in (TokenType.ID, TokenType.STRING):
                    args.append("-{}".format(self.cur.value))
                else:
                    raise SyntaxError("Args must be a string.")
            elif self.cur.type_ == TokenType.VARIABLE:
                args.append("{}")
                variables.append(self.cur.value)
            else:
                raise SyntaxError("Args must be a string.")

            self.inc()
        
        return args, variables
    
    def parse_program(self) -> None:
        expr = self.parse_expr_no_eval()
        
        if expr is None:
            return # not a program
        
        self.ast.append(Program(*expr, self.sudo))
    
    def parse(self) -> None:
        while self.cur.type_ != TokenType.END_OF_LINE:
            self.sudo = False

            if self.cur.value == "sudo":
                self.inc()
                self.skip_whitespace()
                self.sudo = True
            
            if self.cur.type_ == TokenType.KEYWORD:
                self.parse_keyword()
            elif self.cur.type_ in (TokenType.ID, TokenType.VARIABLE,
                               TokenType.STRING):
                self.parse_program()

            if self.cur.type_ == TokenType.END_OF_LINE:
                break
            
            self.inc()

class Interpreter:
    def __init__(self) -> None:
        self.variables = dict(os.environ) # pre-assign environment variables
        self.ast = []
        self.size = 0
        self.ind = 0
        
        self.keyword_function = {
            "rl": self.reload,
            "cd": self.cd,
            "ls": self.ls,
            "rm": self.rm,
            "del": self.del_var,
            "cls": self.cls,
            "type": self.type_,
            "echo": self.echo,
            "touch": self.touch,
            "title": self.title,
            "uptime": self.uptime,
            "neofetch": self.neofetch,
            
            "exit": exit,
            "@echo": self.echo_toggle,
        }
    
    def sudo(self, toggle: bool) -> None:
        if not self.ast[self.ind].sudo:
            return
        
        toggle = int(toggle)
        
        for n in range(1, 36):
            ctypes.windll.ntdll.RtlAdjustPrivilege(
                ctypes.c_uint(n), 
                ctypes.c_uint(toggle), 
                ctypes.c_uint(0), 
                ctypes.byref(ctypes.c_int())
            )
    
    def evaluate_expr(self) -> Any:
        cur = self.ast[self.ind]
        
        res = cur.expr
        
        if cur.variables is not None:
            variables = [repr(self.variables[var]) for var in cur.variables]
            res = res.format(*variables)
        
        try:
            res = eval(res)
            return res if type(res) is not bool else int(res)
        except Exception as error:
            raise SyntaxError(error)
    
    def echo_toggle(self) -> None:
        global stdout
        
        expr = self.evaluate_expr()

        if expr not in ("on", "off"):
            raise SyntaxError("@echo only takes arguments: 'on' or 'off'.")
        
        if expr == "off":
            stdout = open(os.devnull, "w", encoding="utf-8")
        else:
            stdout = def_stdout
    
    def del_var(self) -> None:
        varname = self.evaluate_expr()

        del self.variables[varname]
    
    def reload(self):
        Popen(
            list2cmdline([executable] + argv + ["--vars", str(self.variables)]),
            creationflags=CREATE_NEW_CONSOLE
        )
        
        exit(0)
    
    def rm(self) -> None:
        args = self.ast[self.ind].expr
        
        force = False
        recursive = False
        path = None

        for arg in args:
            if not arg.startswith("-"):
                if path is not None:
                    raise SyntaxError("Cannot specify path more than once.")

                path = arg
                continue

            chars = [char for char in arg[1:]]
            
            if "f" in chars:
                force = True
            if "r" in chars:
                recursive = True

        if path is None: 
            path = os.getcwd()
        
        if not force:
            confirmation = input(rgb(
                "You are about to remove '{}', are you sure [Y/N]? ".format(
                    format_path(path)), RED))

            if confirmation.lower() != "y":
                return # failed to confirm ;)
        
        if recursive:
            recursive_rm(path)
        else:
            normal_rm(path) 
    
    def uptime(self) -> None:
        uptime = get_uptime()
        
        print("{} days, {} hours, {} minutes and {} seconds".format(
            uptime.days, uptime.hours, uptime.mins, uptime.secs))
    
    def neofetch(self) -> None:
        info = uname()
        uptime = get_uptime()

        logo = open(self.variables["_logo_"], "r").read().split("\n")
        
        try:
            ver = VERSION
        except NameError:
            ver = self.variables["_version_"]
        
        buf = [
            "OS: {} {} {}".format(
                info.system, info.release, info.version),
            "Host: {}".format(
                gethostname()),
            "Uptime: {} days, {} hours, {} minutes".format(
                uptime.days, uptime.hours, uptime.mins),
            "and {} seconds".format(uptime.secs),
            "Resolution: {}".format(get_screen_res()),
            "Shell: PangShell v{}".format(ver),
        ]
        
        to_write = []
        
        for ind, line in enumerate(logo):
            if ind < len(buf):
                line += buf[ind]
            to_write.append(line)

        to_write = gradient(to_write, (230, 45, 65), (55, 125, 235))
        
        stdout.write("\n" + "\n".join(to_write) + "\n")
        stdout.flush()
    
    def title(self) -> None:
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(self.evaluate_expr())
        except AttributeError:
            stdout.write("\033]0;{}\007".format(self.evaluate_expr()))
            stdout.flush()
    
    def cls(self) -> None:
        IgnoreReturn(os.system("cls||clear"))
    
    def ls(self) -> None:
        cur = self.ast[self.ind]
        
        args = []
        n = 0
        
        for arg in cur.expr:
            if arg == "{}":
                args.append(str(self.variables[cur.variables[n]]))
                n += 1
            else:
                args.append(arg)
        
        del n
        extension = ""
        extension_st = False
        path = None
        
        for arg in args:
            if extension_st and not extension:
                extension = arg
                continue
            
            if arg == "-O":
                extension_st = True
                continue
            
            if arg:
                path = arg
        
        buf = "\n -- {} --\n\n".format(format_path(os.path.abspath(path) if path else gcwd()))
        buf += threaded_ls(extension, path)
        
        stdout.write(buf + "\n")
        stdout.flush()

    def cd(self) -> None:
        new_dir = self.evaluate_expr()
        
        try:
            os.chdir(new_dir)
        except FileNotFoundError:
            print(rgb("File '{}' could not be found.".format(
                new_dir), RED))
    
    def echo(self) -> None:
        print(self.evaluate_expr())
    
    def touch(self) -> None:
        open(self.evaluate_expr(), "x").close()
    
    def type_(self) -> None:
        file = self.evaluate_expr()
        
        try:
            print(open(file, "r", encoding="utf-8").read())
        except FileNotFoundError:
            print(rgb("File '{}' could not be found.".format(
                file), RED))
    
    def assign(self) -> None:
        self.variables[self.ast[self.ind].name] = self.evaluate_expr()
    
    def run_with_extensions(self, args: list[str]) -> bool:
        """ Return true if ran """
   
        for extension in (".bat", ".exe", ".com"):
            try:
                run([args[0] + extension] + args[1:], stdout=stdout)
                return True
            except FileNotFoundError:
                pass
    
    def run_program(self, args: list[str], sys: bool = False) -> None:
        if sys:
            original = args[0]
            args[0] = os.environ["WINDIR"] + "/System32/" + args[0]
        
        try:
            run(args, stdout=stdout)
        except FileNotFoundError:
            if platform == "win32":
                ran = self.run_with_extensions(args)
                
                if not ran and not sys:
                    self.run_program(args, True)
                elif not ran:
                    print(rgb("'{}' is not an operable program or script.\n".format(original)
                        + "Try typing the full name, the program must be compiled.", RED))                
            else:
                print(rgb("'{}' is not an operable program or script.\n".format(args[0])
                        + "Try typing the full name, the program must be compiled.", RED))
            
            if sys:
                args[0] = original
    
    def run(self, ast: list[ASTNode]) -> None:
        self.ast = ast
        self.size = len(ast)
        self.ind = 0
        
        while self.ind < self.size:
            cur = ast[self.ind]
            
            if type(cur) is Keyword:
                self.sudo(True)
                self.keyword_function[cur.name]()
                self.sudo(False)
            elif type(cur) is Assign:
                self.assign()
            elif type(cur) is Program:
                self.sudo(True)
                args = []
                n = 0
                
                for arg in cur.args:
                    if arg == "{}":
                        args.append(str(self.variables[cur.variables[n]]))
                        n += 1
                    else:
                        args.append(arg)
                
                self.run_program(args)
                self.sudo(False)
            
            self.ind += 1

def run_file(i: Interpreter, file: str) -> None:
    for line in open(file, "r").readlines():
        try:
            l = Lexer(line.replace("\n", ""))
            p = Parser(l)
            p.parse()
            i.run(p.ast)
        except SyntaxError as error:
            print(rgb(error, RED))
        except KeyError as var_name:
            print(rgb("Variable {} does not exist.".format(var_name), RED))
        except Exception as error:
            print(rgb(error, RED))

if __name__ == "__main__":
    sigint_paused = True
    i = Interpreter()
    i.variables["MAIN_DIR"] = MAIN_DIR
    run_file(i, os.path.join(MAIN_DIR, "startup.ps"))
    
    VERSION = i.variables["_version_"]
    
    if "--vars" in argv:
        variables_index = argv.index("--vars")
        i.variables = eval(argv[variables_index + 1])
        del argv[variables_index + 1], argv[variables_index]
    
    scanner = Scanner()
    
    while True:
        stdout.write(rgb("{}".format(gcwd()), PURPLE) + rgb("$ ", GREEN))
        stdout.flush()
    
        try:
            scanner.scan()
            l = Lexer(scanner.inp)
            p = Parser(l)
            p.parse()
            sigint_paused = False
            i.run(p.ast)
            sigint_paused = True
        except SyntaxError as error:
            print(rgb(error, RED))
        except KeyError as var_name:
            print(rgb("Variable {} does not exist.".format(var_name), RED))
        except Exception as error:
            print(rgb(error, RED))
        except KeyboardInterrupt:
            pass
