# Semester Project Phase 1: Lexer (Tokenizer)


**Language:** Python  
**Section:** 1 — Lexer: The Tokenizer  

---

## Overview

This is the lexer (tokenizer) for the SPL (Students’ Programming Language) compiler.  
It is the first phase of the compiler front-end and is responsible for:

- Reading source code from `.spl` / `.txt` files.
- Converting raw characters into a sequential stream of tokens.
- Discarding whitespace, tabs, newlines, and comments.
- Reporting lexical errors with exact line/column positions.

This design cleanly separates tokenization from parsing, making the next phase (parser) simpler and more robust.

---

## Master Token List

We implemented an exhaustive master token list covering:

- **Keywords:** `glob`, `proc`, `func`, `main`, `if`, `else`, `while`, `return`, `true`, `false`, `and`, `or`, `not`, `print`, `string`, `int`, `var`, `const`  
- **Operators:** `+`, `-`, `*`, `/`, `%`, `<`, `>`, `<=`, `>=`, `==`, `!=`, `->`, `=` (assignment)  
- **Punctuation / Delimiters:** `( ) { } [ ] ; , : .`  
- **Identifiers:** user-defined names, matched by `[A-Za-z_][A-Za-z0-9_]*`  
- **Literals:** numbers (integers and floats with exponents), strings (single or double quoted, with escape support)  
- **Catch-all for errors:** `MISMATCH` ensures illegal characters raise a `LexerError`.

**Implementation location:**  
See `lexer.py` → `Lexer.DEFAULT_TOKEN_SPEC` and `Lexer.DEFAULT_KEYWORDS`.

---

## Regular Expressions

Each token type has a precise regular expression:

- **Identifiers:** `[A-Za-z_][A-Za-z0-9_]*`  
- **Numbers:** integers (`\d+`), decimals (`\d+\.\d+`), and scientific notation (`6.02e23`)  
- **Strings:** `"(?:\\.|[^"\\])*"` or `'(?:\\.|[^'\\])*'` — allows escaped characters inside quotes  
- **Whitespace & comments:** have separate patterns so they can be skipped entirely

**Implementation location:**  
See `lexer.py` → `DEFAULT_TOKEN_SPEC`.

---

## Whitespace and Comment Handling

Our lexer:

- Skips whitespace and newlines (no tokens produced)  
- Correctly updates line/column numbers when skipping newlines  
- Handles three comment styles:
  - `//` single line
  - `/* */` multi-line
  - `#` single line

Comments are discarded, but line numbers are still counted for accurate error reporting.

**Implementation location:**  
See `Lexer.tokenize` → branches for `SKIP`, `NEWLINE`, `MCOMMENT`, `SCOMMENT`, `HASHCOMMENT`.

---

## Token Stream Creation

The lexer outputs a sequential token stream — a list or iterator of `Token` objects, each containing:

- **type:** token type (e.g., `ID`, `NUMBER`, `ASSIGN`, `PRINT`)  
- **value:** only for identifiers & literals (e.g., `counter`, `42`, `"hello"`)  
- **line / column:** precise source location  
- **index:** character index in file (for debugging / parser lookahead)

Example (from `demo.spl`):

```python
Token(type='GLOB', value=None, line=1, column=1, index=0)
Token(type='ID', value='x', line=1, column=6, index=5)
Token(type='ASSIGN', value='=', line=1, column=8, index=7)
Token(type='NUMBER', value=10, line=1, column=10, index=9)
...
```

**Implementation location:** 
See `lexer.py` → `Lexer.tokenize` (yields Token dataclass instances).

## Lexical Error Handling
Invalid characters are caught by the `MISMATCH` token and reported immediately:

```python
Lexical error: Illegal character '$' at <input>:3:7
```

This prevents the parser from receiving bad input and makes debugging easier.

## Testing

We wrote unit tests using Python’s unittest framework (test_lexer.py):

- test_identifier_and_keyword → verifies glob recognized as keyword and identifier tokenization
- test_numbers → verifies integers, floats, and scientific notation
- test_strings_and_escape → verifies string literal decoding and escape sequence handling
- test_comments_ignored → verifies that comments are removed from the token stream
- test_illegal_char → verifies that illegal characters raise LexerError

 Run tests:
  ```
  python -m unittest test_lexer.py
  ```

## Running the Lexer
To tokenize a file:
```
python lexer.py demo.spl
```

Or to run interactively (paste code into stdin):
```
python lexer.py
```