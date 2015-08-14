import collections
import json

try:     # ST3
    from .elm_plugin import *
except:  # ST2
    from elm_plugin import *

class ElmProjectCommand(sublime_plugin.TextCommand):

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def run(self, edit, prop_name=None, choices=None, caption=None):
        self.window = self.view.window()
        if not prop_name:
            self.window.open_file(self.project.json_path, sublime.TRANSIENT)
            return
        self.prop_name = prop_name
        initial_value = getattr(self.project, prop_name)
        if choices:
            self.show_choices(choices, initial_value)
        else:
            self.window.show_input_panel(caption, initial_value, self.on_finished, None, None)

    def show_choices(self, choices, initial_value):
        self.norm_choices = [choice.lower() for choice in choices]
        try:
            # ValueError: $initial_value is not in list
            initial_index = self.norm_choices.index(initial_value.lower())
            # ST2: Boost.Python.ArgumentError: Python argument types
            self.window.show_quick_panel(choices, self.on_choice, selected_index=initial_index)
        except: # simplest control flow
            if not is_ST2():
                log_string('project.logging.invalid_choice', initial_value)
            self.window.show_quick_panel(choices, self.on_choice)

    def on_choice(self, index):
        if index != -1:
            self.on_finished(self.norm_choices[index])

    def on_finished(self, value):
        setattr(self.project, self.prop_name, value)
        keys = self.project._last_updated_key_path
        if keys:
            sublime.status_message(get_string('project.updated', '.'.join(keys), value))

BUILD_KEY = ('sublime-build',)
MAIN_KEY = BUILD_KEY + ('main',)
HTML_KEY = BUILD_KEY + ('html',)
OUTPUT_KEY = BUILD_KEY + ('output',)
OUTPUT_PATH_KEY = OUTPUT_KEY + ('path',)
OUTPUT_COMP_KEY = OUTPUT_KEY + ('components',)
OUTPUT_DIR_KEY = OUTPUT_COMP_KEY + ('dir',)
OUTPUT_NAME_KEY = OUTPUT_COMP_KEY + ('name',)
OUTPUT_EXT_KEY = OUTPUT_COMP_KEY + ('ext',)

class ElmProject(object):

    @classmethod
    def find_json(cls, dir_path):
        if not fs.isdir(fs.abspath(dir_path)):
            return None
        file_path = fs.abspath(fs.join(dir_path, 'elm-package.json'))
        if fs.isfile(file_path):
            return file_path
        parent_path = fs.join(dir_path, fs.pardir)
        if fs.abspath(parent_path) == fs.abspath(dir_path):
            return None
        return cls.find_json(parent_path)

    def __init__(self, file_path):
        self.file_path = file_path
        self.json_path = self.find_json(fs.dirname(file_path or ''))
        self.data_dict = self.load_json()

    def __getitem__(self, keys):
        if not self.exists:
            return None
        item = self.data_dict
        for key in keys:
            item = item.get(key)
            if not item:
                break
        return item

    def __setitem__(self, keys, value):
        self._last_updated_key_path = None
        if not self.exists:
            sublime.error_message(get_string('project.not_found'))
            return
        item = self.data_dict
        for key in keys[0:-1]:
            item = item.setdefault(key, {})
        item[keys[-1]] = value
        self.save_json()
        self._last_updated_key_path = keys

    def __repr__(self):
        members = [(name, getattr(self, name), ' ' * 4)
            for name in dir(self) if name[0] != '_']
        properties = ["{indent}{name}={value},".format(**locals())
            for name, value, indent in members if not callable(value)]
        return "{0}(\n{1}\n)".format(self.__class__.__name__, '\n'.join(properties))

    def load_json(self):
        try:
            with open(self.json_path) as json_file:
                if is_ST2(): # AttributeError: 'module' object has no attribute 'OrderedDict'
                    return json.load(json_file)
                else:
                    return json.load(json_file, object_pairs_hook=collections.OrderedDict)
        except TypeError: # self.json_path == None
            pass
        except ValueError:
            log_string('project.logging.invalid_json', self.json_path)
        return None

    def save_json(self):
        with open(self.json_path, 'w') as json_file:
            json.dump(self.data_dict, json_file,
                indent=4,
                separators=(',', ': '),
                sort_keys=is_ST2())

    @property
    def exists(self):
        return bool(self.data_dict)

    @property
    def working_dir(self):
        return fs.dirname(self.json_path or '')

    @property
    def main_path(self):
        return self[MAIN_KEY] or fs.relpath(self.file_path, self.working_dir)

    @main_path.setter
    def main_path(self, value):
        self[MAIN_KEY] = value

    @property
    def html_path(self):
        return self[HTML_KEY] or self.output_path

    @html_path.setter
    def html_path(self, value):
        self[HTML_KEY] = value

    @property
    def output_path(self):
        output_path = fs.join(self.output_dir, self.output_name + '.' + self.output_ext)
        return self[OUTPUT_PATH_KEY] or fs.normpath(output_path)

    @output_path.setter
    def output_path(self, value):
        self[OUTPUT_PATH_KEY] = value

    @property
    def output_dir(self):
        return self[OUTPUT_DIR_KEY] or 'build'

    @output_dir.setter
    def output_dir(self, value):
        self[OUTPUT_DIR_KEY] = value

    @property
    def output_name(self):
        return self[OUTPUT_NAME_KEY] or fs.splitext(fs.basename(self.main_path))[0]

    @output_name.setter
    def output_name(self, value):
        self[OUTPUT_NAME_KEY] = value

    @property
    def output_ext(self):
        return self[OUTPUT_EXT_KEY] or 'html'

    @output_ext.setter
    def output_ext(self, value):
        self[OUTPUT_EXT_KEY] = value
