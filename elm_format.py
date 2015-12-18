import subprocess
import os.path
import re
import sublime, sublime_plugin


class ElmFormatCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		command = "elm-format {} --yes".format(self.view.file_name())
		p = subprocess.Popen(command, shell=True)

class ElmFormatRegexCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.window().show_input_panel("regex", "[a-z]", self.find_files, lambda x: x, lambda: None)

	def find_files(self, s):
		root = self.view.window().folders()[0]
		for path, subdirs, files in os.walk(root):
			subdirs[:] = [d for d in subdirs if d not in ["elm-stuff", ".git"]]
			files[:] = [f for f in files if f.endswith(".elm") and re.match(s, os.path.splitext(f)[0])]
			for name in files:
				print(os.path.join(path, name))

class ElmLanguageSupport(sublime_plugin.EventListener):
	def on_pre_save(self, view):
		sel = view.sel()[0]
		region = view.word(sel)
		scope = view.scope_name(region.b)
		if scope.find('source.elm') != -1:
			settings = sublime.load_settings('Elm Language Support.sublime-settings')
			if settings.get('elm_format_on_save', False):
				view.run_command('elm_format')
