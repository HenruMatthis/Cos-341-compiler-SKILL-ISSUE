"""
Regex-based Lexer for SPL (Python implementation).

Produces a token stream: Token(type, value, line, column, index)
"""

from dataclasses import dataclass
import re
from typing import Iterator, List, Dict, Optional, Tuple

@dataclass
class Token:
    type: str
    value: Optional[object]
    line: int
    column: int
    index: int

class LexerError(Exception):
    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.line = line
        self.column = column

class Lexer:
    """
    Regex-based Lexer.
    """

    DEFAULT_TOKEN_SPEC: List[Tuple[str, str]] = [
        # Whitespace & comments
        ('NEWLINE',      r'\n+'),
        ('SKIP',         r'[ \t\r]+'),
        ('MCOMMENT',     r'/\*[\s\S]*?\*/'),
        ('SCOMMENT',     r'//[^\n]*'),
        ('HASHCOMMENT',  r'#[^\n]*'),

        # Literals
        ('NUMBER',       r'\d+\.\d+([eE][+-]?\d+)?|\d+[eE][+-]?\d+|\d+'),
        ('STRING',       r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''),

        # Multi-char operators
        ('LE',           r'<='),
        ('GE',           r'>='),
        ('EQ',           r'=='),
        ('NEQ',          r'!='),
        ('ARROW',        r'->'),

        # Assignment & single-char operators
        ('ASSIGN',       r'='),
        ('PLUS',         r'\+'),
        ('MINUS',        r'-'),
        ('TIMES',        r'\*'),
        ('DIVIDE',       r'/'),
        ('MOD',          r'%'),
        ('LPAREN',       r'\('),
        ('RPAREN',       r'\)'),
        ('LBRACE',       r'\{'),
        ('RBRACE',       r'\}'),
        ('LBRACKET',     r'\['),
        ('RBRACKET',     r'\]'),
        ('SEMI',         r';'),
        ('COMMA',        r','),
        ('COLON',        r':'),
        ('DOT',          r'\.'),
        ('LT',           r'<'),
        ('GT',           r'>'),

        # Identifiers & keywords
        ('ID',           r'[A-Za-z_][A-Za-z0-9_]*'),

        # Always last
        ('MISMATCH',     r'.'),
    ]

    DEFAULT_KEYWORDS: Dict[str, str] = {
        # --- Core SPL structural keywords ---
        'glob': 'GLOB',
        'proc': 'PROC',
        'func': 'FUNC',
        'main': 'MAIN',
        'local': 'LOCAL',
        'var': 'VAR',

        # --- Control flow ---
        'if': 'IF',
        'else': 'ELSE',
        'while': 'WHILE',
        'do': 'DO',
        'until': 'UNTIL',
        'return': 'RETURN',
        'halt': 'HALT',

        # --- I/O ---
        'print': 'PRINT',

        # --- Logical / arithmetic operators (word form) ---
        'eq': 'EQ_WORD',
        'gt': 'GT_WORD',
        'lt': 'LT_WORD',
        'ge': 'GE_WORD',
        'le': 'LE_WORD',
        'or': 'OR_WORD',
        'and': 'AND_WORD',
        'plus': 'PLUS_WORD',
        'minus': 'MINUS_WORD',
        'mult': 'MULT_WORD',
        'div': 'DIV_WORD',
        'neg': 'NEG_WORD',
        'not': 'NOT_WORD',

        # --- Optional type / const keywords ---
        'const': 'CONST',
        'true': 'TRUE',
        'false': 'FALSE',
        'int': 'INT_TYPE',
        'string': 'STRING_TYPE',
    }


    def __init__(self,
                 token_spec: Optional[List[Tuple[str, str]]] = None,
                 keywords: Optional[Dict[str, str]] = None):
        self.token_spec = token_spec or Lexer.DEFAULT_TOKEN_SPEC
        self.keywords = {k: v for k, v in (keywords or Lexer.DEFAULT_KEYWORDS).items()}
        self.master_pattern = re.compile("|".join(f"(?P<{name}>{pat})"
                                                 for name, pat in self.token_spec))

    def tokenize(self, text: str, filename: str = "<input>") -> Iterator[Token]:
        lineno = 1
        line_start = 0
        pos = 0
        end = len(text)

        while pos < end:
            m = self.master_pattern.match(text, pos)
            if not m:
                col = pos - line_start + 1
                raise LexerError(f"Unexpected character at {filename}:{lineno}:{col}", lineno, col)

            typ = m.lastgroup
            val = m.group(typ)

            if typ == 'NEWLINE':
                lineno += val.count('\n')
                line_start = m.end()

            elif typ in ('SKIP',):
                pass

            elif typ in ('MCOMMENT', 'SCOMMENT', 'HASHCOMMENT'):
                if '\n' in val:
                    lineno += val.count('\n')
                    line_start = m.end() - (val.rfind('\n') + 1)

            elif typ == 'ID':
                key_lower = val.lower()
                if key_lower in self.keywords:
                    yield Token(self.keywords[key_lower], None, lineno,
                                m.start() - line_start + 1, m.start())
                else:
                    yield Token('ID', val, lineno,
                                m.start() - line_start + 1, m.start())

            elif typ == 'NUMBER':
                if '.' in val or 'e' in val.lower():
                    try:
                        number = float(val)
                    except ValueError:
                        raise LexerError(f"Malformed number '{val}'",
                                         lineno, m.start() - line_start + 1)
                    yield Token('NUMBER', number, lineno,
                                m.start() - line_start + 1, m.start())
                else:
                    yield Token('NUMBER', int(val), lineno,
                                m.start() - line_start + 1, m.start())

            elif typ == 'STRING':
                inner = val[1:-1]
                try:
                    decoded = bytes(inner, "utf-8").decode("unicode_escape")
                except Exception:
                    decoded = inner
                yield Token('STRING', decoded, lineno,
                            m.start() - line_start + 1, m.start())

            elif typ == 'MISMATCH':
                col = m.start() - line_start + 1
                raise LexerError(f"Illegal character {val!r} at {filename}:{lineno}:{col}",
                                 lineno, col)

            else:
                yield Token(typ, val, lineno,
                            m.start() - line_start + 1, m.start())

            pos = m.end()

    def tokenize_file(self, path: str) -> Iterator[Token]:
        with open(path, 'r', encoding='utf8') as f:
            yield from self.tokenize(f.read(), filename=path)

    def print_token_spec(self) -> None:
        print("Token specification (order matters):")
        for name, pat in self.token_spec:
            print(f"  {name}: {pat}")
        print("Keywords:")
        for k, v in sorted(self.keywords.items()):
            print(f"  {k} -> {v}")

if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser(description='Lexer demo for SPL')
    parser.add_argument('file', nargs='?', help='source file (if omitted, read stdin)')
    args = parser.parse_args()
    data = ""
    if args.file:
        with open(args.file, 'r', encoding='utf8') as fh:
            data = fh.read()
    else:
        print("Enter SPL code (Ctrl-D to finish):")
        data = sys.stdin.read()
    lex = Lexer()
    try:
        for t in lex.tokenize(data, filename=(args.file or "<stdin>")):
            print(t)
    except LexerError as e:
        print("Lexical error:", e)
        sys.exit(2)
