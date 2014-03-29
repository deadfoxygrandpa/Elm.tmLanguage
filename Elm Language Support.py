import os
import subprocess
import json
import threading
import time

import sublime, sublime_plugin

SETTINGS = sublime.load_settings('Elm Language Support.sublime-settings')

ELM_DOCS_PATH = SETTINGS.get('elm_docs_path') or 'docs.json'


class Module(object):
    """
    Container that extracts info from Elm's docs.json modules
    """
    def __init__(self, data):
        """
        data should be a single module from docs.json
        """
        self.name = data['name']
        self.document = data['document']
        self.values = [name(v['raw']) + ' : ' + signature(v['raw'])
                       for v in data['values']]
        self.value_names = [name(v) for v in self.values]
        self.datatypes = [v['name'] for v in data['datatypes']]
        self.constructors = [[v['name'] for v in x['constructors']] 
                             for x in data['datatypes']]
        self.aliases = [v['name'] for v in data['aliases']]
        self.raw_aliases = [v['raw'] for v in data['aliases']]
        self.raw_datatypes = [v['raw'] for v in data['datatypes']]
        self.types = dict(zip(self.value_names, 
                              [signature(v) for v in self.values]))


def load_docs(path):
    """
    Load docs.json into memory
    """
    with open(path) as f:
        return json.load(f)

def get_prelude_modules(modules):
    """
    Scan modules for a Basics module, then read it to see which modules
    are imported by default into Prelude
    """
    for m in modules:
        if m.name == 'Basics':
            prelude = m.document.split('imported by default: ')[1]
            prelude = prelude.split('\n\n')[0].replace('\n', ' ')[:-1]
            prelude = prelude.split(', ')
            return prelude + ['Basics', 'Prelude']

def name(t):
    """
    Given an Elm type signatue of form:
        name : <types>
    return name
    Also gets the name of data constructors or type aliases
    """
    if t.startswith('type '):
        return t[5:].split(' = ')[0].strip()
    elif t.startswith('data '):
        return t[5:].split(' = ')[0].strip()
    return t.split(' : ')[0].strip()

def signature(t):
    """
     Given an Elm type signatue of form:
        name : a -> b
    or similar, return the 'a -> b' part
    Also gets the constructors of a data declaration or the type of an alias
    Only works on single-line declarations
    """
    if t.startswith('type '):
        return t[5:].split(' = ')[1].strip()  
    elif t.startswith('data '):
        return t[5:].split(' = ')[1].strip()  
    return t.split(' : ')[1].strip()

def search_modules(value, modules):
    """
    Search for a function name, value, data constructor, or type constructor
    inside a list of modules. Return their entire type signatures. If more than
    one match is found, all matches are returned, separated by semicolons
    """
    names = []
    for module in modules:
        if value in module.value_names:
            names.append(module.name + '.' + value + ' : ' + module.types[value])
        elif value in module.datatypes:
            datatype = [datatype for datatype in module.raw_datatypes \
                        if name(datatype).split(' ')[0].strip() == value][0]
            names.append('data ' + module.name + '.' + name(datatype) + ' = ' + signature(datatype))
        elif value in module.aliases:
            alias = [alias for alias in module.raw_aliases if name(alias) == value][0]
            names.append('type ' + module.name + '.' + value + ' = ' + signature(alias))
        elif value == module.name:
            names.append('Module ' + module.name)
    return '; '.join(names)

def modules_in_scope(view):
    """
    Given a view, search for all import statements and return a dict mapping
    all modules in scope to their status.
    Possible statuses:
        open: from an 'import open <module>' statement
        qualified: from an 'import <module>' statement
        <alias>: from an 'import <module> as <alias>' statement
        [names]: from an 'import <module> ([names])' statement
    """
    import_pattern = 'import\W+(open)?\W*([a-zA-Z0-9._\']+)(?:\\W+as\\W+([a-zA-Z0-9._\']+))?(?:\W+\((.*)\))?'
    regions = view.find_all(import_pattern)
    imports = [view.substr(region)[7:].strip() for region in regions]
    modules = {}
    for imp in imports:
        if imp.startswith('open'):
            ## This was removed in Elm 0.12, but keeping it in for now
            modules[imp[5:]] = 'open'
        elif len(imp.split(' as ')) == 2:
            x = imp.split(' as ')
            modules[x[0].strip()] = x[1].strip()
        elif len(imp.split('(')) == 2:
            x = imp.replace(')', '').split('(')
            values = [v.strip() for v in x[1].split(',')]
            if values[0] == '..':
                modules[x[0].strip()] = 'open'
            else:
                modules[x[0].strip()] = values
        else:
            modules[imp] = 'qualified'
    for module in PRELUDE:
        modules[module] = 'open'
    return modules

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
        in_scope = modules_in_scope(view)

        open_modules = [m for m in MODULES if m.name in [v for v in in_scope.keys() if in_scope[v] == 'open']]
        qualified_modules = [m for m in MODULES if m.name in [v for v in in_scope.keys() if in_scope[v] == 'qualified']]
        aliased_modules = dict((m, in_scope[m.name]) for m in MODULES if m.name in 
            [v for v in in_scope.keys() if in_scope[v] not in ['open', 'qualified'] \
            and not isinstance(in_scope[v], list)])
        
        open_values = dict((m, in_scope[m.name]) for m in MODULES if m.name in 
            [v for v in in_scope.keys() if isinstance(in_scope[v], list)])

        word = view.substr(region)
        module = '.'.join(word.split('.')[:-1])
        value = None
        if module:
            value = word.split('.')[-1]
        msg = search_modules(word, open_modules) or \
            search_modules(value, [m for m in qualified_modules if m.name == module]) or \
            search_modules(value, [m for m in aliased_modules.keys() if module == aliased_modules[m]]) or \
            search_modules(word, [m for m in open_values.keys() if word in open_values[m]])

        return msg or ''

# Load the modules from the Elm Standard Library docs
MODULES = [Module(m) for m in load_docs(ELM_DOCS_PATH)]
PRELUDE = get_prelude_modules(MODULES)


class ElmLanguageSupport(sublime_plugin.EventListener):
    # TODO: implement completions based on current context
    # def on_query_completions(self, view, prefix, locations):
    #     return []

    def on_selection_modified(self, view):
        if SETTINGS.get('enabled', True):
            msg = get_type(view) or ''
            sublime.status_message(msg)

class ElmShowType(sublime_plugin.TextCommand):
    def run(self, edit):
        print get_type(self.view)
        msg = get_type(self.view) or ''
        sublime.status_message(msg)        

class ElmSetDocsPath(sublime_plugin.ApplicationCommand):
    def run(self):
        p = subprocess.Popen('elm-paths docs', stdout=subprocess.PIPE, shell=True)
        version = p.communicate()[0].strip() or ''
        if version.endswith('docs.json'):
            SETTINGS.set('elm_docs_path', version)
        print version or 'elm-paths not installed...'

class ElmEnable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "true")
        sublime.save_settings('Elm Language Support.sublime-settings')

class ElmDisable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "false")
        sublime.save_settings('Elm Language Support.sublime-settings')
