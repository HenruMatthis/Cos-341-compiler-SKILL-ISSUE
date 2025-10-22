# test_semantic.py
"""
Comprehensive test suite for semantic analyzer (Tasks 5 & 6).
Tests scope checking and type checking.
"""

import sys
import os

# Add parent directory to path to import modules
# This allows importing from the project root when running from Tests folder
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Debug: Print the path being added
print(f"Adding to Python path: {parent_dir}")
print(f"Files in parent directory: {os.listdir(parent_dir)[:10]}")  # Show first 10 files

from lexer import Lexer
from parser_spl import Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError


def print_symbol_table_snapshot(analyzer: SemanticAnalyzer):
    """Print the full multi-scope story."""
    analyzer.print_full_symbol_story()


def test_case(name: str, source: str, should_fail: bool = False):
    """Run a single test case."""
    print("\n" + "="*70)
    print(f"TEST: {name}")
    print("="*70)
    print("Source code:")
    print(source)
    print("-"*70)
    
    try:
        # Lex
        lexer = Lexer()
        tokens = list(lexer.tokenize(source))
        
        # Parse
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Semantic analysis
        analyzer = SemanticAnalyzer()
        symbol_table = analyzer.analyze(ast)
        
        if should_fail:
            print("❌ FAIL: Expected semantic error but compilation succeeded")
            print_symbol_table_snapshot(analyzer)
            return False
        else:
            print("✅ PASS: Compilation successful")
            print_symbol_table_snapshot(analyzer)
            return True
            
    except SemanticError as e:
        if should_fail:
            print(f"✅ PASS: Caught expected error:\n   {e.message}")
            return True
        else:
            print(f"❌ FAIL: Unexpected semantic error:\n   {e.message}")
            return False
    
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception:\n   {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all semantic analysis tests."""
    results = []
    
    # ==================== SCOPE CHECKING TESTS ====================
    
    # Test 1: Valid simple program
    results.append(test_case(
        "Valid Simple Program",
        """
        glob { x y }
        proc { }
        func { }
        main {
            var { z }
            x = 10;
            y = (x plus 5);
            z = y
        }
        """,
        should_fail=False
    ))
    
    # Test 2: Duplicate global variable
    results.append(test_case(
        "Duplicate Global Variable",
        """
        glob { x x }
        proc { }
        func { }
        main { var { } halt }
        """,
        should_fail=True
    ))
    
    # Test 3: Duplicate local variable
    results.append(test_case(
        "Duplicate Local Variable in Main",
        """
        glob { }
        proc { }
        func { }
        main {
            var { a a }
            halt
        }
        """,
        should_fail=True
    ))
    
    # Test 4: Shadowing parameter with local
    results.append(test_case(
        "Shadowing Parameter with Local Variable",
        """
        glob { }
        proc {
            pdef myproc(x) {
                local { x }
                halt
            }
        }
        func { }
        main { var { } halt }
        """,
        should_fail=True
    ))
    
    # Test 5: Valid function with parameters and locals
    results.append(test_case(
        "Valid Function with Parameters and Locals",
        """
        glob { }
        proc { }
        func {
            fdef add(a b) {
                local { result }
                result = (a plus b);
                return result
            }
        }
        main { var { } halt }
        """,
        should_fail=False
    ))
    
    # Test 6: Undefined variable usage
    results.append(test_case(
        "Undefined Variable",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            y = 10
        }
        """,
        should_fail=True
    ))
    
    # Test 7: Global name clash (variable and function with same name)
    results.append(test_case(
        "Global Name Clash - Variable and Function",
        """
        glob { compute }
        proc { }
        func {
            fdef compute(x) {
                local { }
                halt;
                return x
            }
        }
        main { var { } halt }
        """,
        should_fail=True
    ))
    
    # Test 8: Valid nested scopes
    results.append(test_case(
        "Valid Nested Scopes",
        """
        glob { global1 }
        proc {
            pdef proc1(param1 param2) {
                local { local1 }
                global1 = param1;
                local1 = param2
            }
        }
        func {
            fdef func1(param3) {
                local { local2 local3 }
                local2 = param3;
                local3 = global1;
                return local2
            }
        }
        main {
            var { main1 main2 }
            main1 = 5;
            main2 = func1(main1);
            proc1(main1 main2)
        }
        """,
        should_fail=False
    ))
    
    # ==================== TYPE CHECKING TESTS ====================
    
    # Test 9: Valid arithmetic operations
    results.append(test_case(
        "Valid Arithmetic Operations",
        """
        glob { a b c }
        proc { }
        func { }
        main {
            var { }
            a = 10;
            b = 20;
            c = (a plus b);
            c = (c minus 5);
            c = (c mult 2);
            c = (c div 3)
        }
        """,
        should_fail=False
    ))
    
    # Test 10: Valid comparison operations
    results.append(test_case(
        "Valid Comparison Operations",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            x = 10;
            if (x > 5) {
                x = 100
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 11: Valid logical operations in loop
    results.append(test_case(
        "Valid Logical Operations",
        """
        glob { counter }
        proc { }
        func { }
        main {
            var { }
            counter = 0;
            while ((counter > 0) and (counter > 10)) {
                counter = (counter plus 1)
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 12: Invalid - using numeric in boolean context
    results.append(test_case(
        "Invalid Boolean Context - Numeric Condition",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            x = 10;
            if x {
                halt
            }
        }
        """,
        should_fail=True
    ))
    
    # Test 13: Invalid - logical operator on numeric
    results.append(test_case(
        "Invalid Logical Operator on Numeric",
        """
        glob { a b }
        proc { }
        func { }
        main {
            var { c }
            a = 5;
            b = 10;
            c = (a and b)
        }
        """,
        should_fail=True
    ))
    
    # Test 14: Valid - negation of numeric
    results.append(test_case(
        "Valid Negation of Numeric",
        """
        glob { x result }
        proc { }
        func { }
        main {
            var { }
            x = 42;
            result = (neg x)
        }
        """,
        should_fail=False
    ))
    
    # Test 15: Valid - not operator on boolean
    results.append(test_case(
        "Valid NOT Operator on Boolean",
        """
        glob { x y }
        proc { }
        func { }
        main {
            var { }
            x = 10;
            y = 20;
            if (not (x > y)) {
                halt
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 16: Invalid - arithmetic on boolean
    results.append(test_case(
        "Invalid Arithmetic on Boolean",
        """
        glob { x y }
        proc { }
        func { }
        main {
            var { z }
            x = 5;
            y = 10;
            z = ((x > y) plus 5)
        }
        """,
        should_fail=True
    ))
    
    # Test 17: Valid - complex nested expressions
    results.append(test_case(
        "Valid Complex Nested Expressions",
        """
        glob { a b c }
        proc { }
        func { }
        main {
            var { }
            a = 10;
            b = 20;
            c = ((a plus b) mult ((b minus a) div 2))
        }
        """,
        should_fail=False
    ))
    
    # Test 18: Valid - do-until loop with boolean condition
    results.append(test_case(
        "Valid Do-Until Loop",
        """
        glob { counter }
        proc { }
        func { }
        main {
            var { }
            counter = 0;
            do {
                counter = (counter plus 1)
            } until (counter > 10)
        }
        """,
        should_fail=False
    ))
    
    # Test 19: Invalid - numeric in do-until condition
    results.append(test_case(
        "Invalid Do-Until Condition",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            x = 0;
            do {
                x = (x plus 1)
            } until x
        }
        """,
        should_fail=True
    ))
    
    # Test 20: Valid - function call in assignment
    results.append(test_case(
        "Valid Function Call in Assignment",
        """
        glob { result }
        proc { }
        func {
            fdef multiply(x y) {
                local { temp }
                temp = (x mult y);
                return temp
            }
        }
        main {
            var { }
            result = multiply(5 10)
        }
        """,
        should_fail=False
    ))
    
    # Test 21: Invalid - calling undefined function
    results.append(test_case(
        "Undefined Function Call",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            x = undefined(5)
        }
        """,
        should_fail=True
    ))
    
    # Test 22: Valid - procedure call
    results.append(test_case(
        "Valid Procedure Call",
        """
        glob { global1 }
        proc {
            pdef setvalue(newval) {
                local { }
                global1 = newval
            }
        }
        func { }
        main {
            var { }
            setvalue(42)
        }
        """,
        should_fail=False
    ))
    
    # Test 23: Invalid - calling undefined procedure
    results.append(test_case(
        "Undefined Procedure Call",
        """
        glob { }
        proc { }
        func { }
        main {
            var { }
            undefined(10)
        }
        """,
        should_fail=True
    ))
    
    # Test 24: Valid - print with variable and string
    results.append(test_case(
        "Valid Print Statements",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { }
            x = 42;
            print x;
            print "hello"
        }
        """,
        should_fail=False
    ))
    
    # Test 25: Valid - if-else with proper boolean conditions
    results.append(test_case(
        "Valid If-Else Statement",
        """
        glob { x y }
        proc { }
        func { }
        main {
            var { }
            x = 10;
            y = 20;
            if (x > y) {
                x = 100
            } else {
                y = 200
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 26: Invalid - or operator with numeric operands
    results.append(test_case(
        "Invalid OR Operator with Numeric",
        """
        glob { a b }
        proc { }
        func { }
        main {
            var { }
            a = 5;
            b = 10;
            if (a or b) {
                halt
            }
        }
        """,
        should_fail=True
    ))
    
    # Test 27: Valid - complex boolean expression
    results.append(test_case(
        "Valid Complex Boolean Expression",
        """
        glob { x y z }
        proc { }
        func { }
        main {
            var { }
            x = 5;
            y = 10;
            z = 15;
            if (((x > y) or (y > z)) and (not (x eq z))) {
                halt
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 28: Valid - equality comparison
    results.append(test_case(
        "Valid Equality Comparison",
        """
        glob { a b }
        proc { }
        func { }
        main {
            var { }
            a = 10;
            b = 10;
            if (a eq b) {
                print "equal"
            }
        }
        """,
        should_fail=False
    ))
    
    # Test 29: Invalid - not operator on numeric
    results.append(test_case(
        "Invalid NOT Operator on Numeric",
        """
        glob { x }
        proc { }
        func { }
        main {
            var { y }
            x = 10;
            y = (not x)
        }
        """,
        should_fail=True
    ))
    
    # Test 30: Valid - multiple parameters (max 3)
    results.append(test_case(
        "Valid Multiple Parameters",
        """
        glob { }
        proc {
            pdef procparams(a b c) {
                local { }
                print a;
                print b;
                print c
            }
        }
        func {
            fdef funcparams(x y z) {
                local { temp }
                temp = (x plus (y plus z));
                return temp
            }
        }
        main {
            var { result }
            result = funcparams(1 2 3);
            procparams(10 20 30)
        }
        """,
        should_fail=False
    ))
    
    # Test 31: Valid - accessing variables from outer scope
    results.append(test_case(
        "Valid Scope Access - Outer Variables",
        """
        glob { global1 global2 }
        proc {
            pdef useglobal(param1) {
                local { local1 }
                local1 = global1;
                global2 = param1
            }
        }
        func { }
        main {
            var { main1 }
            global1 = 5;
            main1 = global1;
            useglobal(main1)
        }
        """,
        should_fail=False
    ))
    
    # Test 32: Invalid - calling function as procedure
    results.append(test_case(
        "Invalid Call Function as Procedure",
        """
        glob { }
        proc { }
        func {
            fdef myfunc(x) {
                local { }
                halt;
                return x
            }
        }
        main {
            var { }
            myfunc(10)
        }
        """,
        should_fail=True
    ))
    
    # Test 33: Invalid - calling procedure as function
    results.append(test_case(
        "Invalid Call Procedure as Function",
        """
        glob { }
        proc {
            pdef myproc(x) {
                local { }
                print x
            }
        }
        func { }
        main {
            var { result }
            result = myproc(10)
        }
        """,
        should_fail=True
    ))
    
    # Test 34: Valid - empty parameter lists
    results.append(test_case(
        "Valid Empty Parameter Lists",
        """
        glob { x }
        proc {
            pdef noparams() {
                local { }
                x = 100
            }
        }
        func {
            fdef returnfive() {
                local { }
                halt;
                return 5
            }
        }
        main {
            var { }
            x = returnfive();
            noparams()
        }
        """,
        should_fail=False
    ))
    
    # Test 35: Valid - nested while loops
    results.append(test_case(
        "Valid Nested While Loops",
        """
        glob { i j }
        proc { }
        func { }
        main {
            var { }
            i = 0;
            while (i > 10) {
                j = 0;
                while (j > 5) {
                    j = (j plus 1)
                };
                i = (i plus 1)
            }
        }
        """,
        should_fail=False
    ))
    
    # ==================== SUMMARY ====================
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print("="*70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)