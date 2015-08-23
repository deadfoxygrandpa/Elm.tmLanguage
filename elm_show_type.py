from __future__ import print_function

import os.path
import subprocess
import json

import sublime, sublime_plugin

SETTINGS = sublime.load_settings('Elm Language Support.sublime-settings')

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

def get_type(view):
    """
    Given a view, return the type signature of the word under the cursor,
    if found. If no type is found, returnan empty string
    """
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    scope = view.scope_name(region.b)
    if scope.find('source.elm') != -1 and scope.find('string') == -1 and scope.find('comment') == -1:
        filename = view.file_name()
        word = view.substr(region)
        sublime.set_timeout_async(lambda: query_oracle(filename, word), 0)
        return ''

def query_oracle(filename, query):
    if len(query) == 0:
        return None
    p = subprocess.Popen('elm-oracle ' + filename + ' ' + query, stdout=subprocess.PIPE, cwd=os.path.dirname(filename), shell=True)
    output = p.communicate()[0].strip()
    data = json.loads(output.decode('utf-8'))
    if len(data) > 0:
        data = data[0]
        if data['name'] != query.split('.')[-1]:
            return None
        type_signature = data['fullName'] + ' : ' + data['signature']
        sublime.status_message(type_signature)

class ElmLanguageSupport(sublime_plugin.EventListener):
    # TODO: implement completions based on current context
    # def on_query_completions(self, view, prefix, locations):
    #     return []

    def on_selection_modified(self, view):
        sel = view.sel()[0]
        region = join_qualified(view.word(sel), view)
        scope = view.scope_name(region.b)
        if SETTINGS.get('enabled', True) and scope.find('source.elm') != -1:
            msg = get_type(view) or ''
            # sublime.status_message(msg)

class ElmShowType(sublime_plugin.TextCommand):
    def run(self, edit):
        print(get_type(self.view))
        msg = get_type(self.view) or ''
        sublime.status_message(msg)

class ElmEnable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "true")
        sublime.save_settings('Elm Language Support.sublime-settings')

class ElmDisable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "false")
        sublime.save_settings('Elm Language Support.sublime-settings')
