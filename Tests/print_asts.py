# print_asts.py
# Runs the parser on valid test cases and pretty-prints the resulting AST.

import unittest
import sys
import re
from test_parser import TestParserSPL # Import the test class
from parser_spl import ParseError     # Import ParseError
from lexer import Lexer, LexerError   # *** FIX: Import LexerError ***

def run_and_print_asts():
    """
    Iterates through valid tests in TestParserSPL, parses them,
    and pretty-prints the AST.
    """
    
    # --- Apply the same setUpClass patches as the test ---
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
         except re.error: print("Warning: Regex error during test setup.")
    # --- End of setup patch ---

    # Get all test method names from the test class
    test_methods = [method for method in dir(TestParserSPL)
                    if method.startswith('test_') and not method.startswith('test_error_')]

    print(f"--- Printing ASTs for {len(test_methods)} Valid Test Cases ---")
    
    # Create an instance of the test class to access its helper
    test_instance = TestParserSPL()

    # Redefine sources here for clarity and independence from test internals
    test_sources = {
        'test_minimal_program': "glob {} proc {} func {} main { var {} halt }",
        'test_global_vars': "glob { count pages word } proc {} func {} main { var {} halt }",
        'test_simple_assignment': "x = 42",
        'test_assignment_var': "a = b",
        'test_print_atom_number': "print 42",
        'test_print_atom_id': "print myvar",
        'test_print_string': 'print "hello"',
        'test_if_then': "if (x > 0) { halt }",
        'test_if_then_else': "if (x eq 0) { x = 1 } else { x = 0 }",
        'test_while_loop': "while (i > 0) { i = (i minus 1) }",
        'test_do_until_loop': "do { i = (i plus 1) } until (i eq 10)",
        'test_procedure_def': "glob {} proc { pdef myproc ( a b ) { local { tmp } tmp = a ; a = b ; b = tmp } } func {} main { var {} halt }",
        'test_function_def': "glob {} proc {} func { fdef add ( x y ) { local {res} res = (x plus y) ; return res } } main { var {} halt }",
        'test_procedure_call': "glob {} proc { pdef swap(x y) { local {} x = y } } func {} main { var {a b} swap(a b) }",
        'test_function_call_in_assignment': "glob {} proc {} func { fdef add(a b) { local{r} r=(a plus b); return r } } main { var { res x y} res = add(x y) }",
        'test_complex_expression': "a = (neg ((b mult c) plus 5))",
        'test_algo_sequence': "x = 1 ; print x ; halt",
        'test_error_proc_call_as_func_call_syntax': "glob {} proc { pdef myp() { local{} halt } } func {} main { var {x} x = myp() }"
    }

    for method_name in test_methods:
        print("\n" + "="*50)
        print(f"Running: {method_name}")
        print("="*50)
        
        if method_name not in test_sources:
            print(f"Source for {method_name} not found in print_asts.py. Skipping.")
            continue
            
        source = test_sources[method_name]
        
        try:
            print("--- Source ---")
            print(source.strip())
            print("\n--- AST ---")
            
            # Use the same helper from the test class
            ast = test_instance._parse_string(source)
            
            # Use the new pretty_print method
            print(ast.pretty_print())
            
        except (ParseError, LexerError) as e:
            print(f"Error during parsing: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    run_and_print_asts()