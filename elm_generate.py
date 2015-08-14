import json
import os
import sys

class Module(object):
	def __init__(self, data):
		self.name = data['name']
		self.values = [name(v['raw']) + ' : ' + signature(v['raw']) for v in data['values']]
		self.valueNames = [name(v) for v in self.values]
		self.datatypes = [v['name'] for v in data['datatypes']]
		self.constructors = [[v['name'] for v in x['constructors']] for x in data['datatypes']]
		self.aliases = [v['name'] for v in data['aliases']]

	def include_text(self):
		s = '<dict>\n\t<key>include</key>\n\t<string>#{}</string>\n</dict>'.format(self.name.lower())
		return s

	def moduleText(self):
		s = '<key>{nameLower}</key>\n<dict>\n\t<key>captures</key>\n\t<dict>\n\t\t<key>1</key>\n\t\t<dict>\n\t\t\t<key>name</key>\n\t\t\t<string>variable.parameter</string>\n\t\t</dict>\n\t\t<key>2</key>\n\t\t<dict>\n\t\t\t<key>name</key>\n\t\t\t<string>variable.parameter</string>\n\t\t</dict>\n\t\t<key>3</key>\n\t\t<dict>\n\t\t\t<key>name</key>\n\t\t\t<string>support.function.elm</string>\n\t\t</dict>\n\t</dict>\n\t<key>match</key>\n\t<string>\\b({name})(.)({values})\\b</string>\n\t<key>name</key>\n\t<string>variable.parameter</string>\n</dict>'
		values = '|'.join([n for n in self.valueNames if not n.startswith('(')])
		if self.aliases:
			values += '|' + '|'.join(self.aliases)
		if self.datatypes:
			values += '|' + '|'.join(self.datatypes)
		return s.format(nameLower=self.name.lower(), name=self.name, values=values)

	def snippets(self):
		base = 'Snippets'
		s = '<snippet>\n\t<content><![CDATA[\n{autocomplete}\n]]></content>\n\t<!-- Optional: Set a tabTrigger to define how to trigger the snippet -->\n\t<tabTrigger>{name}</tabTrigger>\n\t<!-- Optional: Set a scope to limit where the snippet will trigger -->\n\t<scope>source.elm</scope>\n\t<description>{signature}</description>\n</snippet>'
		for v in [func for func in self.values if not name(func).startswith('(')]:
			subdirectories = self.name.split('.')
			path = '{}' + '\\{}'*(len(subdirectories))
			path = path.format(base, *subdirectories)

			if not os.path.exists(path):
				os.makedirs(path)

			path += '\\{}'

			with open(path.format(name(v) + '.sublime-snippet'), 'w') as f:
				f.write(s.format(autocomplete=make_autocomplete(v), name=name(v), signature=signature(v)))

			print('Wrote {}'.format(path.format(name(v) + '.sublime-snippet')))

def name(t):
	return t.split(' : ')[0].strip()

def signature(t):
	return t.split(' : ')[1].strip()

def hintize(t):
	first = t[0].lower()
	t = t.replace(' ', '')
	return first + ''.join(t[1:])

def typeFormat(t):
	if t[0] == '[':
		return 'ListOf' + typeFormat(t[1:-1])
	elif t[0] == '(':
		return ''.join([unicode(v.strip()) for v in t[1:-1].split(',')]) + 'Tuple'
	else:
		if len(t.split(' ')) == 1:
			return t
		else:
			x = t.split(' ')
			return x[0] + ''.join([typeFormat(v) for v in x[1:]])

def tokenize(t):
	return [v.strip() for v in t.split('->')]

def print_type(t):
	print(name(t))
	print([typeFormat(v) for v in tokenize(signature(t))])

def make_autocomplete(t):
	s = '{}'.format(name(t))
	args = arguments(signature(t))
	for n, arg in enumerate(args):
		s += ' ${{{n}:{arg}}}'.format(n=n+1, arg=arg)
	return s

def arguments(signature):
	args = [v.strip() for v in signature.split('->')][:-1]
	new_args = []
	open_parens = 0
	for arg in args:
		parens = arg.count('(') - arg.count(')')
		if parens and not open_parens:
			new_args.append('function')
		elif open_parens != 0:
			open_parens += parens
			continue
		else:
			new_args.append(argify(arg))
		open_parens += parens
	return new_args

def argify(s):
	if s.startswith('('):
		return 'tuple'
	elif s.startswith('['):
		return 'list'
	elif len(s.split(' ')) > 1:
		return s.split(' ')[0].lower()
	else:
		return s.lower()

def loadDocs(path):
	with open(path) as f:
		return json.load(f)


if __name__ == '__main__':
	## Usage: pass in docs.json from cabal's elm directory
	path = sys.argv[1]
	prelude = ['Basics', 'List', 'Signal', 'Text', 'Maybe', 'Time', 'Graphics.Element', 'Color', 'Graphics.Collage']

	modules = [Module(m) for m in loadDocs(path)]

	print('Prelude:')
	print('show|')
	for m in modules:
		if m.name in prelude:
			print('|'.join([n for n in m.valueNames if not n.startswith('(')]))

	print('\n'*5)

	print('Prelude Aliases and Datatypes:')
	print('Int|Float|Char|Bool|String|True|False')
	for m in modules:
		if m.name in prelude:
			print('|'.join([n for n in (m.datatypes + m.aliases) if not n.startswith('(')]) + '|')

	print('\n'*5)

	print('Includes:')
	for m in modules:
		print(m.include_text())

	print('\n'*5)

	print('Includes Continued:')
	for m in modules:
		print(m.moduleText())

	print('\n'*5)

	print('Constructors:')
	print('\(\)|\[\]|True|False|Int|Char|Bool|String|')
	for m in modules:
		if m.name in prelude:
			for c in m.constructors:
				print('|'.join(c) + '|')

	print('\n'*5)

	print('Writing Autocompletion Snippets...:')
	for m in modules:
		if m.name in prelude:
			m.snippets()
			print('\n'*2)

	with open('Snippets\\Basics\\markdown.sublime-snippet', 'w') as f:
		f.write('<snippet>\n<content><![CDATA[\n[markdown|\n\n${1}\n\n|]\n\n\n]]></content>\n<!-- Optional: Set a tabTrigger to define how to trigger the snippet -->\n<tabTrigger>markdown</tabTrigger>\n<!-- Optional: Set a scope to limit where the snippet will trigger -->\n<scope>source.elm</scope>\n<description>A markdown block</description>\n</snippet>')
	print('Wrote markdown.sublime-snippet')
