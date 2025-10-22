# Semantic Analysis for SPL Compiler (Tasks 5 & 6)

## Overview

The semantic analyzer performs two critical compilation phases:

1. **Task 5: Scope Checking** - Validates variable declarations, scope rules, and name resolution
2. **Task 6: Type Checking** - Ensures type compatibility for all operations and expressions

## Quick Start

### Running the Semantic Analyzer

```bash
# Run the comprehensive test suite (35 tests)
python test_semantic.py

# Or from the Tests directory
cd Tests
python test_semantic.py
```

### Basic Integration

```python
from lexer import Lexer
from parser_spl import Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError

# 1. Lex the source code
lexer = Lexer()
tokens = list(lexer.tokenize(source_code))

# 2. Parse into AST
parser = Parser(tokens)
ast = parser.parse()

# 3. Perform semantic analysis
analyzer = SemanticAnalyzer()
try:
    symbol_table = analyzer.analyze(ast)
    print("✅ Semantic analysis passed!")
    analyzer.print_symbol_table()  # View symbol table
except SemanticError as e:
    print(f"❌ Semantic error: {e.message}")
```

### Using with main.py (Optional)

If your `main.py` integrates all phases:

```bash
# Compile a complete SPL file
python main.py program.spl

# Run integrated test suite
python main.py --test
```

---

## Task 5: Scope Checking

### What It Validates

The scope checker enforces SPL's static scoping rules and validates all identifier declarations and uses.

#### 1. Duplicate Declarations

Detects duplicate identifiers in the same scope:

```spl
glob { x x }  // ❌ Error: Duplicate variable declaration 'x' in the same scope
```

```spl
main {
    var { a a }  // ❌ Error: Duplicate variable declaration 'a' in the same scope
    halt
}
```

```spl
proc {
    pdef myfunc(x x) {  // ❌ Error: Duplicate parameter 'x' in parameter list
        local { }
        halt
    }
}
```

#### 2. Parameter Shadowing

Prevents local variables from shadowing parameters:

```spl
func {
    fdef compute(param1) {
        local { param1 }  // ❌ Error: Duplicate declaration of 'param1' in the same scope
        return param1
    }
}
```

**Why this is caught:** Parameters and locals are in the same scope in SPL, so they can't have the same name.

#### 3. Global Name Clashes

Ensures no name conflicts between variables, procedures, and functions at the global level:

```spl
glob { compute }  // Variable named 'compute'
func {
    fdef compute(x) {  // ❌ Error: Duplicate declaration of 'compute' in the same scope
        local { }
        halt;
        return x
    }
}
```

The checker validates:
- No variable name = function name
- No variable name = procedure name  
- No function name = procedure name

#### 4. Undefined Variables

Validates that all used variables are declared:

```spl
main {
    var { }
    x = 10  // ❌ Error: Undefined variable 'x' in assignment
}
```

```spl
glob { x }
main {
    var { }
    y = x  // ❌ Error: Undefined variable 'y' in assignment
}
```

#### 5. Scope Resolution (Static Scoping)

The analyzer implements static scoping with proper nesting:

**Scope Hierarchy:**
```
Global Scope (level 1)
  ├─ Procedure Scope (level 2)
  │   └─ Local variables
  ├─ Function Scope (level 2)
  │   └─ Local variables
  └─ Main Scope (level 2)
      └─ Local variables
```

**Lookup Rules:**
- Inner scopes can access outer scopes
- Lookup proceeds: Local → Parameter → Global
- Names in inner scopes shadow outer scopes

**Example:**
```spl
glob { x }        // Global scope: x

proc {
    pdef myproc(y) {      // Procedure scope: y (parameter)
        local { z }       // Procedure scope: z (local)
        z = x;            // ✅ Can access global x
        z = y;            // ✅ Can access parameter y
        x = z             // ✅ Can modify global x
    }
}

main {
    var { x }  // Main scope: x (shadows global x)
    x = 5      // ✅ Assigns to main's x, not global's x
}
```

---

## Task 6: Type Checking

### Type System Overview

SPL has a **two-type system**:

| Type | Used For | Examples |
|------|----------|----------|
| **numeric** | All variables, numbers, arithmetic results | `42`, `x`, `(5 plus 10)` |
| **boolean** | Comparison results, logical operations | `(x > 5)`, `(a and b)` |

**Key Rule:** All variables are `numeric`. Boolean values only exist as expression results.

### Operation Type Rules

#### Arithmetic Operations

**Operators:** `plus`, `minus`, `mult`, `div`  
**Type Signature:** `numeric × numeric → numeric`

```spl
// ✅ Valid arithmetic
x = (5 plus 10)          // numeric + numeric = numeric
y = (x mult 3)           // numeric * numeric = numeric
z = ((20 minus 5) div 3) // (numeric - numeric) / numeric = numeric

// ❌ Invalid arithmetic
z = ((x > y) plus 1)     // boolean + numeric ❌
w = ((a and b) mult 5)   // boolean * numeric ❌
```

**Error Messages:**
```
❌ Operator 'plus' requires numeric left operand, got boolean
❌ Operator 'mult' requires numeric right operand, got boolean
```

#### Comparison Operations

**Operators:** `eq`, `>`  
**Type Signature:** `numeric × numeric → boolean`

```spl
// ✅ Valid comparisons
if (x > 5) { halt }              // numeric > numeric = boolean
if (x eq 10) { halt }            // numeric = numeric = boolean
if ((a plus b) > (c mult d)) {}  // (numeric) > (numeric) = boolean

// ❌ Invalid comparisons
if ((x > 5) > 10) { halt }       // boolean > numeric ❌
if ((a eq b) eq c) { halt }      // boolean = numeric ❌
```

**Error Messages:**
```
❌ Operator '>' requires numeric left operand, got boolean
❌ Operator 'eq' requires numeric right operand, got boolean
```

#### Logical Operations

**Operators:** `and`, `or`  
**Type Signature:** `boolean × boolean → boolean`

```spl
// ✅ Valid logical operations
if ((x > 5) and (y > 10)) { halt }        // boolean and boolean = boolean
if ((a eq b) or (c eq d)) { halt }        // boolean or boolean = boolean
while ((not (x > 0)) and (y > 5)) {}      // boolean and boolean = boolean

// ❌ Invalid logical operations
if (x and y) { halt }                     // numeric and numeric ❌
if ((x plus y) or (a mult b)) { halt }    // numeric or numeric ❌
```

**Error Messages:**
```
❌ Operator 'and' requires boolean left operand, got numeric
❌ Operator 'or' requires boolean right operand, got numeric
```

#### Unary Operations

**Operators:**
- `neg`: `numeric → numeric` (negation)
- `not`: `boolean → boolean` (logical not)

```spl
// ✅ Valid unary operations
x = (neg 5)                // numeric negation
x = (neg y)                // numeric negation
if (not (x > 5)) { halt }  // boolean not

// ❌ Invalid unary operations
x = (not 5)                // not requires boolean ❌
if (neg (x > 5)) { halt }  // neg requires numeric ❌
```

**Error Messages:**
```
❌ Operator 'neg' requires numeric operand, got boolean
❌ Operator 'not' requires boolean operand, got numeric
```

### Control Structure Type Rules

#### If Statement

**Condition must be boolean:**

```spl
// ✅ Valid if statements
if (x > 5) {      // Condition is boolean
    halt
}

if ((x > 5) and (y > 10)) {  // Condition is boolean
    x = 100
}

if (not (x eq y)) {  // Condition is boolean
    y = 200
}

// ❌ Invalid if statements
if x {            // Condition is numeric ❌
    halt
}

if (x plus y) {   // Condition is numeric ❌
    halt
}
```

**Error Message:**
```
❌ If condition must be boolean, got numeric
```

#### While Loop

**Condition must be boolean:**

```spl
// ✅ Valid while loops
while (counter > 10) {
    counter = (counter plus 1)
}

while ((x > 0) and (y > 0)) {
    x = (x minus 1)
}

// ❌ Invalid while loops
while counter {          // Condition is numeric ❌
    halt
}

while (x plus y) {       // Condition is numeric ❌
    halt
}
```

**Error Message:**
```
❌ While loop condition must be boolean, got numeric
```

#### Do-Until Loop

**Condition must be boolean:**

```spl
// ✅ Valid do-until loops
do {
    x = (x plus 1)
} until (x > 10)        // Condition is boolean

do {
    y = (y minus 1)
} until ((y eq 0) or (x > 100))  // Condition is boolean

// ❌ Invalid do-until loops
do {
    x = (x plus 1)
} until x               // Condition is numeric ❌

do {
    halt
} until (x mult y)      // Condition is numeric ❌
```

**Error Message:**
```
❌ Do-until loop condition must be boolean, got numeric
```

### Function and Procedure Rules

#### Functions

**Rules:**
- All functions return `numeric` type
- Can only be used in assignment RHS (right-hand side)
- Cannot be called as statements

```spl
func {
    fdef add(a b) {
        local { result }
        result = (a plus b);
        return result  // ✅ Must return numeric
    }
}

main {
    var { result }
    result = add(5 10);    // ✅ Function call in assignment
    add(5 10)              // ❌ Error: function called as procedure
}
```

**Error Messages:**
```
❌ 'add' is not a procedure (it's a func)
❌ Function 'add' must return a numeric value
```

#### Procedures

**Rules:**
- Procedures don't return values
- Can only be used as statements
- Cannot be called in expressions

```spl
proc {
    pdef printval(x) {
        local { }
        print x
    }
}

main {
    var { y }
    printval(42);       // ✅ Procedure call as statement
    y = printval(42)    // ❌ Error: procedure called as function
}
```

**Error Messages:**
```
❌ 'printval' is not a function (it's a proc)
❌ Undefined function 'printval'
```

---

## Symbol Table Structure

The semantic analyzer builds a comprehensive symbol table:

### SymbolInfo Structure

Each declared identifier is stored as a `SymbolInfo` object:

```python
@dataclass
class SymbolInfo:
    name: str          # Original source name (e.g., "counter")
    kind: str          # 'var', 'proc', 'func', 'param'
    decl_type: str     # 'numeric', 'boolean', 'string', or None
    scope_level: int   # Depth in scope stack (1=Global, 2+=nested)
    unique_name: str   # IR-safe name (e.g., "v_counter_1")
    node_id: int       # Reference to AST node
    extra: Dict        # Optional metadata
```

### Scope Stack

The symbol table maintains a stack of scopes:

```
Scope Stack:
  [0] Global Scope (level 1)
      ├─ x: var, numeric, v_x_1
      ├─ myproc: proc, None, v_myproc_1
      └─ myfunc: func, None, v_myfunc_1
  
  [1] Function Scope (level 2) - inside myfunc
      ├─ param1: param, numeric, v_param1_1
      └─ local1: var, numeric, v_local1_1
```

### Using the Symbol Table

```python
analyzer = SemanticAnalyzer()
symbol_table = analyzer.analyze(ast)

# Look up a variable
info = symbol_table.lookup("x")
if info:
    print(f"Name: {info.name}")           # "x"
    print(f"Kind: {info.kind}")           # "var"
    print(f"Type: {info.decl_type}")      # "numeric"
    print(f"Scope: {info.scope_level}")   # 1
    print(f"IR Name: {info.unique_name}") # "v_x_1"

# Check if name exists
try:
    symbol_table.assert_exists("undefined_var")
except SymbolTableError as e:
    print(e)  # Name 'undefined_var' not declared

# Get unique IR name
ir_name = symbol_table.get_unique_name("x")  # "v_x_1"
```

---

## Architecture & Implementation

### Tree Crawling Algorithm

The analyzer uses **recursive descent** to traverse the AST:

```
SemanticAnalyzer.analyze(ast)
  │
  └─> _visit_program(ProgramNode)
       ├─> enter_scope("Global")
       │
       ├─> _visit_variable_decls(globals)     # Declare global vars
       │    └─> declare_var() for each
       │
       ├─> _declare_procedures(procs)         # Declare proc signatures
       │    └─> declare_proc() for each
       │
       ├─> _declare_functions(funcs)          # Declare func signatures
       │    └─> declare_func() for each
       │
       ├─> check_no_global_name_clashes()     # Validate no conflicts
       │
       ├─> _visit_procedure_defs(procs)       # Visit proc bodies
       │    └─> _visit_procedure_def()
       │         ├─> enter_scope("Procedure")
       │         ├─> _visit_parameters()      # Declare params
       │         ├─> _visit_body()
       │         │    ├─> declare locals
       │         │    ├─> check_no_shadowing_of_params()
       │         │    └─> _visit_algorithm()  # Check instructions
       │         └─> exit_scope()
       │
       ├─> _visit_function_defs(funcs)        # Visit func bodies
       │    └─> _visit_function_def()
       │         ├─> enter_scope("Function")
       │         ├─> _visit_parameters()
       │         ├─> _visit_body()
       │         ├─> check return type
       │         └─> exit_scope()
       │
       ├─> _visit_main_prog(main)             # Visit main
       │    ├─> enter_scope("Main")
       │    ├─> _visit_variable_decls(locals)
       │    ├─> _visit_algorithm()
       │    └─> exit_scope()
       │
       └─> exit_scope()
```

### Type Annotation

Types are stored in `analyzer.node_types` dictionary:

```python
# During analysis, annotate nodes with types
self._set_node_type(node, "numeric")   # For arithmetic results
self._set_node_type(node, "boolean")   # For comparisons

# Later retrieval
node_type = analyzer.get_node_type(node)  # Returns "numeric" or "boolean"
```

This annotation is used for:
- Validating operator operands
- Checking condition types
- Code generation (future phases)

---

## Testing

### Test Suite Coverage

The `test_semantic.py` includes **35 comprehensive tests**:

#### Scope Checking Tests (Tests 1-8)
1. ✅ Valid simple program
2. ✅ Duplicate global variable (should fail)
3. ✅ Duplicate local variable (should fail)
4. ✅ Parameter shadowing (should fail)
5. ✅ Valid function with parameters and locals
6. ✅ Undefined variable (should fail)
7. ✅ Global name clash (should fail)
8. ✅ Valid nested scopes

#### Type Checking Tests (Tests 9-35)
9. ✅ Valid arithmetic operations
10. ✅ Valid comparison operations
11. ✅ Valid logical operations
12. ✅ Invalid numeric in boolean context (should fail)
13. ✅ Invalid logical operator on numeric (should fail)
14. ✅ Valid negation of numeric
15. ✅ Valid NOT operator on boolean
16. ✅ Invalid arithmetic on boolean (should fail)
17. ✅ Valid complex nested expressions
18. ✅ Valid do-until loop
19. ✅ Invalid do-until condition (should fail)
20. ✅ Valid function call in assignment
21. ✅ Undefined function call (should fail)
22. ✅ Valid procedure call
23. ✅ Undefined procedure call (should fail)
24. ✅ Valid print statements
25. ✅ Valid if-else statement
26. ✅ Invalid OR operator with numeric (should fail)
27. ✅ Valid complex boolean expression
28. ✅ Valid equality comparison
29. ✅ Invalid NOT operator on numeric (should fail)
30. ✅ Valid multiple parameters (max 3)
31. ✅ Valid scope access to outer variables
32. ✅ Invalid call function as procedure (should fail)
33. ✅ Invalid call procedure as function (should fail)
34. ✅ Valid empty parameter lists
35. ✅ Valid nested while loops

### Running Tests

```bash
# From project root
python Tests/test_semantic.py

# From Tests directory
cd Tests
python test_semantic.py
```

### Expected Output

```
======================================================================
TEST SUMMARY
======================================================================
Total Tests: 35
Passed: 35 ✅
Failed: 0 ❌
Success Rate: 100.0%
======================================================================
```

---

## Error Messages Reference

### Scope Errors

| Error | Meaning | Example |
|-------|---------|---------|
| `Duplicate variable declaration 'x' in the same scope` | Same name declared twice in one scope | `glob { x x }` |
| `Duplicate parameter 'x' in parameter list` | Parameter name used twice | `pdef f(x x) { ... }` |
| `Duplicate declaration of 'x' in the same scope` | Name conflicts in same scope | Local shadows parameter |
| `Undefined variable 'x'` | Variable used before declaration | `x = 10` without declaring x |
| `Variable/function name clash: {'compute'}` | Global name conflict | var and func with same name |
| `Shadowing of parameters not allowed: {'x'}` | Local var shadows param | `local { x }` when x is param |

### Type Errors

| Error | Meaning | Example |
|-------|---------|---------|
| `If condition must be boolean, got numeric` | Non-boolean in if condition | `if x { ... }` |
| `While loop condition must be boolean, got numeric` | Non-boolean in while | `while x { ... }` |
| `Do-until loop condition must be boolean, got numeric` | Non-boolean in until | `until x` |
| `Operator 'plus' requires numeric left operand, got boolean` | Wrong type for arithmetic | `(x > 5) plus 10` |
| `Operator 'and' requires boolean left operand, got numeric` | Wrong type for logical | `x and y` |
| `Operator 'neg' requires numeric operand, got boolean` | Wrong type for negation | `neg (x > 5)` |
| `Operator 'not' requires boolean operand, got numeric` | Wrong type for not | `not x` |
| `'myfunc' is not a procedure (it's a func)` | Function called as procedure | `myfunc(10)` as statement |
| `'myproc' is not a function (it's a proc)` | Procedure called as function | `x = myproc(10)` |
| `Function 'f' must return a numeric value` | Wrong return type | Function returns boolean |

---

## Common Pitfalls & Solutions

### 1. Confusing Functions and Procedures

❌ **Wrong:**
```spl
func { fdef calc(x) { local { } return x } }
main {
    var { }
    calc(10)  // ❌ Function called as procedure
}
```

✅ **Correct:**
```spl
func { fdef calc(x) { local { } return x } }
main {
    var { result }
    result = calc(10)  // ✅ Function used in assignment
}
```

### 2. Using Numeric in Boolean Context

❌ **Wrong:**
```spl
if x { halt }  // ❌ x is numeric, not boolean
```

✅ **Correct:**
```spl
if (x > 0) { halt }  // ✅ Comparison produces boolean
```

### 3. Applying Logical Operators to Numbers

❌ **Wrong:**
```spl
if (x and y) { halt }  // ❌ x and y are numeric
```

✅ **Correct:**
```spl
if ((x > 0) and (y > 0)) { halt }  // ✅ Both operands boolean
```

### 4. Parameter Shadowing

❌ **Wrong:**
```spl
pdef myfunc(param1) {
    local { param1 }  // ❌ Shadows parameter
    halt
}
```

✅ **Correct:**
```spl
pdef myfunc(param1) {
    local { local1 }  // ✅ Different name
    local1 = param1
}
```

### 5. All Variables Are Numeric

**Remember:** SPL doesn't have boolean variables. Booleans only exist as expression results.

❌ **Wrong thinking:** "I need a boolean variable"
✅ **Correct thinking:** "I need a comparison that produces a boolean"

```spl
// There are NO boolean variables in SPL
// This is valid:
if ((x > 5) and (y > 10)) { halt }

// But you can't store the boolean:
// z = ((x > 5) and (y > 10))  // ❌ Can't assign boolean to numeric var
```

---

## Integration with Code Generation

The semantic analyzer prepares the AST for code generation:

### What's Ready After Semantic Analysis

1. **✅ Validated AST** - All scope and type rules enforced
2. **✅ Type-annotated nodes** - Each expression has known type
3. **✅ Symbol table** - Maps source names to IR-safe names
4. **✅ Unique identifiers** - Prevents name collisions

### Using Results for Code Generation

```python
# After semantic analysis
ast, symbol_table = compile_spl(source)

# Generate code with unique names
for var in symbol_table.get_all_symbols_in_scope(1):
    ir_name = var.unique_name  # Use this in generated code
    print(f"DECLARE {ir_name}")  # e.g., "DECLARE v_x_1"

# Use type information
for instruction in ast.main.algorithm.instructions:
    if isinstance(instruction, AssignmentNode):
        rhs_type = analyzer.get_node_type(instruction.rhs)
        if rhs_type == "numeric":
            # Generate numeric assignment code
            pass
```

---

## File Structure

### Required Files

```
project/
├── semantic_analyzer.py     # Main implementation (Task 5 & 6)
├── symbol_table.py          # Symbol table data structure
├── ast_nodes.py            # AST node definitions
├── lexer.py                # Lexical analyzer
├── parser_spl.py           # Syntax analyzer
└── Tests/
    └── test_semantic.py    # Test suite (35 tests)
```

### Optional Files

```
project/
├── main.py                 # Full compiler integration
└── semantic.md            # This documentation
```

---

## Submission Checklist

For Tasks 5 & 6 submission:

- [ ] `semantic_analyzer.py` - Complete implementation
- [ ] `symbol_table.py` - Symbol table (provided/completed)
- [ ] `test_semantic.py` - Test suite showing 100% pass rate
- [ ] All 35 tests passing
- [ ] Documentation/comments in code
- [ ] Symbol table properly handles nested scopes
- [ ] Type checking validates all operations
- [ ] Clear error messages for all violations

---

## Summary

### Task 5: Scope Checking ✅

**Implemented:**
- ✅ Duplicate detection in same scope
- ✅ Parameter shadowing prevention
- ✅ Global name clash detection
- ✅ Undefined variable detection
- ✅ Static scoping with proper nesting
- ✅ Symbol table with unique IR names

### Task 6: Type Checking ✅

**Implemented:**
- ✅ Boolean condition enforcement (if/while/until)
- ✅ Arithmetic operator validation (numeric × numeric → numeric)
- ✅ Comparison operator validation (numeric × numeric → boolean)
- ✅ Logical operator validation (boolean × boolean → boolean)
- ✅ Unary operator validation (neg/not)
- ✅ Function/procedure distinction
- ✅ Function return type checking
- ✅ Type annotation of AST nodes

**Test Coverage:**
- ✅ 35/35 tests passing (100%)
- ✅ All scope rules validated
- ✅ All type rules validated
- ✅ Comprehensive error detection

---

## Additional Resources

### Key Concepts

- **Static Scoping:** Name resolution based on lexical structure
- **Type Inference:** Determining expression types from operations
- **Symbol Table:** Data structure for tracking declarations
- **AST Traversal:** Recursive visiting of tree nodes
- **Semantic Validation:** Enforcing language rules beyond syntax

### References

- Original documents: `2. Parser.pdf`, `3.1 Symbol Table for SPL.pdf`
- Grammar specification: `LL(1).pdf`
- AST node definitions: `ast_nodes.py`
- Test examples: `test_semantic.py`

---

**Status:** ✅ Tasks 5 & 6 Complete  
**Test Results:** 35/35 Passing (100%)  
**Ready For:** Code Generation (Tasks 7-9)