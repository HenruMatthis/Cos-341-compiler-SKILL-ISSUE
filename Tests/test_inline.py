# test_inline.py
import unittest
import sys
import os
import re
from typing import List

# Add project root to import path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# --- Import necessary classes ---
from inline import Inliner, FunctionBodyInfo # Assuming inline.py is in the project root

# Helper to clean IR lists for comparison
def clean_ir(ir_list: List[str]) -> List[str]:
    return [line.strip() for line in ir_list if line.strip()]

class TestInliner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # --- Define sample FunctionBodyInfo objects for testing ---

        # func add(a b) { local {t} t = (a plus b); return t }
        cls.func_add_body = FunctionBodyInfo(
            name="v_add_1",
            params=["v_a_2", "v_b_3"],
            body_ir=[
                "REM L1", # Example label inside body
                "t1 = v_a_2 + v_b_3",
                "v_t_4 = t1",
                "RETURN v_t_4",
                "REM L2" # Another label
            ]
        )

        # proc print_val(x) { local{} print x }
        cls.proc_print_val_body = FunctionBodyInfo(
            name="v_print_val_5",
            params=["v_x_6"],
            body_ir=[
                "PRINT v_x_6"
                # No RETURN
            ]
        )

        # func complex_calc(x) { local {y} y=10; if (x > 5) { return y } else { return 0 } }
        cls.func_complex_body = FunctionBodyInfo(
            name="v_complex_calc_10",
            params=["v_x_11"],
            body_ir=[
                "v_y_12 = 10",      # Simplified IR for y=10
                "t10 = v_x_11",     # IR for x in condition
                "t11 = 5",          # IR for 5 in condition
                "IF t10 > t11 THEN L3", # Condition
                "t12 = 0",          # Else branch result
                "RETURN t12",       # return 0
                "GOTO L4",          # Jump over then branch return
                "REM L3",           # Then branch label
                "RETURN v_y_12",    # return y
                "REM L4"            # Exit label
            ]
        )

        cls.available_bodies = {
            "v_add_1": cls.func_add_body,
            "v_print_val_5": cls.proc_print_val_body,
            "v_complex_calc_10": cls.func_complex_body
        }

    def setUp(self):
        # Create a new Inliner instance for each test
        self.inliner = Inliner(self.available_bodies)

    # --- Test Cases ---

    def test_simple_function_call(self):
        initial_ir = [
            "v_p_7 = 5",
            "v_q_8 = 10",
            "t2 = CALL v_add_1(v_p_7, v_q_8)",
            "v_result_9 = t2",
            "STOP"
        ]
        expected_ir = [
            "v_p_7 = 5",
            "v_q_8 = 10",
            # Inlined 'add' call starts here
            "v_a_2 = v_p_7",            # Parameter passing
            "v_b_3 = v_q_8",            # Parameter passing
            "REM L1_inline_1",          # Unique label
            "t1 = v_a_2 + v_b_3",       # Body instruction
            "v_t_4 = t1",               # Body instruction
            "v_result_9 = v_t_4",       # RETURN replaced with assignment to target 'v_result_9'
            "REM L2_inline_1",          # Unique label
            # Inlined 'add' call ends here
            # Original call line is removed
            # The assignment v_result_9 = t2 is now handled by the replaced RETURN
            "STOP"
        ]
        actual_ir = self.inliner.inline_calls(initial_ir)
        self.assertEqual(clean_ir(actual_ir), clean_ir(expected_ir))

    def test_simple_procedure_call(self):
        initial_ir = [
            "v_val_10 = 42",
            "t3 = CALL v_print_val_5(v_val_10)", # Dummy target t3
            "STOP"
        ]
        expected_ir = [
            "v_val_10 = 42",
            # Inlined 'print_val' call starts here
            "v_x_6 = v_val_10",         # Parameter passing
            "PRINT v_x_6",              # Body instruction
            # Inlined 'print_val' call ends here
            # Original call line is removed
            "STOP"
        ]
        actual_ir = self.inliner.inline_calls(initial_ir)
        self.assertEqual(clean_ir(actual_ir), clean_ir(expected_ir))

    def test_multiple_calls_same_function(self):
        initial_ir = [
            "t1 = CALL v_add_1(1, 2)",
            "v_res1_11 = t1",
            "t2 = CALL v_add_1(10, 20)",
            "v_res2_12 = t2",
            "STOP"
        ]
        actual_ir = self.inliner.inline_calls(initial_ir)

        # Check parameter passing for first call
        self.assertIn("v_a_2 = 1", actual_ir)
        self.assertIn("v_b_3 = 2", actual_ir)
        # Check body parts exist with unique labels for first call
        self.assertIn("REM L1_inline_1", actual_ir)
        self.assertIn("v_res1_11 = v_t_4", actual_ir) # Return replaced
        self.assertIn("REM L2_inline_1", actual_ir)

        # Check parameter passing for second call
        self.assertIn("v_a_2 = 10", actual_ir)
        self.assertIn("v_b_3 = 20", actual_ir)
        # Check body parts exist with unique labels for second call
        self.assertIn("REM L1_inline_2", actual_ir)
        self.assertIn("v_res2_12 = v_t_4", actual_ir) # Return replaced
        self.assertIn("REM L2_inline_2", actual_ir)

        # Ensure original CALL lines are gone
        self.assertFalse(any("CALL v_add_1" in line for line in actual_ir))

    def test_function_with_multiple_returns(self):
        initial_ir = [
            "v_input_13 = 7",
            "t13 = CALL v_complex_calc_10(v_input_13)",
            "v_output_14 = t13",
            "STOP"
        ]
        actual_ir = self.inliner.inline_calls(initial_ir)

        # Check parameter passing
        self.assertIn("v_x_11 = v_input_13", actual_ir)

        # Check labels are unique
        self.assertTrue(any(line == "REM L3_inline_1" for line in actual_ir))
        self.assertTrue(any(line == "REM L4_inline_1" for line in actual_ir))
        # Check jumps use unique labels
        self.assertTrue(any(re.match(r"IF .+ THEN L3_inline_1", line) for line in actual_ir))
        self.assertTrue(any(line == "GOTO L4_inline_1" for line in actual_ir))

        # Check BOTH return statements are replaced with assignment to v_output_14
        self.assertIn("v_output_14 = t12", actual_ir)   # return 0 replaced
        self.assertIn("v_output_14 = v_y_12", actual_ir) # return y replaced

        # Ensure no original RETURN or CALL remains
        self.assertFalse(any("RETURN " in line for line in actual_ir))
        self.assertFalse(any("CALL " in line for line in actual_ir))

    def test_no_calls(self):
        initial_ir = [
            "v_a_15 = 1",
            "v_b_16 = 2",
            "STOP"
        ]
        expected_ir = initial_ir # Should remain unchanged
        actual_ir = self.inliner.inline_calls(initial_ir)
        self.assertEqual(clean_ir(actual_ir), clean_ir(expected_ir))

    def test_call_undefined_function(self):
        # The inliner should ideally skip inlining if the function isn't found
        # (and potentially log a warning, as implemented).
        initial_ir = [
            "t1 = CALL v_undefined_func_99(1)",
            "v_res_17 = t1",
            "STOP"
        ]
        # Expect the original code back as no inlining happened
        expected_ir = initial_ir
        actual_ir = self.inliner.inline_calls(initial_ir)
        self.assertEqual(clean_ir(actual_ir), clean_ir(expected_ir))

    def test_argument_count_mismatch(self):
        initial_ir = [
            # Call add (expects 2 args) with 1 arg
            "t1 = CALL v_add_1(5)",
            "v_res_18 = t1",
            "STOP"
        ]
        # The Inliner should raise an error during processing
        with self.assertRaisesRegex(ValueError, r"Argument count mismatch calling v_add_1"):
            self.inliner.inline_calls(initial_ir)


if __name__ == '__main__':
    unittest.main()