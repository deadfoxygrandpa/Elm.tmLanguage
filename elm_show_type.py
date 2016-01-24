from __future__ import print_function

import webbrowser
import os, os.path
import subprocess
import json
import re
from difflib import SequenceMatcher

import sublime, sublime_plugin

try:     # ST3
    from .elm_project import ElmProject
except:  # ST2
    from elm_project import ElmProject

LOOKUPS = {}

def join_qualified(region, view):
    """
    Given a region, expand outward on periods to return a new region defining
    the entire word, in the context of Elm syntax.

    For example, when the region encompasses the 'map' part of a larger
    'Dict.map' word, this function will return the entire region encompassing
    'Dict.map'. The same is true if the region is encompassing 'Dict'.

    Recursively expands outward in both directions, correctly returning longer
    constructions such as 'Graphics.Input.button'
    """
    starting_region = region
    prefix = view.substr(region.a - 1)
    suffix = view.substr(region.b)
    if prefix == '.':
        region = region.cover(view.word(region.a - 2))
    if suffix == '.':
        region = region.cover(view.word(region.b + 1))

    if region == starting_region:
        return region
    else:
        return join_qualified(region, view)

def get_word_under_cursor(view):
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    return view.substr(region).strip()     

def get_type(view, panel):
    """
    Given a view, return the type signature of the word under the cursor,
    if found. If no type is found, return an empty string. Write the info
    to an output panel.
    """
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    scope = view.scope_name(region.b)
    if scope.find('source.elm') != -1 and scope.find('string') == -1 and scope.find('comment') == -1:
        filename = view.file_name()
        word = view.substr(region).strip()
        sublime.set_timeout_async(lambda: search_and_set_status_message(filename, word, panel, 0), 0)

def search_and_set_status_message(filename, query, panel, tries):
    """
    Given a filename and a query, look up in the in-memory dict of values
    pulled from elm oracle to find a match. If a match is found, display
    the type signature in the status bar and set it in the output panel.
    """
    global LOOKUPS
    if len(query) == 0:
        return None
    if filename not in LOOKUPS.keys():
        if tries >= 10:
            return None
        else:
            # if the filename is not found loaded into memory, it's probably being
            # loaded into memory right now. Try 10 more times at 100ms intervals
            # and if it still isn't loaded, there's likely a problem we can't fix
            # here.
            sublime.set_timeout_async(search_and_set_status_message(filename, query, panel, tries + 1), 100)
    else:
        data = LOOKUPS[filename]
        if len(data) > 0:
            matches = [item for item in data if item['name'] == query.split('.')[-1]]
            if len(matches) == 0:
                return None
            else:
                # sort matches by similarity to query
                matches.sort(key=lambda x: SequenceMatcher(None, query, x['fullName']).ratio(), reverse=True)
                item = matches[0]
                type_signature = item['fullName'] + ' : ' + item['signature']
                sublime.status_message(type_signature)
                panel.run_command('erase_view')
                # add full name and type annotation
                panel_output = '`' + type_signature + '`' + '\n\n' + item['comment'][1:]
                # replace backticks with no-width space for syntax highlighting
                panel_output = panel_output.replace('`', '\uFEFF')
                # add no-width space to beginning and end of code blocks for syntax highlighting
                panel_output = re.sub('\n( {4}[\s\S]+?)((?=\n\S)\n|\Z)', '\uFEFF\n\\1\uFEFF\n', panel_output)
                # remove first four spaces on each line from code blocks
                panel_output = re.sub('\n {4}', '\n', panel_output)
                panel.run_command('append', {'characters': panel_output})
        return None    

def get_matching_names(filename, prefix):
    """
    Given a file name and a search prefix, return a list of matching
    completions from elm oracle.
    """
    def skip_chars(full_name):
        # Sublime Text seems to have odd behavior on completions. If the full
        # name is at the same "path level" as the prefix, then the completion
        # will replace the entire entry, otherwise it will only replace after
        # the final period separator
        full_name_path = full_name.split('.')[:-1]
        prefix_path = prefix.split('.')[:-1]
        if full_name_path == prefix_path:
            return full_name
        else:
            # get the characters to remove from the completion to avoid duplication
            # of paths. If it's 0, then stay at 0, otherwise add a period back
            chars_to_skip = len('.'.join(prefix_path))
            if chars_to_skip > 0:
                chars_to_skip += 1
            return full_name[chars_to_skip:]

    global LOOKUPS
    if filename not in LOOKUPS.keys():
        return None
    else:
        data = LOOKUPS[filename]
        completions = {(v['fullName'] + '\t' + v['signature'], skip_chars(v['fullName'])) 
            for v in data 
            if v['fullName'].startswith(prefix) or v['name'].startswith(prefix)}
        return [[v[0], v[1]] for v in completions]

def explore_package(filename, package_name):
    global LOOKUPS
    if filename not in LOOKUPS.keys() or len(package_name) == 0:
        return None
    elif package_name[0].upper() != package_name[0]:
        sublime.status_message('This is not a package!')
        return None
    else:
        def open_link(items, i):
            if i == -1:
                return None
            else:
                open_in_browser(items[i][3])
        data = [[v['fullName'], v['signature'], v['comment'], v['href']] 
            for v in LOOKUPS[filename] 
            if v['fullName'].startswith(package_name)]
        # all items must be the same number of rows
        n = 75
        panel_items = [v[:2] + [v[2][:n]] + [v[2][n:2*n]] + [v[2][2*n:]] for v in data]
        sublime.active_window().show_quick_panel(panel_items, lambda i: open_link(data, i))

def open_in_browser(url):
    webbrowser.open_new_tab(url)        

def load_from_oracle(filename):
    """
    Loads all data about the current file from elm oracle and adds it
    to the LOOKUPS global dictionary.
    """
    global LOOKUPS
    project = ElmProject(filename)
    os.chdir(project.working_dir)

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
        os.environ["PATH"] = os.path.expandvars(path + path_separator + '$PATH')

    p = subprocess.Popen(['elm-oracle', filename, ''], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=shell)

    if path:
        os.environ['PATH'] = old_path

    output, errors = p.communicate()
    output = output.strip()
    if settings.get('debug', False):
        string_settings = sublime.load_settings('Elm User Strings.sublime-settings')
        print(string_settings.get('logging.prefix', '') + '(elm-oracle) ' + str(output), '\nerrors: ' + str(errors.strip()))
        if str(errors.strip()):
            print('Your PATH is: ', os.environ['PATH'])
    try:
        data = json.loads(output.decode('utf-8'))
    except ValueError:
        return None
    LOOKUPS[filename] = data

def view_load(view):
    """
    Selectively calls load_from_oracle based on the current scope.
    """
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    scope = view.scope_name(region.b)
    if scope.find('source.elm') != -1:
        load_from_oracle(view.file_name())


class ElmOracleListener(sublime_plugin.EventListener):
    """
    An event listener to load and search through data from elm oracle.
    """

    def on_selection_modified_async(self, view):
        sel = view.sel()[0]
        region = join_qualified(view.word(sel), view)
        scope = view.scope_name(region.b)
        if scope.find('source.elm') != -1:
            view.run_command('elm_show_type')

    def on_activated_async(self, view):
        view_load(view)

    def on_post_save_async(self, view):
        view_load(view)

    def on_query_completions(self, view, prefix, locations):
        word = get_word_under_cursor(view)
        return get_matching_names(view.file_name(), word)


class ElmShowType(sublime_plugin.TextCommand):
    """
    A text command to lookup the type signature of the function under the
    cursor, and display it in the status bar if found.
    """
    type_panel = None

    def run(self, edit, panel=False):
        if self.type_panel is None:
            self.type_panel = self.view.window().create_output_panel('elm_type')
            if os.name == "nt":
                # using extension hide-tmLanguage because hidden-tmLanguage doesn't work correctly
                self.type_panel.set_syntax_file('Packages/Elm Language Support/Syntaxes/Elm Documentation.hide-tmLanguage')
            else:
                self.type_panel.set_syntax_file('Packages/Elm Language Support/Syntaxes/Elm Documentation.hidden-tmLanguage')
        get_type(self.view, self.type_panel)
        if panel:
            self.view.window().run_command('elm_show_type_panel')


class ElmShowTypePanel(sublime_plugin.WindowCommand):
    """
    Turns on the type output panel
    """
    def run(self):
        self.window.run_command("show_panel", {"panel": "output.elm_type"})


class ElmOracleExplore(sublime_plugin.TextCommand):
    def run(self, edit):
        word = get_word_under_cursor(self.view)
        parts = [part for part in word.split('.') if part[0].upper() == part[0]]
        package_name = '.'.join(parts)
        explore_package(self.view.file_name(), package_name)


class EraseView(sublime_plugin.TextCommand):
    """
    Erases a view
    """
    def run(self, edit):
        self.view.erase(edit, sublime.Region(0, self.view.size()))
