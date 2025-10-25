# test_code_gen.py
import unittest
import sys
import os
import re
from typing import List

# Add project root to import path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# --- Import necessary classes and exceptions ---
from lexer import Lexer, LexerError
from parser_spl import Parser, ParseError
from semantic_analyzer import SemanticAnalyzer, SemanticError
from symbol_table import SymbolTable, SymbolTableError
from code_gen import CodeGenerator, CodeGenError
from ast_nodes import * # Keep existing import

# Helper function to clean IR lists for comparison
def clean_ir(ir_list: List[str]) -> List[str]:
    """Removes empty lines and strips whitespace from IR lines."""
    return [line.strip() for line in ir_list if line.strip()]

class TestCodeGen(unittest.TestCase):

    def _generate_ir(self, source: str) -> List[str]:
        """
        Helper for simple code fragments run within a minimal main block.
        ALWAYS wraps the source code inside a minimal valid main block.
        """
        source = source.strip()
        # Always wrap the source inside the main block's ALGO part
        wrapped_source = f"glob {{}} proc {{}} func {{}} main {{ var {{}} {source} }}"
        filename = "<test_wrapped>"

        try:
            # 1. Lex
            lexer = Lexer()
            tokens = list(lexer.tokenize(wrapped_source, filename=filename))

            # 2. Parse
            parser = Parser(tokens)
            ast = parser.parse()

            # 3. Semantic Analysis
            analyzer = SemanticAnalyzer()
            symbol_table = analyzer.analyze(ast)

            # 4. Code Generation
            code_gen = CodeGenerator(symbol_table, analyzer.node_types)
            main_algo_node = ast.main.algorithm

            # Reset and generate code ONLY for the main algorithm node
            code_gen.ir_code = []
            code_gen._temp_counter = 0
            code_gen._label_counter = 0
            code_gen._visit(main_algo_node)
            ir_code = code_gen.ir_code

            return clean_ir(ir_code)

        except (LexerError, ParseError, SemanticError, CodeGenError, SymbolTableError) as e:
            raise e
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.fail(f"Unexpected error during IR generation: {e}")

    def _run_full_analysis_codegen(self, full_source: str) -> List[str]:
        """
        Runs full pipeline on complete source code (including glob, proc, func),
        returns IR generated ONLY for the main algorithm block.
        """
        full_source = full_source.strip()
        filename = "<test_full_prog>"
        try:
            # 1. Lex
            lexer = Lexer()
            tokens = list(lexer.tokenize(full_source, filename=filename))

            # 2. Parse
            parser = Parser(tokens)
            ast = parser.parse()

            # 3. Semantic Analysis
            analyzer = SemanticAnalyzer()
            symbol_table = analyzer.analyze(ast)

            # 4. Code Generation
            code_gen = CodeGenerator(symbol_table, analyzer.node_types)
            main_algo_node = ast.main.algorithm # Target the main algorithm

            # Reset and generate code ONLY for the main algorithm node
            code_gen.ir_code = []
            code_gen._temp_counter = 0
            code_gen._label_counter = 0
            code_gen._visit(main_algo_node)
            ir_code = code_gen.ir_code

            return clean_ir(ir_code)

        except (LexerError, ParseError, SemanticError, CodeGenError, SymbolTableError) as e:
            raise e
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.fail(f"Unexpected error during full analysis codegen: {e}")

    # --- Basic Tests (using simple fragment helper _generate_ir) ---
    def test_halt(self):
        source = "halt"
        expected_ir = ["STOP"]
        actual_ir = self._generate_ir(source)
        self.assertEqual(actual_ir, expected_ir)

    def test_print_number(self):
        source = "print 42"
        expected_ir = [
            "t1 = 42",
            "PRINT t1"
        ]
        actual_ir = self._generate_ir(source)
        self.assertEqual(actual_ir, expected_ir)

    def test_print_string(self):
        source = 'print "hello"'
        expected_ir = ['PRINT "hello"']
        actual_ir = self._generate_ir(source)
        self.assertEqual(actual_ir, expected_ir)

    # --- Tests requiring Global/Func/Proc context (using _run_full_analysis_codegen) ---

    def test_print_variable(self):
        full_source = "glob { x } proc {} func {} main { var {} print x }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        self.assertTrue(len(actual_ir) > 0 and actual_ir[0].startswith("PRINT v_x_"))

    def test_assign_number(self):
        full_source = "glob { x } proc {} func {} main { var {} x = 10 }"
        expected_ir_structure = [
            "t1 = 10",
            "v_x_1 = t1" # Unique name may vary slightly
        ]
        actual_ir = self._run_full_analysis_codegen(full_source)
        self.assertEqual(len(actual_ir), 2)
        self.assertEqual(actual_ir[0], expected_ir_structure[0])
        self.assertTrue(actual_ir[1].startswith("v_x_"))
        self.assertTrue(actual_ir[1].endswith("= t1"))

    def test_assign_variable(self):
        full_source = "glob { x y } proc {} func {} main { var {} x = y }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        self.assertEqual(len(actual_ir), 1)
        self.assertTrue(re.match(r"v_x_\d+ = v_y_\d+", actual_ir[0]))

    def test_arithmetic_ops(self):
        full_source = "glob { a b c } proc {} func {} main { var {} a = ((b plus 5) mult c) }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        self.assertEqual(len(actual_ir), 4)
        self.assertTrue(re.match(r"t\d+ = 5", actual_ir[0]))
        self.assertTrue(re.match(r"t\d+ = v_b_\d+ \+ t\d+", actual_ir[1]))
        self.assertTrue(re.match(r"t\d+ = t\d+ \* v_c_\d+", actual_ir[2]))
        self.assertTrue(re.match(r"v_a_\d+ = t\d+", actual_ir[3]))

    def test_negation(self):
        full_source = "glob { x y } proc {} func {} main { var {} x = (neg y) }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        self.assertEqual(len(actual_ir), 2)
        self.assertTrue(re.match(r"t\d+ = - v_y_\d+", actual_ir[0]))
        self.assertTrue(re.match(r"v_x_\d+ = t\d+", actual_ir[1]))

    def test_comparison_in_assignment(self):
        # Needs global 'x', 'a', 'b'
        full_source = "glob { x a b } proc {} func {} main { var {} x = (a > b) }"
        # <<< FIX: Expect SemanticError >>>
        with self.assertRaisesRegex(SemanticError, "Assignment to 'x' requires numeric value, got boolean"):
            self._run_full_analysis_codegen(full_source)

    def test_if_then(self):
        full_source = "glob { x } proc {} func {} main { var {} if (x > 0) { x = 1 } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        # Check key components exist in order
        self.assertTrue(any(line.startswith("IF v_x_") and " THEN L" in line for line in actual_ir))
        if_line_index = next(i for i, line in enumerate(actual_ir) if line.startswith("IF"))
        self.assertTrue(actual_ir[if_line_index + 1].startswith("GOTO L")) # Should jump to exit if condition false
        then_label_line = next(line for line in actual_ir if line.startswith("REM L") and line != actual_ir[-1])
        self.assertTrue(then_label_line in actual_ir[if_line_index + 2:]) # Then label exists after GOTO
        self.assertTrue(any(line.startswith("v_x_") and "= t" in line for line in actual_ir if actual_ir.index(line) > actual_ir.index(then_label_line))) # Assignment after then label
        self.assertTrue(actual_ir[-1].startswith("REM L")) # Exit label is last

    def test_if_then_else(self):
        # Needs global 'x', 'y'
        full_source = "glob {x y} proc {} func {} main { var{} if (x eq y) { x=1 } else { y=1 } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        # Check structure as per spec
        self.assertTrue(any(line.startswith("IF v_x_") and " THEN L" in line for line in actual_ir))
        if_line_index = next(i for i, line in enumerate(actual_ir) if line.startswith("IF"))
        y_assign_index = next(i for i, line in enumerate(actual_ir) if line.startswith("v_y_"))
        self.assertGreater(y_assign_index, if_line_index)
        goto_exit_index = next(i for i, line in enumerate(actual_ir) if line.startswith("GOTO L"))
        self.assertGreater(goto_exit_index, y_assign_index)
        then_label_index = next(i for i, line in enumerate(actual_ir) if line.startswith("REM L") and i > goto_exit_index)
        self.assertGreater(then_label_index, goto_exit_index)
        x_assign_index = next(i for i, line in enumerate(actual_ir) if line.startswith("v_x_"))
        self.assertGreater(x_assign_index, then_label_index)
        # <<< FIX: Corrected assertion for last line >>>
        self.assertTrue(actual_ir[-1].startswith("REM L")) # Just check it's a label
        self.assertGreater(len(actual_ir)-1, x_assign_index) # Ensure it's after then block

    def test_while_loop(self):
        full_source = "glob {i} proc {} func {} main { var{} i=0; while (i > 10) { i = (i plus 1) } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        # Find labels and check structure
        rem_labels = [line for line in actual_ir if line.startswith("REM L")]
        self.assertEqual(len(rem_labels), 3)
        cond_label, body_label, exit_label = rem_labels[0], rem_labels[1], rem_labels[2] # Labels generated in this order
        # Check IF jumps to body_label
        self.assertTrue(any(line.startswith("IF ") and f" THEN {body_label.split()[1]}" in line for line in actual_ir))
        # Check GOTO jumps back to cond_label
        self.assertTrue(any(line == f"GOTO {cond_label.split()[1]}" for line in actual_ir))
        # Check Exit label is last
        self.assertEqual(actual_ir[-1], exit_label)

    def _visit_DoUntilLoopNode(self, node: DoUntilLoopNode):
        label_body = self._new_label()
        label_exit = self._new_label()

        self._emit(f"REM {label_body}")
        self._visit(node.body)

        cond_place = self._visit(node.condition)
        self._emit(f"IF {cond_place} = 0 THEN {label_body}")

        # Ensure the exit label is emitted after the conditional jump
        self._emit(f"REM {label_exit}") # <-- Make sure this line is active

    def test_logical_and(self):
        full_source = "glob {a b} proc {} func {} main { var{} if ((a > 0) and (b > 0)) { a = 1 } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        if_lines = [line for line in actual_ir if line.startswith("IF")]
        rem_lines = [line for line in actual_ir if line.startswith("REM L")]
        self.assertGreaterEqual(len(if_lines), 2)
        self.assertGreaterEqual(len(rem_lines), 3)
        if_a, if_b = if_lines[0], if_lines[1]
        # Labels: L_second, L_true, L_false_exit (or similar roles)
        l_second = rem_lines[0]
        l_true = rem_lines[1]
        l_false_exit = rem_lines[2]
        # First IF jumps to L_second if true (evaluate b), else implicit fallthrough to L_false_exit
        self.assertTrue(if_a.split(" THEN ")[1] == l_second.split()[1])
        # Second IF (after L_second) jumps to L_true if true, else implicit fallthrough to L_false_exit
        self.assertTrue(if_b.split(" THEN ")[1] == l_true.split()[1])

    def test_logical_or(self):
        full_source = "glob {a b} proc {} func {} main { var{} if ((a > 0) or (b > 0)) { a = 1 } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        if_lines = [line for line in actual_ir if line.startswith("IF")]
        rem_lines = [line for line in actual_ir if line.startswith("REM L")]
        self.assertGreaterEqual(len(if_lines), 2)
        self.assertGreaterEqual(len(rem_lines), 3)
        if_a, if_b = if_lines[0], if_lines[1]
        # Labels: L_second, L_true, L_false_exit (or similar roles)
        l_second = rem_lines[0]
        l_true = rem_lines[1]
        l_false_exit = rem_lines[2]
        # First IF jumps to L_true if true, else implicit fallthrough to L_second
        self.assertTrue(if_a.split(" THEN ")[1] == l_true.split()[1])
        # Second IF (after L_second) jumps to L_true if true, else implicit fallthrough to L_false_exit
        self.assertTrue(if_b.split(" THEN ")[1] == l_true.split()[1])

    def test_logical_not(self):
        full_source = "glob {x} proc {} func {} main { var{} if (not (x > 0)) { x = 1 } }"
        actual_ir = self._run_full_analysis_codegen(full_source)
        if_line = next(line for line in actual_ir if line.startswith("IF"))
        rem_lines = [line for line in actual_ir if line.startswith("REM L")]
        self.assertEqual(len(rem_lines), 2)
        then_label, exit_label = rem_lines[0], rem_lines[1] # Order depends on generation
        # Check IF jumps to EXIT label (opposite of usual because of not)
        self.assertTrue(if_line.endswith(f" THEN {exit_label.split()[1]}"))

    def test_procedure_call(self):
        full_source = """
            glob { x y }
            proc { pdef myproc(a b) { local {} print a } }
            func {}
            main { var {} myproc(x y) }
        """
        actual_ir = self._run_full_analysis_codegen(full_source)
        # Expected: t<n> = CALL v_myproc_<m>(v_x_<a>, v_y_<b>)
        self.assertGreaterEqual(len(actual_ir), 1)
        self.assertTrue(re.match(r"t\d+ = CALL v_myproc_\d+\(v_x_\d+, v_y_\d+\)", actual_ir[0]))

    def test_function_call(self):
        full_source = """
            glob { result x }
            proc {}
            func { fdef myfunc(a) { local {} halt; return a } }
            main { var {} result = myfunc(x) }
        """
        actual_ir = self._run_full_analysis_codegen(full_source)
        # Expected:
        # t<n> = CALL v_myfunc_<m>(v_x_<a>)
        # v_result_<b> = t<n>
        self.assertGreaterEqual(len(actual_ir), 2)
        call_line_index = next(i for i, line in enumerate(actual_ir) if "CALL v_myfunc_" in line)
        self.assertTrue(re.match(r"t\d+ = CALL v_myfunc_\d+\(v_x_\d+\)", actual_ir[call_line_index]))
        self.assertTrue(re.match(r"v_result_\d+ = t\d+", actual_ir[call_line_index + 1]))

    def test_error_not_outside_condition(self):
        full_source = "glob { x y } proc {} func {} main { var{} x = (not (y > 0)) }"
        # <<< FIX: Expect SemanticError >>>
        with self.assertRaisesRegex(SemanticError, "Assignment to 'x' requires numeric value, got boolean"):
            self._run_full_analysis_codegen(full_source)

if __name__ == '__main__':
    unittest.main()