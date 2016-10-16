# -*- coding: utf-8 -*-
"""
Run formatter tests
"""

import platform

from py3status.formatter import Formatter

is_pypy = platform.python_implementation() == 'PyPy'
f = Formatter()

param_dict = {
    'name': u'Björk',
    'number': 42,
    'pi': 3.14159265359,
    'yes': True,
    'no': False,
    'empty': '',
    'None': None,
    '?bad name': 'evil',
    u'☂ Very bad name ': u'☂ extremely evil',
    'long_str': 'I am a long string though not too long',
    'python2_unicode': u'Björk',
    'python2_str': 'Björk',
    'zero': 0,
}

composites = {
    'complex': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'}],
    'simple': {'full_text': 'NY 12:34'},
    'empty': [],
}


class Module:
    module_param = 'something'

    class py3:
        COLOR_BAD = '#FF0000'
        COLOR_DEGRADED = '#FF00'
        COLOR_GOOD = '#00FF00'

    def module_method(self):
        return 'method'

    @property
    def module_property(self):
        return 'property'


def run_formatter(test_dict):
    if test_dict.get('py3only') and f.python2:
        return
    if not test_dict.get('pypy', True) and is_pypy:
        return
    try:
        module = Module()
        if test_dict.get('composite'):
            result = f.format(test_dict['format'], module, param_dict, composites, )
        else:
            result = f.format(test_dict['format'], module, param_dict)
    except Exception as e:
        if test_dict.get('exception') == str(e):
            assert(True)
            return
        raise e

    expected = test_dict.get('expected')
    if f.python2 and isinstance(expected, str):
        expected = expected.decode('utf-8')
    assert (result == expected)


def test_1():
    run_formatter({'format': u'hello ☂', 'expected': u'hello ☂', })


def test_2():
    run_formatter({'format': 'hello ☂', 'expected': u'hello ☂', })


def test_3():
    run_formatter({'format': '[hello]', 'expected': '', })


def test_4():
    run_formatter({'format': r'\\ \[ \] \{ \}', 'expected': r'\ [ ] { }', })


def test_5():
    run_formatter({'format': '{{hello}}', 'expected': '{hello}', })


def test_6():
    run_formatter({'format': '{{hello}', 'expected': '{hello}', })


def test_7():
    run_formatter({'format': '{?bad name}', 'expected': 'evil', })


def test_8():
    run_formatter({
        'format': '{☂ Very bad name }',
        'expected': '☂ extremely evil',
        # unicode.format({<unicode>: ..}) is broken in pypy
        'pypy': False,
    })


def test_9():
    run_formatter({
        'format': '{missing} {name} {number}',
        'expected': '{missing} Björk 42',
    })


def test_10():
    run_formatter({
        'format': '{missing}|{name}|{number}',
        'expected': 'Björk',
    })


def test_11():
    run_formatter({'format': '{missing}|empty', 'expected': 'empty', })


def test_12():
    run_formatter({'format': '[{missing}|empty]', 'expected': '', })


def test_13():
    run_formatter({
        'format': 'pre [{missing}|empty] post',
        'expected': 'pre  post',
    })


def test_14():
    run_formatter({
        'format': 'pre [{missing}|empty] post|After',
        'expected': 'After',
    })


def test_15():
    run_formatter({'format': '{module_param}', 'expected': 'something', })


def test_16():
    run_formatter({
        'format': '{module_method}',
        'expected': '{module_method}',
    })


def test_17():
    run_formatter({'format': '{module_property}', 'expected': 'property', })


def test_18():
    run_formatter({'format': 'Hello {name}!', 'expected': 'Hello Björk!', })


def test_19():
    run_formatter({'format': '[Hello {name}!]', 'expected': 'Hello Björk!', })


def test_20():
    run_formatter({'format': '[Hello {missing}|Anon!]', 'expected': '', })


def test_21():
    run_formatter({
        'format': 'zero [one [two [three [no]]]]|Numbers',
        'expected': 'Numbers',
    })


def test_22():
    run_formatter({
        'format': 'zero [one [two [three [{yes}]]]]|Numbers',
        'expected': 'zero one two three True',
    })


def test_23():
    run_formatter({
        'format': 'zero [one [two [three [{no}]]]]|Numbers',
        'expected': 'Numbers',
    })


def test_24():
    run_formatter(
        # zero/False/None etc
        {
            'format': '{zero}',
            'expected': '0',
        })


def test_25():
    run_formatter({'format': '[{zero}] hello', 'expected': '0 hello', })


def test_26():
    run_formatter({
        'format': '[{zero} ping] hello',
        'expected': '0 ping hello',
    })


def test_27():
    run_formatter({'format': '{None}', 'expected': '', })


def test_28():
    run_formatter({'format': '[{None}] hello', 'expected': ' hello', })


def test_29():
    run_formatter({'format': '[{None} ping] hello', 'expected': ' hello', })


def test_30():
    run_formatter({'format': '{no}', 'expected': '', })


def test_31():
    run_formatter({'format': '[{no}] hello', 'expected': ' hello', })


def test_32():
    run_formatter({'format': '[{no} ping] hello', 'expected': ' hello', })


def test_33():
    run_formatter({'format': '{yes}', 'expected': 'True', })


def test_34():
    run_formatter({'format': '[{yes}] hello', 'expected': 'True hello', })


def test_35():
    run_formatter({
        'format': '[{yes} ping] hello',
        'expected': 'True ping hello',
    })


def test_36():
    run_formatter({'format': '{empty}', 'expected': '', })


def test_37():
    run_formatter({'format': '[{empty}] hello', 'expected': ' hello', })


def test_38():
    run_formatter({'format': '[{empty} ping] hello', 'expected': ' hello', })


def test_39():
    run_formatter(
        # python 2 unicode
        {
            'format': 'Hello {python2_unicode}! ☂',
            'expected': 'Hello Björk! ☂',
        })


def test_40():
    run_formatter({
        'format': u'Hello {python2_unicode}! ☂',
        'expected': 'Hello Björk! ☂',
    })


def test_41():
    run_formatter({
        'format': 'Hello {python2_str}! ☂',
        'expected': 'Hello Björk! ☂',
    })


def test_42():
    run_formatter({
        'format': u'Hello {python2_str}! ☂',
        'expected': 'Hello Björk! ☂',
    })


def test_43():
    run_formatter(
        # formatting
        {
            'format': '{name}',
            'expected': 'Björk',
        })


def test_44():
    run_formatter({'format': '{name!s}', 'expected': 'Björk', })


def test_45():
    # the repesentation is different in python2 "u'Björk'"
    run_formatter({
        'format': '{name!r}',
        'expected': "'Björk'",
        'py3only': True,
    })


def test_46():
    run_formatter({'format': '{name:7}', 'expected': 'Björk  ', })


def test_47():
    run_formatter({'format': '{name:<7}', 'expected': 'Björk  ', })


def test_48():
    run_formatter({'format': '{name:>7}', 'expected': '  Björk', })


def test_49():
    run_formatter({'format': '{name:*^9}', 'expected': '**Björk**', })


def test_50():
    run_formatter({
        'format': '{long_str}',
        'expected': 'I am a long string though not too long',
    })


def test_51():
    run_formatter({'format': '{long_str:.6}', 'expected': 'I am a', })


def test_52():
    run_formatter({'format': '{number}', 'expected': '42', })


def test_53():
    run_formatter({'format': '{number:04d}', 'expected': '0042', })


def test_54():
    run_formatter({'format': '{pi}', 'expected': '3.14159265359', })


def test_55():
    run_formatter({'format': '{pi:05.2f}', 'expected': '03.14', })


def test_56():
    run_formatter(
        # commands
        {
            'format': '{missing}|\?show Anon',
            'expected': 'Anon',
        })


def test_57():
    run_formatter({
        'format': 'Hello [{missing}|[\?show Anon]]!',
        'expected': 'Hello Anon!',
    })


def test_58():
    run_formatter({'format': '[\?if=yes Hello]', 'expected': 'Hello', })


def test_59():
    run_formatter({'format': '[\?if=no Hello]', 'expected': '', })


def test_60():
    run_formatter({'format': '[\?if=missing Hello]', 'expected': '', })


def test_61():
    run_formatter({'format': '[\?if=!yes Hello]', 'expected': '', })


def test_62():
    run_formatter({'format': '[\?if=!no Hello]', 'expected': 'Hello', })


def test_63():
    run_formatter({'format': '[\?if=!missing Hello]', 'expected': 'Hello', })


def test_64():
    run_formatter({
        'format': '[\?if=yes Hello[ {name}]]',
        'expected': 'Hello Björk',
    })


def test_65():
    run_formatter({'format': '[\?if=no Hello[ {name}]]', 'expected': '', })


def test_66():
    run_formatter({
        'format': '[\?max_length=10 Hello {name} {number}]',
        'expected': 'Hello Björ',
    })


def test_67():
    run_formatter({
        'format': '\?max_length=9 Hello {name} {number}',
        'expected': 'Hello Bjö',
    })


def test_68():
    run_formatter(
        # Errors
        {
            'format': 'hello]',
            'exception': 'Too many `]`',
        })


def test_69():
    run_formatter({'format': '[hello', 'exception': 'Block not closed', })


def test_70():
    run_formatter(
        # Composites
        {
            'format': '{empty}',
            'expected': [],
            'composite': True,
        })


def test_71():
    run_formatter({
        'format': '{simple}',
        'expected': [{'full_text': 'NY 12:34'}],
        'composite': True,
    })


def test_72():
    run_formatter({
        'format': '{complex}',
        'expected': [{'full_text': 'LA 09:34NY 12:34'}],
        'composite': True,
    })


def test_73():
    run_formatter({
        'format': 'TEST {simple}',
        'expected': [{'full_text': u'TEST NY 12:34'}],
        'composite': True,
    })


def test_74():
    run_formatter({'format': '[{empty}]', 'expected': [], 'composite': True, })


def test_75():
    run_formatter({
        'format': '[{simple}]',
        'expected': [{'full_text': 'NY 12:34'}],
        'composite': True,
    })


def test_76():
    run_formatter({
        'format': '[{complex}]',
        'expected': [{'full_text': 'LA 09:34NY 12:34'}],
        'composite': True,
    })


def test_77():
    run_formatter({
        'format': 'TEST [{simple}]',
        'expected': [{'full_text': u'TEST NY 12:34'}],
        'composite': True,
    })


def test_78():
    run_formatter({
        'format': '{simple} TEST [{name}[ {number}]]',
        'expected': [
            {'full_text': u'NY 12:34 TEST Björk 42'}
        ],
        'composite': True,
    })


def test_else_true():
    run_formatter({
        'format': '[\?if=yes Hello|Goodbye]',
        'expected': 'Hello',
    })


def test_else_false():
    run_formatter({
        'format': '[\?if=no Hello|Goodbye|Something else]',
        'expected': 'Goodbye',
    })

# block colors


def test_color_1():
    run_formatter({
        'format': '[\?color=bad {name}]',
        'expected':  [{'full_text': u'Björk', 'color': '#FF0000'}],
    })


def test_color_2():
    run_formatter({
        'format': '[\?color=good Name [\?color=bad {name}] hello]',
        'expected':  [
            {'full_text': 'Name ', 'color': '#00FF00'},
            {'full_text': u'Björk', 'color': '#FF0000'},
            {'full_text': ' hello', 'color': '#00FF00'}
        ],
    })


def test_color_3():
    run_formatter({
        'format': '[\?max_length=20&color=good Name [\?color=bad {name}] hello]',
        'expected':  [
            {'full_text': 'Name ', 'color': '#00FF00'},
            {'full_text': u'Björk', 'color': '#FF0000'},
            {'full_text': ' hello', 'color': '#00FF00'}
        ],
    })


def test_color_4():
    run_formatter({
        'format': '[\?max_length=8&color=good Name [\?color=bad {name}] hello]',
        'expected':  [
            {'full_text': 'Name ', 'color': '#00FF00'},
            {'full_text': u'Bjö', 'color': '#FF0000'}
        ],

    })


def test_color_5():
    run_formatter({
        'format': '[\?color=bad {name}][\?color=good {name}]',
        'expected': [
            {'full_text': u'Björk', 'color': '#FF0000'},
            {'full_text': u'Björk', 'color': '#00FF00'}
        ],
    })


def test_color_6():
    run_formatter({
        'format': '[\?color=bad {name}] [\?color=good {name}]',
        'expected': [
            {'full_text': u'Björk', 'color': '#FF0000'},
            {'full_text': ' '},
            {'full_text': u'Björk', 'color': '#00FF00'}
        ],
    })
