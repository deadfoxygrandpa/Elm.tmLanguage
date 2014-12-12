import sublime, sublime_plugin
import os
import codecs
import subprocess
import threading
import plistlib

# File I/O

PACKAGES_PATH = sublime.packages_path()
ELM_LANGUAGE_SUPPORT_PATH = os.path.join(PACKAGES_PATH, 'Elm Language Support')

def write_file(filename, s):
    with codecs.open(filename, "w", "utf-8") as f:
        f.write(s)

def write_bin_file(filename, s):
    with codecs.open(filename, "wb") as f:
        f.write(s)

def read_file(filename):
    with codecs.open(filename, "r", "utf-8") as f:
        return f.read()

def abs_path(filename):
    return os.path.join(PACKAGES_PATH, os.path.normpath(filename[9:]))

def read_color_scheme(color_scheme_path):
	return plistlib.readPlist(color_scheme_path)

def write_color_scheme(color_scheme, filename):
	path = os.path.join(ELM_LANGUAGE_SUPPORT_PATH, filename)
	plistlib.writePlist(color_scheme, path)
	return path

# Miscellaneous

def get_color_scheme(view):
	return abs_path(view.settings().get('color_scheme'))

def get_colors(color_scheme):
	settings = [v['settings'] for v in color_scheme['settings'] if ['settings'] == v.keys()][0]
	return (settings['background'], settings['foreground'])

def slightly_perturb_color(color):
	color = color.upper()
	last_digit = color[-1]
	if last_digit == 'F':
		last_digit = 'E'
	else:
		last_digit = int(last_digit, 16) # to an int
		last_digit = hex(last_digit - 1) # to an '0x' prepended string
		last_digit = last_digit[-1].upper()
	return color[:-1] + last_digit

def build_scope_settings(name, scope_name, background, foreground):
	settings = {'background': background, 'foreground:': foreground}
	return {'scope': scope_name, 'name': name, 'settings': settings}

def add_scope_to_color_scheme(color_scheme, scope_settings):
	color_scheme['settings'].append(scope_settings)
	return color_scheme

def write_perturbed_color_scheme(color_scheme):
	background, foreground = get_colors(color_scheme)
	background = slightly_perturb_color(background)
	foreground = slightly_perturb_color(foreground)
	scope_settings = build_scope_settings('Elm Language Support Inactive', 'elmlanguagesupport', background, foreground)
	color_scheme = add_scope_to_color_scheme(color_scheme, scope_settings)
	new_color_scheme_path = write_color_scheme(color_scheme, 'Elm Language Support.tmTheme')
	return 'Packages/Elm Language Support/Elm Language Support.tmTheme'

def switch_color_scheme(view, color_scheme_path):
	view.settings().set('color_scheme', color_scheme_path)

def invert_regions(size, regions):
    start = 0
    inverted = []
    for region in regions:
        inverted.append(sublime.Region(start, region.a))
        start = region.b
    inverted.append(sublime.Region(start, size))
    return inverted

# Commands

def create_and_switch_color_scheme(view):
    color_scheme = read_color_scheme(get_color_scheme(view))
    new_color_scheme_path = write_perturbed_color_scheme(color_scheme)
    switch_color_scheme(view, new_color_scheme_path)

def hide_scopes(view):
    point = view.sel()[0].a
    score = view.score_selector(point, 'entity.glsl.elm')
    regions = view.find_by_selector('entity.glsl.elm')
    view.erase_regions('elmlanguagesupporthidden')
    if score == 0:
        view.add_regions('elmlanguagesupporthidden', regions, 'elmlanguagesupport')
    else:
        view.add_regions('elmlanguagesupporthidden', invert_regions(view.size(), regions), 'elmlanguagesupport')

class CreateAndSwitchColorScheme(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
        # create_and_switch_color_scheme(self.view)

class HideScopes(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        hide_scopes(view)

# Event Listeners

class ElmLanguageSupportEventListener(sublime_plugin.EventListener):

    def on_load(self, view):
        create_and_switch_color_scheme(view)

    def on_selection_modified(self, view):
        hide_scopes(view)
