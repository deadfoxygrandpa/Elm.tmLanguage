import sublime
import sublime_plugin
import json
import os.path as fs

strings = sublime.load_settings('Elm User Strings.sublime-settings')

class ElmProjectCommand(sublime_plugin.TextCommand):

    def run(self, edit, prop_name=None, choices=None, caption=None):
        window = self.view.window()
        if not prop_name:
            return window.open_file(self.project.json_path, sublime.TRANSIENT)
        self.prop_name = prop_name
        initial_value = getattr(self.project, prop_name)
        if not choices:
            return window.show_input_panel(caption, initial_value, self.on_finished, None, None)
        self.choices = choices
        if int(sublime.version()) < 3000:
            return window.show_quick_panel(choices, self.on_option)
        try:
            initial_index = [choice.lower() for choice in choices].index(initial_value.lower())
        except:
            initial_index = -1
        window.show_quick_panel(choices, self.on_option, selected_index=initial_index)

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def on_finished(self, value):
        setattr(self.project, self.prop_name, value)
        sublime.status_message(strings.get('project_updated').format(self.prop_name, value))

    def on_option(self, index):
        if index != -1:
            self.on_finished(self.choices[index].lower())

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
        try:
            with open(self.json_path) as json_file:
                self.data_dict = json.load(json_file)
        except:
            pass

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
        if not self.exists:
            return sublime.error_message(strings.get('project_not_found'))
        item = self.data_dict
        for key in keys[0:-1]:
            item = item.setdefault(key, {})
        item[keys[-1]] = value
        with open(self.json_path, 'w') as json_file:
            json.dump(self.data_dict, json_file, indent=4, separators=(',', ': '), sort_keys=True)

    @property
    def exists(self):
        return hasattr(self, 'data_dict')

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
        formatted_path = fs.join(self.output_dir, self.output_name + '.' + self.output_ext)
        return self[OUTPUT_PATH_KEY] or fs.normpath(formatted_path)

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
