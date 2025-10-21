import unittest
import sys
import os

# Add project root to import path so we can import symbol_table.py
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from symbol_table import SymbolTable, SymbolInfo, SymbolTableError

class TestSymbolTable(unittest.TestCase):
    def setUp(self):
        self.symtab = SymbolTable()
        self.symtab.enter_scope("Global")

    def tearDown(self):
        self.symtab._scopes.clear()

    def test_declare_and_lookup_variable(self):
        self.symtab.declare_var("x", decl_type="numeric")
        info = self.symtab.lookup("x")
        self.assertIsNotNone(info)
        self.assertEqual(info.decl_type, "numeric")
        self.assertTrue(info.unique_name.startswith("v_x_"))

    def test_nested_scopes(self):
        self.symtab.declare_var("x", decl_type="numeric")
        self.symtab.enter_scope("Proc")
        self.symtab.declare_var("y", decl_type="string")

        # Both variables should be visible
        self.assertIsNotNone(self.symtab.lookup("y"))
        self.assertIsNotNone(self.symtab.lookup("x"))

        self.symtab.exit_scope()
        # y should no longer be visible
        self.assertIsNone(self.symtab.lookup("y"))

    def test_duplicate_declaration_in_same_scope(self):
        self.symtab.declare_var("a", decl_type="numeric")
        with self.assertRaises(SymbolTableError):
            self.symtab.declare_var("a", decl_type="boolean")

    def test_unique_name_generation(self):
        n1 = self.symtab._gen_unique_name("x")
        n2 = self.symtab._gen_unique_name("x")
        self.assertNotEqual(n1, n2)

    def test_scope_level_tracking(self):
        self.symtab.declare_var("x", decl_type="numeric")
        global_scope_level = self.symtab.current_scope_level()
        self.symtab.enter_scope("Main")
        self.symtab.declare_var("y", decl_type="numeric")
        self.assertGreater(self.symtab.current_scope_level(), global_scope_level)
        self.symtab.exit_scope()


if __name__ == "__main__":
    unittest.main()
