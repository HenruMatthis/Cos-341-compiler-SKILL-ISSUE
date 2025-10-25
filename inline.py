# inline.py
"""
Implements function and procedure inlining (Task 8) on the generated IR code.
Follows the method described in COS 341 Lecture 16 slides.
Assumes non-recursive functions/procedures.
"""

import re
from typing import List, Dict, Tuple, Optional

# --- Data structure to hold info about function/procedure bodies ---
class FunctionBodyInfo:
    def __init__(self, name: str, params: List[str], body_ir: List[str]):
        self.name: str = name          # Unique IR name
        self.params: List[str] = params  # List of unique parameter IR names
        self.body_ir: List[str] = body_ir # List of IR instructions for the body

# --- Main Inlining Logic ---

class Inliner:
    def __init__(self, function_bodies: Dict[str, FunctionBodyInfo]):
        """
        Initializes the Inliner.
        Args:
            function_bodies: A dictionary mapping unique function/procedure names
                             to FunctionBodyInfo objects containing their parameters
                             and pre-generated body IR.
        """
        self.function_bodies: Dict[str, FunctionBodyInfo] = function_bodies
        self._inline_counter = 0 # To ensure unique labels for each inlining instance

    def _make_labels_unique(self, ir_code: List[str], inline_id: int) -> List[str]:
        """
        Makes labels (Lx) and their jump targets unique within a block of IR code
        by appending an inline instance ID (_inline_X).
        """
        unique_ir = []
        label_pattern = re.compile(r"^(L\d+)$") # Matches only label names like L1, L2
        rem_label_pattern = re.compile(r"^REM (L\d+)$") # Matches REM L1, REM L2
        jump_pattern = re.compile(r"^(GOTO|IF .+ THEN) (L\d+)$") # Matches GOTO L1 or IF..THEN L1

        new_labels: Dict[str, str] = {} # Map original label -> new unique label

        # First pass: find all defined labels and create unique versions
        for line in ir_code:
            rem_match = rem_label_pattern.match(line)
            if rem_match:
                original_label = rem_match.group(1)
                if original_label not in new_labels:
                    new_labels[original_label] = f"{original_label}_inline_{inline_id}"

        # Second pass: replace labels and jump targets
        for line in ir_code:
            rem_match = rem_label_pattern.match(line)
            jump_match = jump_pattern.match(line)

            if rem_match:
                original_label = rem_match.group(1)
                unique_ir.append(f"REM {new_labels.get(original_label, original_label)}")
            elif jump_match:
                command_part = jump_match.group(1)
                original_label = jump_match.group(2)
                unique_ir.append(f"{command_part} {new_labels.get(original_label, original_label)}")
            else:
                unique_ir.append(line) # Keep lines without labels/jumps as is

        return unique_ir

    def _adapt_body(self,
                    body_ir: List[str],
                    return_target: Optional[str],
                    inline_id: int) -> List[str]:
        """
        Adapts the copied body IR:
        1. Makes labels unique.
        2. Replaces RETURN instructions with assignments to the call target.
           
        """
        adapted_ir = []
        return_pattern = re.compile(r"^RETURN (t\d+|v_\w+_\d+)$") # Matches RETURN t1 or RETURN v_result_1

        unique_body_ir = self._make_labels_unique(body_ir, inline_id)

        for line in unique_body_ir:
            return_match = return_pattern.match(line)
            if return_match and return_target:
                # Replace RETURN place with target = place [cite: 5266]
                return_value_place = return_match.group(1)
                adapted_ir.append(f"{return_target} = {return_value_place}")
            elif return_match and not return_target:
                # Found RETURN in a procedure, should not happen if types are right
                # Or maybe it's the main return? For now, just skip it in proc context.
                 pass # Ignore return in procedures
            else:
                adapted_ir.append(line)

        return adapted_ir


    # inline.py - Revised inline_calls method

    def inline_calls(self, ir_code: List[str]) -> List[str]:
        inlined_ir: List[str] = []
        # Pattern to match CALL instructions
        call_pattern = re.compile(r"^(t\d+|v_\w+_\d+) = CALL (v_\w+_\d+)\(([^)]*)\)$")
        # Pattern to match assignments like v_result = tX
        assignment_pattern = re.compile(r"^(v_\w+_\d+) = (t\d+)$")

        i = 0
        while i < len(ir_code):
            instruction = ir_code[i]
            call_match = call_pattern.match(instruction)

            if call_match:
                call_target_temp = call_match.group(1) # e.g., t2
                func_name = call_match.group(2)
                args_str = call_match.group(3)
                call_args = [arg.strip() for arg in args_str.split(',') if arg.strip()]

                # --- Check Preconditions ---
                if func_name not in self.function_bodies:
                    inlined_ir.append(instruction) # Keep the CALL if body not found
                    print(f"Warning: Definition for '{func_name}' not found for inlining.")
                    i += 1
                    continue

                func_info = self.function_bodies[func_name]
                # Assuming non-recursive check passed earlier

                # --- Determine Actual Return Target and if next line should be skipped ---
                actual_return_target = call_target_temp # Default target is the CALL's temp
                is_procedure_call = True # Assume procedure unless we find RETURNs
                skip_next_instruction = False

                # Check if it's actually a function (has RETURNs?)
                has_return = any(line.strip().startswith("RETURN") for line in func_info.body_ir)

                if has_return:
                    is_procedure_call = False
                    # Look ahead to see if the temp is immediately assigned to a final variable
                    if i + 1 < len(ir_code):
                        next_instruction = ir_code[i+1]
                        assignment_match = assignment_pattern.match(next_instruction)
                        # Does the next line look like: v_final = call_target_temp ?
                        if assignment_match and assignment_match.group(2) == call_target_temp:
                            actual_return_target = assignment_match.group(1) # Use v_final as target
                            skip_next_instruction = True # We will skip the 'v_final = t_temp' line
                else:
                    # It's a procedure, no return value needed in _adapt_body
                    actual_return_target = None


                # --- Perform Inlining Steps ---
                self._inline_counter += 1
                inline_id = self._inline_counter

                # 1. Generate Parameter Assignments
                if len(call_args) != len(func_info.params):
                    raise ValueError(f"Argument count mismatch calling {func_name}: "
                                     f"expected {len(func_info.params)}, got {len(call_args)}")
                param_assignments = [f"{param} = {arg}" for param, arg in zip(func_info.params, call_args)]

                # 2. Adapt Body Code (unique labels, replace RETURN with actual_return_target)
                adapted_body = self._adapt_body(func_info.body_ir,
                                                actual_return_target,
                                                inline_id)

                # 3. Add assignments and adapted body to output IR
                inlined_ir.extend(param_assignments)
                inlined_ir.extend(adapted_body)

                # 4. Advance index past CALL and potentially the skipped assignment
                i += 2 if skip_next_instruction else 1

            else:
                # Not a CALL instruction, just copy it
                inlined_ir.append(instruction)
                i += 1

        return inlined_ir

# --- Example Usage (requires pre-generated IR and function body info) ---
if __name__ == '__main__':
    # --- Dummy data representing output from CodeGenerator ---

    # Example: fdef func1(a b) { local {t} t = (a plus b); return t }
    func1_body = FunctionBodyInfo(
        name="v_func1_1",
        params=["v_a_2", "v_b_3"],
        body_ir=[
            "t1 = v_a_2 + v_b_3", # Simplified IR for (a plus b)
            "v_t_4 = t1",         # Simplified IR for t = ...
            "RETURN v_t_4"        # IR for return t
        ]
    )

    # Example: pdef proc1(x) { local{} print x }
    proc1_body = FunctionBodyInfo(
        name="v_proc1_5",
        params=["v_x_6"],
        body_ir=[
            "PRINT v_x_6" # Simplified IR for print x
            # No RETURN instruction
        ]
    )

    available_bodies = {
        "v_func1_1": func1_body,
        "v_proc1_5": proc1_body,
    }

    # Example IR code containing CALL instructions
    initial_ir = [
        "v_main_var_7 = 10",
        "t2 = CALL v_func1_1(v_main_var_7, 5)", # result = func1(main_var, 5)
        "v_result_8 = t2",
        "t3 = 20",
        "t4 = CALL v_proc1_5(t3)",              # proc1(20)
        "STOP"
    ]

    # --- Perform Inlining ---
    inliner = Inliner(available_bodies)
    final_ir = inliner.inline_calls(initial_ir)

    # --- Print Result ---
    print("--- Initial IR ---")
    for line in initial_ir:
        print(line)

    print("\n--- Final Inlined IR ---")
    for line in final_ir:
        print(line)

    # --- Example 2: Inlining the same function twice ---
    initial_ir_2 = [
        "t1 = CALL v_func1_1(1, 2)",
        "v_res1_9 = t1",
        "t2 = CALL v_func1_1(10, 20)",
        "v_res2_10 = t2",
        "STOP"
    ]
    final_ir_2 = inliner.inline_calls(initial_ir_2)
    print("\n--- Final Inlined IR (Example 2) ---")
    for line in final_ir_2:
        print(line)