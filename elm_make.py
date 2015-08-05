import sublime
import json
import os.path as fs
import re
import string

if int(sublime.version()) < 3000:
    from elm_project import ElmProject
    default_exec = __import__('exec')
else:
    from .elm_project import ElmProject
    from importlib import import_module
    default_exec = import_module('Default.exec')

strings = sublime.load_settings('Elm User Strings.sublime-settings')

class ElmMakeCommand(default_exec.ExecCommand):
    '''Inspired by:
    http://www.sublimetext.com/forum/viewtopic.php?t=12028
    https://github.com/search?q=sublime+filename%3Aexec.py
    https://github.com/search?q=finish+ExecCommand+NOT+ProcessListener+extension%3Apy
    https://github.com/bblanchon/SublimeText-HighlightBuildErrors/blob/master/HighlightBuildErrors.py
    '''

    @staticmethod
    def import_dependencies():
        return __import__('Highlight Build Errors').HighlightBuildErrors.ExecCommand,

    def __new__(cls, window):
        try:
            cls.__bases__ = cls.import_dependencies()
            cls.is_patched = True
        except:
            cls.is_patched = False
        finally:
            return super(ElmMakeCommand, cls).__new__(cls)

    def run(self, cmd, working_dir, error_format, **kwargs):
        self.error_format = string.Template(error_format)
        project = ElmProject(cmd[1])
        cmd[1] = fs.expanduser(project.main_path)
        cmd[2] = cmd[2].format(fs.expanduser(project.output_path))
        project_dir = project.working_dir or working_dir
        super(ElmMakeCommand, self).run(cmd, working_dir=project_dir, **kwargs)
        if self.is_patched:
            self.debug_text = ''
        else:
            self.debug_text = strings.get('make_highlighting_disabled')

    def on_data(self, proc, json_data):
        try:
            error_list = self.decode_json(json_data)
        except:
            error_data = json_data
        else:
            error_data = '\n'.join(error_list).encode(self.encoding)
        finally:
            super(ElmMakeCommand, self).on_data(proc, error_data)

    def decode_json(self, json_data): # throws
        result_str = json_data.decode(self.encoding)
        json_str, success_str = result_str.split('\n', 1)
        decode_error = lambda dict: self.format_error(**dict) if 'type' in dict else dict
        error_list = json.loads(json_str, object_hook=decode_error)
        error_list.append(success_str)
        return error_list

    def format_error(shelf, type, file, region, overview, details, **kwargs):
        line = region['start']['line']
        column = region['start']['column']
        message = overview
        if details:
            message += '\n' + re.sub(r'(\n)+', r'\1', details)
        # TypeError: substitute() got multiple values for argument 'self'
        # https://bugs.python.org/issue23671
        return shelf.error_format.substitute(**locals())
