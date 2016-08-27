# -*- coding: utf-8 -*-
import re
import sys

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl


class Composite:
    """
    Helper class to identify a composite
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u'<Composite `{}`>'.format(self.name)


class Block:
    """
    Represents a block of our format.  Block being contained inside [..]

    A block may contain options split by a pipe | and the first 'valid' block
    is the one that will be used.  blocks can contain other blocks and also
    know about their parent block (if they have one)
    """

    def __init__(self, param_dict, composites, module, parent=None):
        self.commands = {}
        self.composites = composites
        self.content = []
        self.module = module
        self.options = []
        self.param_dict = param_dict
        self.parent = parent
        self.valid_blocks = set()
        self.parameters_used = []
        self.block_parameters = []

    def __repr__(self):
        return repr(self.options)

    def parameter_used(self, name):
        self.parameters_used.append(name)

    def add(self, item):
        """
        Add item to the block
        """
        self.content.append(item)

    def switch(self):
        """
        New option has been started
        """
        self.options.append(self.content)
        self.content = []

    def mark_valid(self):
        """
        Mark the current block as valid. Propogate this to any parent blocks
        """
        self.valid_blocks.add(len(self.options))
        if self.parent:
            self.parent.mark_valid()

    def set_commands(self, commands):
        """
        Process any commands into a dict and store
        commands are url query string encoded
        """
        self.commands.update(parse_qsl(commands, keep_blank_values=True))

    def is_valid_by_command(self):
        """
        Check if we have a command forcing the block to be valid or not
        """
        if 'if' in self.commands:
            _if = self.commands['if']
            if _if and _if.startswith('!'):
                if not self.param_dict.get(_if[1:]):
                    return True
                else:
                    return False
            else:
                if self.param_dict.get(_if):
                    return True
                else:
                    return False
        if 'show' in self.commands:
            return True
        # explicitly return None to aid code readability
        return None

    def set_valid_state(self):
        """
        Mark block valid if a command requests
        """
        if self.is_valid_by_command():
            self.mark_valid()
        self.set_params_used()

    def set_params_used(self):
        self.block_parameters.append(self.parameters_used)
        self.parameters_used = []

    def show(self, is_composite):
        """
        This is where we go output the content of a block and any valid child
        block that it contains.

        """
        # Start by finalising the block.
        # Any active content is added to self.options
        if self.content:
            self.options.append(self.content)

        output = []
        parameters_used = []

        for index, option in enumerate(self.options):
            if index in self.valid_blocks:
                parameters_used = self.block_parameters[index]
                # A block may be valid but has a command that causes this to be
                # disregarded.
                if self.is_valid_by_command() is False:
                    continue
                # add the content of the block and any children
                # to the output
                for item in option:
                    if isinstance(item, Block):
                        block_output, parameters = item.show(is_composite)
                        output.extend(block_output)
                        parameters_used.extend(parameters)
                    else:
                        output.append(item)
                break

        # if not building a composite then we can simply
        # build our output and return it here
        if not is_composite:
            data = ''.join(output)
            # apply our max length command
            if 'max_length' in self.commands:
                data = data[:int(self.commands['max_length'])]
            return data, parameters_used

        # Build up our output.  We join any text pieces togeather and if we
        # have composites we keep them for final substitution in the main block
        data = []
        text = ''
        for item in output:
            if not isinstance(item, Composite):
                text += item
            else:
                if text:
                    if is_composite:
                        data.append({'full_text': text})
                    else:
                        data.append(text)
                text = ''
                if self.parent is None:
                    # This is the main block so we get the actual composites
                    composite = self.composites.get(item.name)
                    parameters_used.append(item.name)
                    if isinstance(composite, list):
                        data += composite
                    else:
                        data.append(composite)
                else:
                    data.append(item)
        if text:
            if is_composite:
                data.append({'full_text': text})
            else:
                data.append(text)

        return data, parameters_used


class Formatter:
    """
    Formatter for processing format strings via the format method.
    """

    TOKENS = [
        r'(?P<block_start>\[)'
        r'|(?P<block_end>\])'
        r'|(?P<switch>\|)'
        r'|(\\\?(?P<command>\S*)\s)'
        r'|(?P<escaped>(\\.|\{\{|\}\}))'
        r'|(?P<placeholder>(\{(?P<key>([^}\\\:\!]|\\.)*)(([^}\\]|\\.)*)?\}))'
        r'|(?P<literal>([^\[\]\\\{\}\|])+)'
        r'|(?P<lost_brace>(\}))'
    ]

    python2 = sys.version_info < (3, 0)
    reg_ex = re.compile(TOKENS[0], re.M | re.I)

    def format(self, format_string, module=None, param_dict=None,
               composites=None, return_used=False):
        """
        Format a string.
        substituting place holders which can be found in
        composites, param_dict or as attributes of the supplied module.
        """

        is_composite = composites is not None

        def set_param(param, value, key):
            """
            Converts a placeholder to a string value.
            We fix python 2 unicode issues and use string.format()
            to ensure that formatting is applied correctly
            """
            if self.python2 and isinstance(param, str):
                param = param.decode('utf-8')
            if param:
                value = value.format(**{key: param})
                block.add(value)
                block.mark_valid()
                return True
            return False

        # fix python 2 unicode issues
        if self.python2 and isinstance(format_string, str):
            format_string = format_string.decode('utf-8')

        if param_dict is None:
            param_dict = {}

        if composites is None:
            composites = {}

        block = Block(param_dict, composites, module)

        # Tokenize the format string and process them
        for token in re.finditer(self.reg_ex, format_string):
            value = token.group(0)
            if token.group('block_start'):
                # Create new block
                new_block = Block(param_dict, composites, module, block)
                block.add(new_block)
                block = new_block
            elif token.group('block_end'):
                # Close block setting any valid state as needed
                # and return to parent block to continue
                block.set_valid_state()
                if not block.parent:
                    raise Exception('Too many `]`')
                block = block.parent
            elif token.group('switch'):
                # a new option has been created
                block.set_valid_state()
                block.switch()
            elif token.group('placeholder'):
                # Found a {placeholder}
                key = token.group('key')
                if key in composites:
                    # Add the composite
                    if composites[key]:
                        block.add(Composite(key))
                        block.mark_valid()
                elif key in param_dict:
                    # was a supplied parameter
                    param = param_dict.get(key)
                    if set_param(param, value, key):
                        block.parameter_used(key)
                elif module and hasattr(module, key):
                    # attribute of the module
                    param = getattr(module, key)
                    if not hasattr(param, '__call__'):
                        if set_param(param, value, key):
                            block.parameter_used(key)
                    else:
                        block.add(value)
                else:
                    # substitution not found so add as a literal
                    block.add(value)
            elif token.group('literal'):
                block.add(value)
            elif token.group('lost_brace'):
                # due to how parsing happens we can get a lonesome }
                # eg in format_sting '{{something}' this fixes that issue
                block.add(value)
            elif token.group('command'):
                # a block command has been found
                block.set_commands(token.group('command'))
            elif token.group('escaped'):
                # escaped characters add unescaped values
                if value[0] in ['\\', '{', '}']:
                    value = value[1:]
                block.add(value)

        if block.parent:
            raise Exception('Block not closed')

        # This is the main block if none of the sections are valid use the last
        # one for situations like '{placeholder}|Nothing'
        if not block.valid_blocks:
            block.mark_valid()
        block.set_params_used()
        output, parameter_used = block.show(is_composite)
        if return_used:
            return output, parameter_used
        return output


if __name__ == '__main__':

    """
    Run formatter tests
    """

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
    }

    composites = {
        'complex': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'}],
        'simple': {'full_text': 'NY 12:34'},
        'empty': [],
    }

    class Module:
        module_param = 'something'

        def module_method(self):
            return 'method'

        @ property
        def module_property(self):
            return 'property'

    tests = [
        {
            'format': u'hello ☂',
            'expected': u'hello ☂',
        },
        {
            'format': 'hello ☂',
            'expected': u'hello ☂',
        },
        {
            'format': '[hello]',
            'expected': '',
        },
        {
            'format': r'\\ \[ \] \{ \}',
            'expected': r'\ [ ] { }',
        },
        {
            'format': '{{hello}}',
            'expected': '{hello}',
        },
        {
            'format': '{{hello}',
            'expected': '{hello}',
        },
        {
            'format': '{?bad name}',
            'expected': 'evil',
        },
        {
            'format': '{☂ Very bad name }',
            'expected': '☂ extremely evil',
        },
        {
            'format': '{missing} {name} {number}',
            'expected': '{missing} Björk 42',
        },
        {
            'format': '{missing}|{name}|{number}',
            'expected': 'Björk',
        },
        {
            'format': '{missing}|empty',
            'expected': 'empty',
        },
        {
            'format': '[{missing}|empty]',
            'expected': '',
        },
        {
            'format': 'pre [{missing}|empty] post',
            'expected': 'pre  post',
        },
        {
            'format': 'pre [{missing}|empty] post|After',
            'expected': 'After',
        },
        {
            'format': '{module_param}',
            'expected': 'something',
        },
        {
            'format': '{module_method}',
            'expected': '{module_method}',
        },
        {
            'format': '{module_property}',
            'expected': 'property',
        },
        {
            'format': 'Hello {name}!',
            'expected': 'Hello Björk!',
        },
        {
            'format': '[Hello {name}!]',
            'expected': 'Hello Björk!',
        },
        {
            'format': '[Hello {missing}|Anon!]',
            'expected': '',
        },
        {
            'format': 'zero [one [two [three [no]]]]|Numbers',
            'expected': 'Numbers',
        },
        {
            'format': 'zero [one [two [three [{yes}]]]]|Numbers',
            'expected': 'zero one two three True',
        },
        {
            'format': 'zero [one [two [three [{no}]]]]|Numbers',
            'expected': 'Numbers',
        },
        # python 2 unicode
        {
            'format': 'Hello {python2_unicode}! ☂',
            'expected': 'Hello Björk! ☂',
        },
        {
            'format': u'Hello {python2_unicode}! ☂',
            'expected': 'Hello Björk! ☂',
        },
        {
            'format': 'Hello {python2_str}! ☂',
            'expected': 'Hello Björk! ☂',
        },
        {
            'format': u'Hello {python2_str}! ☂',
            'expected': 'Hello Björk! ☂',
        },
        # formatting
        {
            'format': '{name}',
            'expected': 'Björk',
        },
        {
            'format': '{name!s}',
            'expected': 'Björk',
        },
        {
            'format': '{name!r}',
            'expected': "'Björk'",
            'py3only': True,
        },
        {
            'format': '{name:7}',
            'expected': 'Björk  ',
        },
        {
            'format': '{name:<7}',
            'expected': 'Björk  ',
        },
        {
            'format': '{name:>7}',
            'expected': '  Björk',
        },
        {
            'format': '{name:*^9}',
            'expected': '**Björk**',
        },
        {
            'format': '{long_str}',
            'expected': 'I am a long string though not too long',
        },
        {
            'format': '{long_str:.6}',
            'expected': 'I am a',
        },
        {
            'format': '{number}',
            'expected': '42',
        },
        {
            'format': '{number:04d}',
            'expected': '0042',
        },
        {
            'format': '{pi}',
            'expected': '3.14159265359',
        },
        {
            'format': '{pi:05.2f}',
            'expected': '03.14',
        },
        # commands
        {
            'format': '{missing}|\?show Anon',
            'expected': 'Anon',
        },
        {
            'format': 'Hello [{missing}|[\?show Anon]]!',
            'expected': 'Hello Anon!',
        },
        {
            'format': '[\?if=yes Hello]',
            'expected': 'Hello',
        },
        {
            'format': '[\?if=no Hello]',
            'expected': '',
        },
        {
            'format': '[\?if=missing Hello]',
            'expected': '',
        },
        {
            'format': '[\?if=!yes Hello]',
            'expected': '',
        },
        {
            'format': '[\?if=!no Hello]',
            'expected': 'Hello',
        },
        {
            'format': '[\?if=!missing Hello]',
            'expected': 'Hello',
        },
        {
            'format': '[\?if=yes Hello[ {name}]]',
            'expected': 'Hello Björk',
        },
        {
            'format': '[\?if=no Hello[ {name}]]',
            'expected': '',
        },
        {
            'format': '[\?max_length=10 Hello {name} {number}]',
            'expected': 'Hello Björ',
        },
        {
            'format': '\?max_length=9 Hello {name} {number}',
            'expected': 'Hello Bjö',
        },
        # Errors
        {
            'format': 'hello]',
            'exception': 'Too many `]`',
        },
        {
            'format': '[hello',
            'exception': 'Block not closed',
        },
        # Composites
        {
            'format': '{empty}',
            'expected': [],
            'composite': True,
        },
        {
            'format': '{simple}',
            'expected': [{'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': '{complex}',
            'expected': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': 'TEST {simple}',
            'expected': [{'full_text': u'TEST '}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': '[{empty}]',
            'expected': [],
            'composite': True,
        },
        {
            'format': '[{simple}]',
            'expected': [{'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': '[{complex}]',
            'expected': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': 'TEST [{simple}]',
            'expected': [{'full_text': u'TEST '}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': '{complex} {complex}',
            'expected': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'},
                         {'full_text': ' '}, {'full_text': 'LA 09:34'},
                         {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': 'TEST [{simple}|{complex}]',
            'expected': [{'full_text': u'TEST '}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        {
            'format': 'TEST {simple}|{complex}',
            'expected': [{'full_text': u'TEST '}, {'full_text': 'NY 12:34'}],
            'composite': True,
        },
        # parameters used
        {
            'format': u'hello ☂',
            'expected': u'hello ☂',
            'used': [],
        },
        {
            'format': 'hello ☂',
            'expected': u'hello ☂',
        },
        {
            'format': '[hello]',
            'expected': '',
            'used': [],
        },
        {
            'format': '{missing} {name} {number}',
            'expected': '{missing} Björk 42',
            'used': ['name', 'number'],
        },
        {
            'format': '{missing}|{name}|{number}',
            'expected': 'Björk',
            'used': ['name'],
        },
        {
            'format': '{missing}|empty',
            'expected': 'empty',
            'used': [],
        },
        {
            'format': 'zero [one [two [three [no]]]]|Numbers',
            'expected': 'Numbers',
            'used': [],
        },
        {
            'format': 'zero [one [two [three [{yes}]]]]|Numbers',
            'expected': 'zero one two three True',
            'used': ['yes'],
        },
        {
            'format': 'zero [one [two [three [{no}]]]]|Numbers',
            'expected': 'Numbers',
            'used': [],
        },
        # commands
        {
            'format': '{missing}|\?show Anon',
            'expected': 'Anon',
            'used': [],
        },
        {
            'format': '[\?if=yes Hello]',
            'expected': 'Hello',
            'used': [],
        },
        {
            'format': '[\?if=no Hello]',
            'expected': '',
            'used': [],
        },
        {
            'format': '[\?if=yes Hello[ {name}]]',
            'expected': 'Hello Björk',
            'used': ['name'],
        },
        {
            'format': '[\?if=no Hello[ {name}]]',
            'expected': '',
            'used': [],
        },
        # Composites
        {
            'format': '{empty}',
            'expected': [],
            'composite': True,
            'used': [],
        },
        {
            'format': '{simple}',
            'expected': [{'full_text': 'NY 12:34'}],
            'composite': True,
            'used': ['simple'],
        },
        {
            'format': '{complex}',
            'expected': [{'full_text': 'LA 09:34'}, {'full_text': 'NY 12:34'}],
            'composite': True,
            'used': ['complex'],
        },
        {
            'format': 'TEST [{simple}]',
            'expected': [{'full_text': u'TEST '}, {'full_text': 'NY 12:34'}],
            'composite': True,
            'used': ['simple'],
        },
    ]

    passed = 0
    failed = 0
    module = Module()

    for test in tests:
        if test.get('py3only') and f.python2:
            continue
        try:
            if test.get('composite'):
                if 'used' in test:
                    result, parameters_used = f.format(
                        test['format'],
                        module,
                        param_dict,
                        composites,
                        True,
                    )
                else:
                    result = f.format(
                        test['format'],
                        module,
                        param_dict,
                        composites,
                    )
                    parameters_used = None
            else:
                if 'used' in test:
                    result, parameters_used = f.format(
                        test['format'], module, param_dict, return_used=True
                    )
                else:
                    result = f.format(test['format'], module, param_dict)
                    parameters_used = None
        except Exception as e:
            if test.get('exception') == str(e):
                passed += 1
                continue
            else:
                print('Fail %r' % test['format'])
                print('exception raised %r' % e)
                print('')
                failed += 1
        expected = test.get('expected')
        expected_params = test.get('used')
        if f.python2 and isinstance(expected, str):
            expected = expected.decode('utf-8')
        if result == expected and parameters_used == expected_params:
            passed += 1
        else:
            print('Fail %r' % test['format'])
            if result != expected:
                print('Result')
                print('expected %r' % expected)
                print('got      %r' % result)
            if parameters_used != expected_params:
                print('Parameters')
                print('expected %r' % expected_params)
                print('got      %r' % parameters_used)
            print('')
            failed += 1

    print('Tests complete: %s passed %s failed' % (passed, failed))
