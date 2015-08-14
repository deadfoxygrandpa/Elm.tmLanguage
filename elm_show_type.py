from __future__ import print_function
try:
    import Queue as queue
except ImportError as py3err:
    import queue

import os
import os.path as fs
import subprocess
import json
import threading
import time
from collections import defaultdict

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

class Worker(threading.Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try: func(*args, **kargs)
            except Exception as e: print(e)
            self.tasks.task_done()

class ThreadPool(object):
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.tasks = queue.Queue(num_threads)
        for _ in range(num_threads): Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()


def load_docs(path):
    """
    Load docs.json into memory
    """
    with open(fs.join(fs.dirname(__file__), path)) as f:
        return json.load(f)

def threadload(f, directory, queue):
    p = subprocess.Popen('elm-doc ' + os.path.relpath(f, directory), stdout=subprocess.PIPE, cwd=directory, shell=True)
    output = p.communicate()[0].strip() or 'Could not document: ' + f
    # print output
    if output.startswith('Could not document: '):
        p = subprocess.Popen('elm -mo --print-types ' + os.path.relpath(f, directory), stdout=subprocess.PIPE, cwd=directory, shell=True)
        output = p.communicate()[0].strip() or 'Could not compile: ' + f
        types = parse_print_types(output)
        raw_values = []
        with open(f) as module:
            first_line = module.readline()
            if first_line.startswith('module ') and first_line.endswith(' where'):
                module_name = first_line.split()[1]
                module_name = module_name.split('(')[0]
            else:
                module_name = os.path.split(f)[1][:-4]
        for t in types:
            try:
                if not name(t).startswith('Could not compile: '):
                    if name(t).startswith(module_name):
                        raw_values.append(t[len(module_name)+1:])
            except IndexError:
                pass
        data = {'name': module_name, 'document': '', 'aliases': [], 'datatypes': [], 'values': [{'raw': t} for t in raw_values]}
        queue.put(data)

def parse_print_types(s):
    lines = s.split('\n')
    lines = [line.strip() for line in lines]
    x = []
    for line in lines:
        if line.startswith('->'):
            x[-1] += ' ' + line
        else:
            x.append(line)
    return x

def load_dependency_docs(name):
    try:
        directory = os.path.split(name)[0]
        try:
            data = []
            source_files = []
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if filename.lower().endswith('.elm'):
                        f = os.path.join(root, filename)
                        if not '_internals' in f:
                            source_files.append((f, filename))
            queue = queue.Queue()
            global POOL
            threads = [POOL.add_task(threadload, f[0], directory, queue) for f in source_files]
            POOL.wait_completion()
            modules = []
            while True:
                if not queue.empty():
                    modules.append(queue.get())
                else:
                    break
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if filename.lower().endswith('.json') and filename in [f[1][:-4] + '.json' for f in source_files]:
                        x = os.path.join(root, filename.lower())
                        if '_internals' not in x:
                            with open(x) as f:
                                data.append(json.load(f))
            return modules + data
        except KeyError:
            return []
    except:
        return []


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
    return t.split(':')[1].strip()

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
            alias = [a for a in module.raw_aliases if name(a).startswith(value)][0]
            names.append('type ' + module.name + '.' + value + ' = ' + signature(alias))
        elif value == module.name:
            names.append('Module ' + module.name)
    return '; '.join(names)

def modules_in_scope(view):
    """
    Given a view, search for all import statements and return a dict mapping
    all modules in scope to their status.
    Possible statuses:
        open: True/False, from an 'import <module> (..)' statement
        qualified: True/False, from an 'import <module>' statement
        alias: A list of strings, from an 'import <module> as <alias>' statement
        names: A list of strings, from an 'import <module> ([names])' statement
    """
    import_pattern = 'import\W+(open)?\W*([a-zA-Z0-9._\']+)(?:\\W+as\\W+([a-zA-Z0-9._\']+))?(?:\W+\((.*)\))?'
    regions = view.find_all(import_pattern)
    imports = [view.substr(region)[7:].strip() for region in regions]
    modules = defaultdict(lambda: {'open': False, 'qualified': False, 'names': [], 'alias': []})
    for imp in imports:
        status = {'open': False, 'qualified': False, 'names': [], 'alias': []}
        name = ""
        if imp.startswith('open'):
            ## This was removed in Elm 0.12, but keeping it in for now
            name = modules[imp[5:]]
            status['open'] = True
        elif len(imp.split(' as ')) == 2:
            x = imp.split(' as ')
            name = x[0].strip()
            status['alias'].append(x[1].strip())
        elif len(imp.split('(')) == 2:
            x = imp.replace(')', '').split('(')
            values = [v.strip() for v in x[1].split(',')]
            name = x[0].strip()
            if values[0] == '..':
                status['open'] = True
            else:
                status['names'] += values
        else:
            name = imp
            status['qualified'] = True
        modules = update_module_scope(status, modules, name)
    for module in PRELUDE:
        status = {'open': True, 'qualified': False, 'names': [], 'alias': []}
        modules = update_module_scope(status, modules, module)
    modules[current_module_name(view)] = {'open': True, 'qualified': False, 'names': [], 'alias': []}
    return modules

def current_module_name(view):
    module_pattern = 'module\W+.*\W+where\W*'
    regions = view.find_all(module_pattern)
    if len(regions) > 0:
        name = view.substr(regions[0]).split()[1]
    else:
        name = ''
    file_name = os.path.split(view.file_name())[1]
    if file_name.lower().endswith('.elm'):
        file_name = file_name[:-4]
    return name or file_name

def update_module_scope(status, modules, name):
    """
    Merge two module statuses together, used only by modules_in_scope
    """
    if modules.get(name) is not None:
        status['open'] = status['open'] or modules[name]['open']
        status['qualified'] = status['qualified'] or modules[name]['qualified']
        status['names'] += modules[name]['names']
        status['alias'] += modules[name]['alias']
    modules[name] = status
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
        open_modules = [m for m in MODULES if m.name in [v for v in in_scope.keys() if in_scope[v]['open']]]
        qualified_modules = [m for m in MODULES if m.name in [v for v in in_scope.keys() if in_scope[v]['qualified']]]
        aliased_modules = dict((m, in_scope[m.name]['alias']) for m in MODULES)
        open_values = dict((m, in_scope[m.name]['names']) for m in MODULES)

        word = view.substr(region)
        module = '.'.join(word.split('.')[:-1])
        value = None
        if module:
            value = word.split('.')[-1]
        msg = search_modules(word, open_modules) or \
            search_modules(value, [m for m in qualified_modules if m.name == module]) or \
            search_modules(value, [m for m in aliased_modules.keys() if module in aliased_modules[m]]) or \
            search_modules(word, [m for m in open_values.keys() if word in open_values[m]])

        return msg or ''

# Load the modules from the Elm Standard Library docs
STD_LIBRARY = [Module(m) for m in load_docs(ELM_DOCS_PATH)]
MODULES = STD_LIBRARY
PRELUDE = get_prelude_modules(MODULES)
POOL = ThreadPool(2)

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
            sublime.status_message(msg)

    def on_activated(self, view):
        sel = view.sel()[0]
        region = join_qualified(view.word(sel), view)
        scope = view.scope_name(region.b)
        if SETTINGS.get('enabled', True) and scope.find('source.elm') != -1:
            threading.Thread(target=self.load_dependencies, args=[view.file_name()]).start()

    def on_post_save(self, view):
        sel = view.sel()[0]
        region = join_qualified(view.word(sel), view)
        scope = view.scope_name(region.b)
        if SETTINGS.get('enabled', True) and scope.find('source.elm') != -1:
            threading.Thread(target=self.load_dependencies, args=[view.file_name()]).start()

    def load_dependencies(self, filename):
        global MODULES
        global STD_LIBRARY
        deps = load_dependency_docs(filename)
        MODULES = STD_LIBRARY + [Module(m) for m in deps]

class ElmShowType(sublime_plugin.TextCommand):
    def run(self, edit):
        print(get_type(self.view))
        msg = get_type(self.view) or ''
        sublime.status_message(msg)

class ElmSetDocsPath(sublime_plugin.ApplicationCommand):
    def run(self):
        p = subprocess.Popen('elm-paths docs', stdout=subprocess.PIPE, shell=True)
        version = p.communicate()[0].strip() or ''
        if version.endswith('docs.json'):
            SETTINGS.set('elm_docs_path', version)
        print(version or 'elm-paths not installed...')

class ElmEnable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "true")
        sublime.save_settings('Elm Language Support.sublime-settings')

class ElmDisable(sublime_plugin.ApplicationCommand):
    def run(self):
        SETTINGS.set("enabled", "false")
        sublime.save_settings('Elm Language Support.sublime-settings')

class ElmCase(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sel = view.sel()
        word = view.word(sel[0])
        sel.add(self.get_lines(sel[0]))

    def find_indent(self, x):
        view = self.view
        line = view.substr(view.line(x))
        indent = len(line) - len(line.lstrip(' '))
        return indent

    def next_line(self, x):
        view = self.view
        line = view.line(x)
        return view.line(line.b + 1)

    def previous_line(self, x):
        view = self.view
        line = view.line(x)
        return view.line(line.begin() - 1)

class ElmCase(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sel = view.sel()
        word = view.word(sel[0])
        sel.add(self.get_lines(sel[0]))

    def find_indent(self, x):
        view = self.view
        line = view.substr(view.line(x))
        indent = len(line) - len(line.lstrip(' '))
        return indent

    def next_line(self, x):
        view = self.view
        line = view.line(x)
        return view.line(line.b + 1)

    def previous_line(self, x):
        view = self.view
        line = view.line(x)
        return view.line(line.begin() - 1)

    def get_lines(self, x):
        view = self.view
        line = view.line(x)

        lines = [line]

        # add lines in current level above the current line
        starting_indent = self.find_indent(line)
        indent = starting_indent
        y = x
        while indent == starting_indent:
            # if self.find_indent(self.previous_line(y)) < starting_indent:
            #     break
            lines.append(self.previous_line(y))
            indent = self.find_indent(self.previous_line(y))
            y = self.previous_line(y)

        # add lines in current level below the current line
        starting_indent = self.find_indent(self.next_line(x))
        indent = starting_indent
        y = x
        while indent == starting_indent:
            if self.find_indent(self.next_line(y)) < starting_indent:
                break
            lines.append(self.next_line(y))
            indent = self.find_indent(self.next_line(y))
            y = self.next_line(y)

        begin = min([v.begin() for v in lines])
        end = max([v.end() for v in lines])

        case = view.find(' case ', begin)
        if case is None or case.begin() > end:
            return x
        else:
            return sublime.Region(case.begin() + 1, end)

def select_block(view, keyword):
    sel = view.sel()[0]
    line = view.line(sel)
    key_pattern = ' ' + keyword + ' '
    key_pt = view.find(key_pattern, line.begin())

    if key_pt is None:
        return None

    if key_pt < line.end():
        starting_indent = find_indent(next_line(sel))
    else:
        starting_indent = find_indent(sel)

    lines = [line]



def find_indent(view):
    line = view.substr(view.line(x))
    indent = len(line) - len(line.lstrip(' '))
    return indent

def next_line(view):
    line = view.line(x)
    return view.line(line.end() + 1)

def previous_line(view):
    line = view.line(x)
    return view.line(line.begin() - 1)
