import json
import re
import string

try:     # ST3
    from .elm_plugin import *
    from .elm_project import ElmProject
    from importlib import import_module
    default_exec = import_module('Default.exec')
except:  # ST2
    from elm_plugin import *
    from elm_project import ElmProject
    default_exec = __import__('exec')

class ElmMakeCommand(default_exec.ExecCommand):
    '''Inspired by:
    http://www.sublimetext.com/forum/viewtopic.php?t=12028
    https://github.com/search?q=sublime+filename%3Aexec.py
    https://github.com/search?q=finish+ExecCommand+NOT+ProcessListener+extension%3Apy
    https://github.com/bblanchon/SublimeText-HighlightBuildErrors/blob/master/HighlightBuildErrors.py
    '''

    @staticmethod
    def __import_dependencies():
        return __import__('Highlight Build Errors').HighlightBuildErrors.ExecCommand,

    def __new__(cls, window):
        try:
            cls.__bases__ = cls.__import_dependencies()
        except ImportError:
            log_string('logging.missing_plugin', 'Highlight Build Errors')
            cls.is_patched = False
        else:
            cls.is_patched = True
        finally:
            return super(ElmMakeCommand, cls).__new__(cls)

    def run(self, info_format, error_format, syntax, color_scheme, **kwargs):
        self.buffer = b''
        self.info_format = string.Template(info_format)
        self.error_format = string.Template(error_format)
        self.do_run(**kwargs)
        self.style_output(syntax, color_scheme)

    def do_run(self, cmd, working_dir, **kwargs):
        project = ElmProject(cmd[1])
        log_string('project.logging.settings', repr(project))
        cmd[1] = fs.expanduser(project.main_path)
        cmd[2] = cmd[2].format(fs.expanduser(project.output_path))
        project_dir = project.working_dir or working_dir
        # ST2: TypeError: __init__() got an unexpected keyword argument 'syntax'
        super(ElmMakeCommand, self).run(cmd, working_dir=project_dir, **kwargs)

    def style_output(self, syntax, color_scheme):
        self.output_view.set_syntax_file(syntax)
        self.output_view.settings().set('color_scheme', color_scheme)
        if self.is_patched:
            self.debug_text = ''
        else:
            self.debug_text = get_string('make.missing_plugin')

    def on_data(self, proc, data):
        self.buffer += data

    def on_finished(self, proc):
        result_strs = self.buffer.decode(self.encoding).split('\n')
        flat_map = lambda f ,xss: sum(map(f, xss), [])
        output_strs = flat_map(self.format_result, result_strs) + ['']
        output_data = '\n'.join(output_strs).encode(self.encoding)
        super(ElmMakeCommand, self).on_data(proc, output_data)
        super(ElmMakeCommand, self).on_finished(proc)

    def format_result(self, result_str):
        decode_error = lambda dict: self.format_error(**dict) if 'type' in dict else dict
        try:
            return json.loads(result_str, object_hook=decode_error)
        except ValueError:
            log_string('make.logging.invalid_json', result_str)
            info_str = result_str.strip()
            return [self.info_format.substitute(info=info_str)] if info_str else []

    def format_error(shelf, type, file, region, overview, details, **kwargs):
        line = region['start']['line']
        column = region['start']['column']
        message = overview
        if details:
            message += '\n' + re.sub(r'(\n)+', r'\1', details)
        # TypeError: substitute() got multiple values for argument 'self'
        # https://bugs.python.org/issue23671
        return shelf.error_format.substitute(**locals())
