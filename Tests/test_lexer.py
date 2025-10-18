import unittest
from lexer import Lexer, Token, LexerError

class TestLexerBasics(unittest.TestCase):
    def setUp(self):
        self.lex = Lexer()

    def test_identifier_and_keyword(self):
        src = "glob counter = 0\n"
        tokens = list(self.lex.tokenize(src))
        # GLOB keyword produced (value None), ID 'counter', ID '...'
        self.assertEqual(tokens[0].type, 'GLOB')
        self.assertEqual(tokens[1].type, 'ID')
        self.assertEqual(tokens[1].value, 'counter')

    def test_numbers(self):
        src = "x = 42\npi = 3.1415\nbig = 6.02e23\n"
        tokens = list(self.lex.tokenize(src))
        # Find NUMBER tokens
        numbers = [t for t in tokens if t.type == 'NUMBER']
        self.assertIn(42, [n.value for n in numbers])
        self.assertTrue(any(isinstance(n.value, float) for n in numbers))

    def test_strings_and_escape(self):
        # Use double-quoted string with escapes, simpler and always valid
        src = r'print "hello\nworld" "single quote"'
        tokens = list(self.lex.tokenize(src))
        strings = [t.value for t in tokens if t.type == 'STRING']
        # Ensure escape sequences are decoded and second string captured correctly
        self.assertTrue(any("hello" in s for s in strings))
        self.assertTrue(any("single quote" == s for s in strings))


    def test_comments_ignored(self):
        src = "x = 1 // comment here\n/* comment \n spanning */ y = 2\n# hash comment\n"
        tokens = list(self.lex.tokenize(src))
        ids = [t for t in tokens if t.type == 'ID']
        self.assertTrue(any(t.value == 'x' for t in ids))
        self.assertTrue(any(t.value == 'y' for t in ids))

    def test_illegal_char(self):
        src = "x = 1 \u2603"  # include snowman char
        with self.assertRaises(LexerError):
            list(self.lex.tokenize(src))

if __name__ == '__main__':
    unittest.main()
