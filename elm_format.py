import subprocess
import re
import sublime, sublime_plugin


class ElmFormatCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		command = "elm-format {} --yes".format(self.view.file_name())
		p = subprocess.Popen(command, shell=True)


class ElmLanguageSupport(sublime_plugin.EventListener):
	def on_pre_save(self, view):
		sel = view.sel()[0]
		region = view.word(sel)
		scope = view.scope_name(region.b)
		if scope.find('source.elm') != -1:
			settings = sublime.load_settings('Elm Language Support.sublime-settings')
			if settings.get('elm_format_on_save', False):
				regex = settings.get('elm_format_filename_filter', '')
				if not (len(regex) > 0 and re.search(regex, view.file_name()) is not None):
					view.run_command('elm_format')
