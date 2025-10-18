# print_asts.py
# Runs the parser on a list of test programs and pretty-prints the resulting AST.

import sys
import re
from lexer import Lexer, LexerError
from parser_spl import Parser, ParseError
from ast_nodes import * # Import all AST node classes

# List of programs to test, as provided
TEST_PROGRAMS = [
    # 1 Minimal valid program — no functions, procs, or vars
    (
        "Minimal SPL Program",
        """
        glob { }
        proc { }
        func { }
        main { var { } halt }
        """
    ),

    # 2 VARIABLES — single and multiple variables
    (
        "Global and Local Variable Declarations",
        """
        glob { a b c }
        proc { }
        func { }
        main { var { x y z } halt }
        """
    ),

    # 3 PROCDEFS — procedure with local vars and algorithm
    (
        "Simple Procedure Definition",
        """
        glob { }
        proc {
            pdef greet(name) {
                local { msg }
                print "hello";
                print name;
                halt
            }
        }
        func { }
        main { var { } halt }
        """
    ),

    # 4 FUNCDEFS — function returning atom
    (
        "Simple Function Definition with Return",
        """
        glob { }
        proc { }
        func {
            fdef add(a b) {
                local { sum }
                sum = (a plus b);
                return sum
            }
        }
        main { var { } halt }
        """
    ),

    # 5 MAINPROG — with local vars and algo
    (
        "Main Program with Algorithm",
        """
        glob { }
        proc { }
        func { }
        main {
            var { x y }
            x = 5;
            y = (x plus 3);
            print y;
            halt
        }
        """
    ),

    # 6 ASSIGN — assignment with function call
    (
        "Assignment Using Function Call",
        """
        glob { }
        proc { }
        func {
            fdef double(n) {
                local { temp }
                temp = (n plus n);
                return temp
            }
        }
        main {
            var { x }
            x = double(5);
            print x;
            halt
        }
        """
    ),

    # 7 LOOP — while + do-until
    (
        "While and Do-Until Loops",
        """
        glob { }
        proc { }
        func { }
        main {
            var { i }
            i = 0;
            while (i > 0) {
                print i;
                i = (i plus 1)
            };
            do {
                print i;
                i = (i minus 1)
            } until (i eq 0);
            halt
        }
        """
    ),

    # 8 BRANCH — if / else
    (
        "If-Else Branching",
        """
        glob { }
        proc { }
        func { }
        main {
            var { x }
            x = 10;
            if (x > 5) {
                print "hello"
            } else {
                print "ok"
            };
            halt
        }
        """
    ),

    # 9 TERM — unary and binary operations
    (
        "Unary and Binary Terms",
        """
        glob { }
        proc { }
        func { }
        main {
            var { a }
            a = (neg (a plus 1));
            print a;
            halt
        }
        """
    ),

    # 10 MAXTHREE — ensure 3 locals is valid
    (
        "Procedure with 3 Local Variables",
        """
        glob { }
        proc {
            pdef demo(a) {
                local { x y z }
                halt
            }
        }
        func { }
        main { var { } halt }
        """
    ),

    # 11 INPUT — function with up to 3 inputs
    (
        "Function with Multiple Inputs",
        """
        glob { }
        proc { }
        func {
            fdef mix(a b c) {
                local { result }
                result = (a plus (b mult c));
                return result
            }
        }
        main {
            var { x }
            x = mix(1 2 3);
            print x;
            halt
        }
        """
    ),

    # 12 ERROR CASE — too many locals
    (
        "Invalid: More than 3 Local Variables",
        """
        glob { }
        proc {
            pdef bad(a) {
                local { x y z w }
                halt
            }
        }
        func { }
        main { var { } halt }
        """
    ),

    # 13 ERROR CASE — missing return
    (
        "Invalid Function (Missing Return)",
        """
        glob { }
        proc { }
        func {
            fdef broken(a) {
                local {}
                a = (a plus 1);
            }
        }
        main { var { } halt }
        """
    ),
]


def setup_lexer():
    """Applies patches to the Lexer class for consistency."""
    required_keywords = {
        'glob': 'GLOB', 'proc': 'PROC', 'func': 'FUNC', 'main': 'MAIN',
        'var': 'VAR', 'local': 'LOCAL', 'return': 'RETURN', 'halt': 'HALT',
        'print': 'PRINT', 'while': 'WHILE', 'do': 'DO', 'until': 'UNTIL',
        'if': 'IF', 'else': 'ELSE', 'neg': 'NEG_WORD', 'not': 'NOT',
        'eq': 'EQ_WORD', 'or': 'OR', 'and': 'AND', 'plus': 'PLUS_WORD',
        'minus': 'MINUS_WORD', 'mult': 'MULT_WORD', 'div': 'DIV_WORD',
        'fdef': 'FDEF', 'pdef': 'PDEF', 'algo': 'ALGO'
    }
    if not hasattr(Lexer, 'DEFAULT_KEYWORDS'): Lexer.DEFAULT_KEYWORDS = {}
    Lexer.DEFAULT_KEYWORDS.update(required_keywords)
    if not hasattr(Lexer, 'DEFAULT_TOKEN_SPEC'): Lexer.DEFAULT_TOKEN_SPEC = []
    
    spec_updated = False
    assign_index = -1
    has_assign = False
    for i, (name, _) in enumerate(Lexer.DEFAULT_TOKEN_SPEC):
        if name == 'EQUALS': assign_index = i; spec_updated = True; break
        if name == 'ASSIGN': has_assign = True; break
    if assign_index != -1: Lexer.DEFAULT_TOKEN_SPEC[assign_index] = ('ASSIGN', r'=')
    elif not has_assign and ('ASSIGN', r'=') not in [t[0] for t in Lexer.DEFAULT_TOKEN_SPEC]:
         insert_before = next((i for i, t in enumerate(Lexer.DEFAULT_TOKEN_SPEC) if t[0] in ('NEWLINE', 'MISMATCH')), len(Lexer.DEFAULT_TOKEN_SPEC))
         Lexer.DEFAULT_TOKEN_SPEC.insert(insert_before, ('ASSIGN', r'='))
         spec_updated = True
    
    if spec_updated and hasattr(Lexer, 'DEFAULT_TOKEN_SPEC'):
         try: Lexer.master_pattern = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in Lexer.DEFAULT_TOKEN_SPEC))
         except AttributeError: pass
         except re.error: print("Warning: Regex error during test setup.", file=sys.stderr)

def run_and_print_asts():
    """
    Iterates through test programs, parses them, and pretty-prints the AST.
    """
    
    # Apply lexer patches first
    setup_lexer()

    print(f"--- Printing ASTs for {len(TEST_PROGRAMS)} Test Programs ---")

    for name, source in TEST_PROGRAMS:
        print("\n" + "="*50)
        print(f"Running: {name}")
        print("="*50)
        
        source = source.strip() # Clean up indentation
        print("--- Source ---")
        print(source)
        
        try:
            lexer = Lexer()
            tokens = list(lexer.tokenize(source, filename=name))
            parser = Parser(tokens)
            ast = parser.parse()
            
            print("\n--- AST ---")
            print(ast.pretty_print())
            
        except (ParseError, LexerError) as e:
            print("\n--- PARSE FAILED ---")
            print(f"Error: {e}")
        except Exception as e:
            print("\n--- UNEXPECTED SCRIPT ERROR ---")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    run_and_print_asts()