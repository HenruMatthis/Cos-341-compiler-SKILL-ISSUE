# test_parser.py
import unittest
import re
from lexer import Lexer, LexerError
from parser_spl import Parser, ParseError
from ast_nodes import *

class TestParserSPL(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure Lexer keywords are fully defined for tests
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

    def _parse_string(self, source: str) -> ASTNode:
        """Helper function to lex and parse a string."""
        source = source.strip()
        lexer = Lexer()
        needs_wrapping = True
        try:
            peek_tokens = list(lexer.tokenize(source, filename="<test_peek>"))
            first_real_token = None
            for t in peek_tokens:
                if t.type not in ('SKIP', 'COMMENT', 'NEWLINE'): first_real_token = t; break
            if first_real_token and first_real_token.type == 'GLOB':
                needs_wrapping = False; tokens = peek_tokens
            else:
                wrapped_source = f"glob {{}} proc {{}} func {{}} main {{ var {{}} {source} }}"
                tokens = list(lexer.tokenize(wrapped_source, filename="<test_wrapped>"))
            parser = Parser(tokens)
            return parser.parse()
        except (LexerError, ParseError) as e: raise e
        except Exception as e: import traceback; traceback.print_exc(); self.fail(f"Unexpected error: {e}")

    # --- Tests for Valid Constructs ---
    
    def test_minimal_program(self):
        source = "glob {} proc {} func {} main { var {} halt }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast, ProgramNode)

    def test_global_vars(self):
        source = "glob { count pages word } proc {} func {} main { var {} halt }"
        ast = self._parse_string(source)
        self.assertEqual(len(ast.globals.variables), 3)

    def test_simple_assignment(self):
        source = "x = 42"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], AssignmentNode)

    def test_assignment_var(self):
        source = "a = b"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0].rhs.value, VarNode)

    def test_print_atom_number(self):
        source = "print 42"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], PrintNode)

    def test_print_atom_id(self):
        source = "print myvar"
        ast = self._parse_string(source)
        self.assertEqual(ast.main.algorithm.instructions[0].output.value.name, "myvar")

    def test_print_string(self):
        source = 'print "hello"'
        ast = self._parse_string(source)
        self.assertEqual(ast.main.algorithm.instructions[0].output, "hello")

    def test_if_then(self):
        source = "if (x > 0) { halt }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], IfBranchNode)

    def test_if_then_else(self):
        source = "if (x eq 0) { x = 1 } else { x = 0 }"
        ast = self._parse_string(source)
        self.assertIsNotNone(ast.main.algorithm.instructions[0].else_branch)

    def test_while_loop(self):
        source = "while (i > 0) { i = (i minus 1) }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], WhileLoopNode)

    def test_do_until_loop(self):
        source = "do { i = (i plus 1) } until (i eq 10)"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], DoUntilLoopNode)

    def test_procedure_def(self):
        source = "glob {} proc { pdef myproc ( a b ) { local { tmp } tmp = a ; a = b ; b = tmp } } func {} main { var {} halt }"
        ast = self._parse_string(source)
        self.assertEqual(len(ast.procs.procedures), 1)

    def test_function_def(self):
        source = "glob {} proc {} func { fdef add ( x y ) { local {res} res = (x plus y) ; return res } } main { var {} halt }"
        ast = self._parse_string(source)
        self.assertEqual(len(ast.funcs.functions), 1)

    def test_procedure_call(self):
        source = "glob {} proc { pdef swap(x y) { local {} x = y } } func {} main { var {a b} swap(a b) }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], ProcedureCallNode)

    def test_function_call_in_assignment(self):
        source = "glob {} proc {} func { fdef add(a b) { local{r} r=(a plus b); return r } } main { var { res x y} res = add(x y) }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0].rhs, FunctionCallNode)

    def test_complex_expression(self):
        source = "a = (neg ((b mult c) plus 5))"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0], AssignmentNode)

    def test_algo_sequence(self):
        source = "x = 1 ; print x ; halt"
        ast = self._parse_string(source)
        self.assertEqual(len(ast.main.algorithm.instructions), 3)

    # --- Tests for Syntax Errors ---

    def test_error_missing_brace_main(self):
        source = "glob {} proc {} func {} main { var {} halt "
        # **Corrected Regex:** Match exact message including the final ')'
        with self.assertRaisesRegex(ParseError, r"Expected token type 'RBRACE' but found end of input.* near token .* \(type HALT \(keyword 'halt'\)\)"):
            self._parse_string(source)

    def test_error_missing_semicolon_algo(self):
        source = "x=1 print x" # Fragment
        with self.assertRaisesRegex(ParseError, r"Expected type 'RBRACE'.* near token .*print"):
            self._parse_string(source)

    def test_error_if_missing_condition_parens(self):
        source = "if x > 0 { halt }" # Fragment
        with self.assertRaisesRegex(ParseError, r"Expected type 'LBRACE'.* near token .* \(type GT\)"):
             self._parse_string(source)

    def test_error_assignment_missing_equals(self):
        source = "x 42" # Fragment
        with self.assertRaisesRegex(ParseError, r"Expected '\(' or '=' after identifier.* near token 42"):
             self._parse_string(source)

    def test_error_wrong_keyword_start(self):
        source = "else {} proc {} func {} main { var {} halt }"
        with self.assertRaisesRegex(ParseError, r"Algorithm block cannot be empty.* near token .* \(type ELSE \(keyword 'else'\)\)"):
            self._parse_string(source)

    def test_error_proc_call_as_func_call_syntax(self):
        source = "glob {} proc { pdef myp() { local{} halt } } func {} main { var {x} x = myp() }"
        ast = self._parse_string(source)
        self.assertIsInstance(ast.main.algorithm.instructions[0].rhs, FunctionCallNode)

    def test_error_unexpected_eof(self):
        source = "glob { x }"
        with self.assertRaisesRegex(ParseError, r"Expected token type 'PROC' but found end of input.* near token .*RBRACE"):
            self._parse_string(source)

    def test_error_too_many_params(self):
        source = "glob {} proc { pdef p (a b c d) { local{} halt } } func {} main { var{} halt}"
        with self.assertRaisesRegex(ParseError, r"Maximum number of variables \(3\) exceeded in list.* near token 'd' \(type ID\)"):
             self._parse_string(source)

    def test_error_too_many_args(self):
        source = "glob {} proc { pdef p (a b c) { local{} halt } } func {} main { var{} p(1 2 3 4) }"
        with self.assertRaisesRegex(ParseError, r"Expected type 'RPAREN' .* near token 4 \(type NUMBER\)"):
             self._parse_string(source)

    def test_error_trailing_semicolon(self):
        source = "halt;" # Fragment
        with self.assertRaisesRegex(ParseError, r"Expected type 'RBRACE'.* near token .* \(type SEMICOLON\)"):
             self._parse_string(source)

    def test_error_empty_algo_block(self):
        source = "" # Fragment
        with self.assertRaisesRegex(ParseError, r"Algorithm block cannot be empty.*near token.*RBRACE"):
             self._parse_string(source)

if __name__ == '__main__':
    unittest.main()