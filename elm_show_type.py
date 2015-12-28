from __future__ import print_function

import os.path
import subprocess
import json

import sublime, sublime_plugin

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

def get_type(view):
    """
    Given a view, return the type signature of the word under the cursor,
    if found. If no type is found, return an empty string.
    """
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    scope = view.scope_name(region.b)
    if scope.find('source.elm') != -1 and scope.find('string') == -1 and scope.find('comment') == -1:
        filename = view.file_name()
        word = view.substr(region).strip()
        sublime.set_timeout_async(lambda: search_and_set_status_message(filename, word, 0), 0)
        return ''

def search_and_set_status_message(filename, query, tries):
    """
    Given a filename and a query, look up in the in-memory dict of values
    pulled from elm oracle to find a match. If a match is found, display
    the type signature in the status bar.
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
            sublime.set_timeout_async(lambda: query(filename, word, tries + 1), 100)
    else:
        data = LOOKUPS[filename]
        if len(data) > 0:
            for item in data:
                if item['name'] == query.split('.')[-1]:
                    type_signature = item['fullName'] + ' : ' + item['signature']
                    sublime.status_message(type_signature)
                    break
        return None     

def load_from_oracle(filename):
    """
    Loads all data about the current file from elm oracle and adds it
    to the LOOKUPS global dictionary.
    """
    global LOOKUPS
    p = subprocess.Popen('elm-oracle ' + filename + ' ""', stdout=subprocess.PIPE, cwd=os.path.dirname(filename), shell=True)
    output = p.communicate()[0].strip()
    try:
        data = json.loads(output.decode('utf-8'))
    except ValueError:
        return None
    LOOKUPS[filename] = data

def view_load(view):
    """
    Selectively calls load_from_oracle based on the current scope.
    """
    global LOOKUPS
    sel = view.sel()[0]
    region = join_qualified(view.word(sel), view)
    scope = view.scope_name(region.b)
    if scope.find('source.elm') != -1:
        load_from_oracle(view.file_name())


class ElmOracleListener(sublime_plugin.EventListener):
    """
    An event listener to load and search through data from elm oracle.
    """
    # TODO: implement completions based on current context
    # def on_query_completions(self, view, prefix, locations):
    #     return []

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


class ElmShowType(sublime_plugin.TextCommand):
    """
    A text command to lookup the type signature of the function under the
    cursor, and display it in the status bar if found.
    """
    def run(self, edit):
        msg = get_type(self.view) or ''
        sublime.status_message(msg)
