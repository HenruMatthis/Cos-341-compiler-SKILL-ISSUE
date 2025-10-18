# test_parser.py
from lexer import Lexer
from parser import Parser
from syntax_tree import ASTNode

# --- SPL TEST PROGRAMS COVERING EACH GRAMMAR RULE ---

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
            greet(name) {
                local { msg }
                print "Hello";
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
            add(a b) {
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
            double(n) {
                n = (n plus n);
                return n
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
            while (i < 3) {
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
                print "Big"
            } else {
                print "Small"
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

    # 10 MAXTHREE — ensure not more than 3 locals
    (
        "Procedure with 3 Local Variables",
        """
        glob { }
        proc {
            demo(a) {
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
            mix(a b c) {
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
            bad(a) {
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
            broken(a) {
                a = (a plus 1);
            }
        }
        main { var { } halt }
        """
    ),
]

# --- RUNNER ---
def run_test(name, source):
    print(f" Running Test: {name}")
    print("─" * 90)
    try:
        lexer = Lexer()
        tokens = list(lexer.tokenize(source))
        parser = Parser(tokens)
        tree = parser.parse_program()
        tree.pretty_print()
        print(" PASSED\n")
    except SyntaxError as e:
        print(f" SYNTAX ERROR: {e}\n")
    except Exception as e:
        print(f" RUNTIME ERROR: {type(e).__name__}: {e}\n")
    print("=" * 90, "\n")


if __name__ == "__main__":
    for name, src in TEST_PROGRAMS:
        run_test(name, src)
