# show_translation.py
"""
Takes SPL source code snippets, runs them through the compiler pipeline
(Lexer -> Parser -> Semantic Analyzer -> Code Generator),
and prints the original source alongside the generated Intermediate Representation (IR).
Useful for manual inspection and showcasing the code generation phase.
"""

import sys
import os
from typing import List

# Add project root to import path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# --- Import compiler components ---
from lexer import Lexer, LexerError
from parser_spl import Parser, ParseError
from semantic_analyzer import SemanticAnalyzer, SemanticError
from symbol_table import SymbolTable, SymbolTableError
from code_gen import CodeGenerator, CodeGenError
from ast_nodes import *

def translate_and_show(name: str, source: str):
    """
    Lexes, parses, analyzes, and generates IR for a source snippet,
    then prints both source and IR.
    """
    print("\n" + "="*70)
    print(f"EXAMPLE: {name}")
    print("="*70)
    print("--- Source Code ---")
    print(source.strip())
    print("-" * 70)

    source_to_compile = source.strip()
    is_full_program = source_to_compile.startswith("glob")
    filename = "<full_program>" if is_full_program else "<fragment>"

    if not is_full_program:
        # Wrap fragments for parsing
        source_to_compile = f"glob {{}} proc {{}} func {{}} main {{ var {{}} {source_to_compile} }}"

    try:
        # 1. Lex
        lexer = Lexer()
        tokens = list(lexer.tokenize(source_to_compile, filename=filename))

        # 2. Parse
        parser = Parser(tokens)
        ast = parser.parse()

        # 3. Semantic Analysis
        analyzer = SemanticAnalyzer()
        symbol_table = analyzer.analyze(ast) # Get populated symbol table and type info

        # 4. Code Generation
        code_gen = CodeGenerator(symbol_table, analyzer.node_types)
        # Target only the main algorithm block for IR generation
        main_algo_node = ast.main.algorithm
        code_gen.ir_code = [] # Reset just in case
        code_gen._temp_counter = 0
        code_gen._label_counter = 0
        code_gen._visit(main_algo_node)
        ir_code = code_gen.ir_code

        print("--- Generated IR Code ---")
        if ir_code:
            for line in ir_code:
                print(line)
        else:
            print("(No IR generated for main algorithm - possibly just declarations or halt)")

    except (LexerError, ParseError, SemanticError, CodeGenError, SymbolTableError) as e:
        print(f"--- COMPILATION FAILED ---")
        print(f"Error: {e}")
    except Exception as e:
        print(f"--- UNEXPECTED ERROR ---")
        import traceback
        traceback.print_exc()

    print("="*70)


# ==================================
#  Define Example Snippets Here
# ==================================
examples = [
    ("Halt",
     "halt"
    ),

    ("Simple Assignment",
     """
     glob { counter }
     proc {} func {} main { var {}
        counter = 0
     }
     """
    ),

    ("Arithmetic Expression",
     """
     glob { a b result }
     proc {} func {} main { var {}
        a = 10;
        b = 5;
        result = ((a mult 2) plus (b div 1))
     }
     """
    ),

    ("If-Then Statement",
     """
     glob { x }
     proc {} func {} main { var {}
        x = 5;
        if (x > 0) {
            print "positive"
        }
     }
     """
    ),

    ("If-Then-Else Statement",
     """
     glob { x status }
     proc {} func {} main { var {}
        x = 0;
        if (x eq 0) {
            status = 1
        } else {
            status = 0
        }
     }
     """
    ),

    ("While Loop",
     """
     glob { i }
     proc {} func {} main { var {}
        i = 5;
        while (i > 0) {
            print i;
            i = (i minus 1)
        }
     }
     """
    ),

    ("Do-Until Loop",
     """
     glob { count }
     proc {} func {} main { var {}
        count = 0;
        do {
            count = (count plus 1);
            print count
        } until (count > 5)
     }
     """
    ),

    ("Logical AND",
     """
     glob { a b flag }
     proc {} func {} main { var {}
         a = 1; b = 0; flag = 0;
         if ((a > 0) and (b > 0)) {
             flag = 1
         }
     }
     """
    ),

    ("Logical OR",
     """
     glob { valid error }
     proc {} func {} main { var {}
         valid = 0; error = 1;
         if ((valid eq 1) or (error eq 1)) {
             print "check needed"
         }
     }
     """
    ),

    ("Logical NOT",
     """
     glob { active }
     proc {} func {} main { var {}
         active = 0;
         if (not (active eq 1)) {
             print "inactive"
         }
     }
     """
    ),

    ("Procedure Call",
     """
     glob { g }
     proc {
         pdef setg(val) { local {} g = val }
     }
     func {}
     main { var { localval }
         localval = 42;
         setg(localval)
     }
     """
    ),

    ("Function Call",
     """
     glob { result input }
     proc {}
     func {
         fdef square(n) { local { sq }
             sq = (n mult n);
             halt; // Need one instruction before return
             return sq
         }
     }
     main { var {}
         input = 7;
         result = square(input)
     }
     """
    ),

    ("Complex Example",
     """
     glob { i sum }
     proc {}
     func {}
     main { var {}
         sum = 0;
         i = 1;
         while (i > 6) {   // Equivalent to while i < 6, using > for test
             sum = (sum plus i);
             if (sum > 10) {
                 print "sum exceeded 10";
                 halt // Use halt instead of break
             } else {
                 print "sum is ok"
             };
             i = (i plus 1)
         };
         print "final sum";
         print sum
     }
     """
     # Note: SPL has no break, using halt as a substitute here.
     # Note: Using 'i > 6' which seems logically inverted, but tests the structure.
     #       A real loop would use a condition like (not (i > 5)) or similar.
    )
]

# ==================================
#          Run Examples
# ==================================
if __name__ == "__main__":
    for name, source in examples:
        translate_and_show(name, source)