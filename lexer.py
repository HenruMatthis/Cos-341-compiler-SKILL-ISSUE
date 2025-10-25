# lexer.py  (tightened version)
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

    def __repr__(self):
        val_repr = f", value={self.value!r}" if self.value is not None else ""
        return f"Token(type='{self.type}'{val_repr}, line={self.line}, col={self.column})"

class LexerError(Exception):
    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.line = line
        self.column = column

class Lexer:
    """Regex-based Lexer for SPL – rejects every illegal character."""
    DEFAULT_TOKEN_SPEC: List[Tuple[str, str]] = [
        ('SKIP',         r'[ \t\r]+'),
        ('COMMENT',      r'//.*'),
        ('NUMBER',       r'(0|[1-9][0-9]*)'),
        ('STRING',       r'"[a-z0-9 ]{0,15}"'),
        ('LBRACE',       r'\{'),
        ('RBRACE',       r'\}'),
        ('LPAREN',       r'\('),
        ('RPAREN',       r'\)'),
        ('SEMICOLON',    r';'),
        ('ASSIGN',       r'='),
        ('GT',           r'>'),
        ('COMMA',        r','),
        ('ID',           r'[a-z][a-z]*[0-9]*'),
        ('NEWLINE',      r'\n+'),
        ('MISMATCH',     r'.'),          # <-- catches everything else
    ]

    DEFAULT_KEYWORDS: Dict[str, str] = {
        'glob': 'GLOB', 'proc': 'PROC', 'func': 'FUNC', 'main': 'MAIN',
        'var': 'VAR', 'local': 'LOCAL', 'return': 'RETURN', 'halt': 'HALT',
        'print': 'PRINT', 'while': 'WHILE', 'do': 'DO', 'until': 'UNTIL',
        'if': 'IF', 'else': 'ELSE',
        'neg': 'NEG_WORD', 'not': 'NOT',
        'eq': 'EQ_WORD', 'or': 'OR', 'and': 'AND',
        'plus': 'PLUS_WORD', 'minus': 'MINUS_WORD',
        'mult': 'MULT_WORD', 'div': 'DIV_WORD',
        'fdef': 'FDEF', 'pdef': 'PDEF', 'algo': 'ALGO'
    }

    master_pattern = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in DEFAULT_TOKEN_SPEC))
    _keyword_values_lookup = {v: k for k, v in DEFAULT_KEYWORDS.items()}

    # ---------- token generators ----------
    def tokenize(self, text: str, filename: str = "<input>") -> Iterator[Token]:
        lineno = 1
        line_start = 0
        pos = 0
        end = len(text)
        while pos < end:
            m = Lexer.master_pattern.match(text, pos)
            if not m:                               # should never happen
                col = pos - line_start + 1
                raise LexerError(f"Unexpected character '{text[pos]}' at {filename}:{lineno}:{col}", lineno, col)

            typ = m.lastgroup
            val = m.group(typ)
            col = m.start() - line_start + 1
            start_index = m.start()

            if typ == 'NEWLINE':
                lineno += val.count('\n')
                line_start = m.end()
            elif typ in ('SKIP', 'COMMENT'):
                pass
            elif typ == 'ID':
                yield Token(Lexer.DEFAULT_KEYWORDS.get(val, 'ID'),
                           None if val in Lexer.DEFAULT_KEYWORDS else val,
                           lineno, col, start_index)
            elif typ == 'NUMBER':
                yield Token('NUMBER', int(val), lineno, col, start_index)
            elif typ == 'STRING':
                inner = val[1:-1]
                if len(inner) > 15:
                    raise LexerError(f"String literal exceeds 15 characters", lineno, col)
                yield Token('STRING', inner, lineno, col, start_index)
            elif typ == 'MISMATCH':                 # <<-- illegal character
                raise LexerError(f"Illegal character {val!r}", lineno, col)
            else:                                   # punctuation
                yield Token(typ, None, lineno, col, start_index)
            pos = m.end()

        yield Token('EOF', None, lineno, pos - line_start + 1, pos)

    def tokenize_file(self, path: str) -> Iterator[Token]:
        try:
            with open(path, encoding='utf-8') as f:
                yield from self.tokenize(f.read(), filename=path)
        except FileNotFoundError:
            raise LexerError(f"File not found: {path}")
        except Exception as e:
            raise LexerError(f"Error reading file {path}: {e}")