""" command prompt """

from subprocess import run, list2cmdline, \
    CREATE_NEW_CONSOLE, Popen

from signal import signal, SIGINT
from socket import gethostname
from enum import Enum, auto
from typing import Any
from helpers import *

def sigint_handler(sig, frame):
    return 0

signal(SIGINT, sigint_handler)

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
        
        while self._peek() in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
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
            
            if cur in "$_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
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

@dataclass
class Program:
    args: str
    variables: list[str] | None = None

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
                raise SyntaxError("Identifier '{}' is only usable in assignment expressions.".format(
                    self.cur.value))
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
                       "type", "title"):
            self.ast.append(Keyword(keyword, *self.parse_expr()))
        elif keyword in ("rm", "ls"):
            self.ast.append(Keyword(keyword, *self.parse_expr_no_eval()))
        else:
            self.ast.append(Keyword(keyword, ""))
        
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
        
        self.ast.append(Program(*expr))
    
    def parse(self) -> None:
        while self.cur.type_ != TokenType.END_OF_LINE:
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
            "echo": self.echo,
            "cd": self.cd,
            "ls": self.ls,
            "touch": self.touch,
            "type": self.type_,
            "cls": self.cls,
            "uptime": self.uptime,
            "neofetch": self.neofetch,
            "title": self.title,
            "rm": self.rm,
            "rl": self.reload,
            "exit": exit,
        }
    
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

        logo = \
"""                :^~^:                 
         :~7?7??JY55Y?!~^             
       :!JJ?!!!7!!!!7?YYJ7:   ^       
   :^!?J?!~~~~!!77!!777?YPY~:^7~      
 :~!JJ?^:^!?Y5P55P5YY7~^:!77???7      
 :^7YJ^:~7JPG5J7!!!^::^::^:!?J5?      
 :!YJ7~!JJY?^:    :   ~:~:  ??5J      
:!JJJ7~?J7^          :::~~^ ~5PP~:^   
:~7Y57!~~                 7?75PG57!   
:^!JY7J^              :  ^7GP55GP?:   
 ^~~J~?~              :~7JYGPJ5P?:::  
    7?~!~^^:   :^:^~!?Y5PPPPJY5?!~~   
    :?J???7!!!7?YPGGGBBP555YY5J?7~    
      ~J5PPP5PPYPBGGGGPPGG5Y7~!:      
        ^7Y555PPPP5YYYJYPJ~^^         
           :^7J55YJ7!~~~~^::          
               :~!~                   """.split("\n")
        
        buf = [
            "OS: {} {} {}".format(
                info.system, info.release, info.version),
            "Host: {}".format(
                gethostname()),
            "Uptime: {} days, {} hours, {} minutes".format(
                uptime.days, uptime.hours, uptime.mins),
            "and {} seconds".format(uptime.secs),
            "Shell: PangShell {}".format(VERSION),
            "Resolution: {}".format(get_screen_res()),
            ]
        
        to_write = []
        
        for ind, line in enumerate(logo):
            if ind < len(buf):
                line += buf[ind]
            to_write.append(line)

        to_write = gradient(to_write, (230, 45, 65), (55, 125, 235))
        
        stdout.write("\n" + "\n".join(to_write) + "\n\n")
        stdout.flush()
    
    def title(self) -> None:
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(self.evaluate_expr())
        except AttributeError:
            stdout.write("\033]0;{}\007".format(self.evaluate_expr()))
    
    def cls(self) -> None:
        IgnoreReturn(os.system("cls||clear"))
    
    def ls(self) -> None:
        cur = self.ast[self.ind]
        
        buf = "\n -- {} --\n\n".format(gcwd())
        extension = ""
        
        if "-O" in cur.expr:
            extension = cur.expr[cur.expr.index("-O") + 1]
        
        for entry in os.scandir():
            if not entry.name.endswith(extension):
                continue
            
            formatted_date = format_date(entry.stat().st_mtime)
            
            if entry.is_file():
                buf += rgb(formatted_date, GREEN) \
                    + " File: " \
                    + rgb("{:>9} ".format(format_size(entry)), RED) \
                    + rgb(entry.name, BLUE) + "\n"
            elif entry.is_dir():
                buf += rgb(formatted_date, GREEN) \
                    + " Dir:            " + rgb(entry.name, BLUE) + "\n"
        
        print(buf)

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
                run([args[0] + extension] + args[1:])
                return True
            except FileNotFoundError:
                pass
    
    def run_program(self, args: list[str], sys: bool = False) -> None:
        if sys:
            original = args[0]
            args[0] = os.environ["WINDIR"] + "/System32/" + args[0]
        
        try:
            run(args)
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
                self.keyword_function[cur.name]()
            elif type(cur) is Assign:
                self.assign()
            elif type(cur) is Program:
                args = []
                n = 0
                
                for arg in cur.args:
                    if arg == "{}":
                        args.append(str(self.variables[cur.variables[n]]))
                        n += 1
                    else:
                        args.append(arg)
                
                self.run_program(args)
            
            self.ind += 1

if __name__ == "__main__":
    i = Interpreter()
    
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
            i.run(p.ast)
        except SyntaxError as error:
            print(rgb(error, RED))
        except KeyError as var_name:
            print(rgb("Variable {} does not exist.".format(var_name), RED))
        except Exception as err:
            print(rgb(err, RED))
