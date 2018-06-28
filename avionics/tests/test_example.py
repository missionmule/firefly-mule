from unittest import TestCase

class TestExample(TestCase):
    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_another(self):
        self.assertTrue('FOO'.isupper())
