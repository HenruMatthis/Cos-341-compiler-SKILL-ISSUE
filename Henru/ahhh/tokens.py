import re

# -------------------------------
# 1. Master Token List
# -------------------------------
KEYWORDS = {
    "glob", "proc", "func", "main", "var", "local", "return", "halt", "print",
    "while", "do", "until", "if", "else", "neg", "not", "eq", "or", "and",
    "plus", "minus", "mult", "div", "fdef", "pdef", "algo"  # Lowercase for simulation
}

TOKEN_REGEX = re.compile(r"""
    (?P<WHITESPACE>\s+) |
    (?P<COMMENT>//.*(?:\n|$)) |
    (?P<LBRACE>\{) |
    (?P<RBRACE>\}) |
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<SEMICOLON>;) |
    (?P<EQUALS>=) |
    (?P<GT>>) |
    (?P<NUMBER>(0|[1-9][0-9]*)) |
    (?P<STRING>"[a-z0-9]{0,15}") |
    (?P<IDENTIFIER>[a-z][a-z]*[0-9]*)
""", re.VERBOSE)

# -------------------------------
# 2. Token Class
# -------------------------------
class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})" if self.value else f"Token({self.type})"

# -------------------------------
# 3. Lexer Class
# -------------------------------
class SimpleLexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.warnings = []  # For unrecognized chars

    def tokenize(self):
        tokens = []
        pos = 0
        while pos < len(self.source_code):
            match = TOKEN_REGEX.match(self.source_code, pos)
            if not match:
                # Skip unrecognized (log warning)
                char = self.source_code[pos]
                self.warnings.append(f"Unrecognized character '{char}' at position {pos}")
                pos += 1
                continue
            kind = match.lastgroup
            value = match.group()
            pos = match.end()

            if kind in ("WHITESPACE", "COMMENT"):
                continue

            if kind == "IDENTIFIER" and value in KEYWORDS:
                kind = "KEYWORD"

            if kind in ("IDENTIFIER", "NUMBER", "STRING", "KEYWORD"):
                if kind == "STRING":
                    value = value[1:-1]  # Remove quotes
                tokens.append(Token(kind, value))
            else:
                tokens.append(Token(kind))

        tokens.append(Token("EOF"))
        return tokens, self.warnings

# Adjusted Test cases (lowercase for compliance)
test_cases = {
    "Simple main": """
        main { var { w } print ( x plus y ) }
    """,

    "Function with return": """
        func { fdef func1 ( b ) { local { z } algo ; return 42 } }
    """,

    "Proc with nested": """
        proc { pdef proc1 ( a ) { local { y } algo } }
    """,

    "Numbers only": """
        var { x } x = 42
    """,

    "String test": """
        print ("hello123") var { name } name = "janri"
    """,

    "With comments": """
        // this is a comment
        glob { x } // another comment
    """
}

def run_tests():
    for name, code in test_cases.items():
        print("=" * 40)
        print(f"Test Case: {name}")
        print("-" * 40)

        lexer = SimpleLexer(code)
        tokens, warnings = lexer.tokenize()
        for token in tokens:
            print(token)
        if warnings:
            print("Warnings:", warnings)
        print()

if __name__ == "__main__":
    run_tests()