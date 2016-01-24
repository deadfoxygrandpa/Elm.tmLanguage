from __future__ import print_function

import subprocess
import os, os.path
import re
import sublime, sublime_plugin


class ElmFormatCommand(sublime_plugin.TextCommand):
	def run(self, edit):

		# Hide the console window on Windows
		shell = False
		path_separator = ':'
		if os.name == "nt":
		    shell = True
		    path_separator = ';'

		settings = sublime.load_settings('Elm Language Support.sublime-settings')
		path = settings.get('elm_paths', '')
		if path:
			old_path = os.environ['PATH']
			os.environ['PATH'] = os.path.expandvars(path + path_separator + '$PATH')

		command = ['elm-format', self.view.file_name(), '--yes']
		p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)

		if path:
			os.environ['PATH'] = old_path

		output, errors = p.communicate()
		
		if settings.get('debug', False):
		    string_settings = sublime.load_settings('Elm User Strings.sublime-settings')
		    print(string_settings.get('logging.prefix', '') + '(elm-format) ' + str(output.strip()), '\nerrors: ' + str(errors.strip()))
		    if str(errors.strip()):
		        print('Your PATH is: ', os.environ['PATH'])


class ElmFormatOnSave(sublime_plugin.EventListener):
	def on_post_save(self, view):
		sel = view.sel()[0]
		region = view.word(sel)
		scope = view.scope_name(region.b)
		if scope.find('source.elm') != -1:
			settings = sublime.load_settings('Elm Language Support.sublime-settings')
			if settings.get('elm_format_on_save', True):
				regex = settings.get('elm_format_filename_filter', '')
				if not (len(regex) > 0 and re.search(regex, view.file_name()) is not None):
					view.run_command('elm_format')
