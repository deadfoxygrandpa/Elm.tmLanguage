import json
import re

from importlib import import_module
try:
    default_exec = import_module('Highlight Build Errors').HighlightBuildErrors
except:
    import Default.exec as default_exec

class ElmMakeCommand(default_exec.ExecCommand):
    '''Inspired by:
    http://www.sublimetext.com/forum/viewtopic.php?t=12028
    https://github.com/search?q=sublime+filename%3Aexec.py
    https://github.com/search?q=finish+ExecCommand+NOT+ProcessListener+extension%3Apy
    https://github.com/bblanchon/SublimeText-HighlightBuildErrors/blob/master/HighlightBuildErrors.py
    '''

    def run(self, error_format, **kwargs):
        self.error_format = error_format
        super(ElmMakeCommand, self).run(**kwargs)
        self.debug_text = 'To highlight build errors : '
        try:
            if default_exec.g_show_errors:
                self.debug_text = ''
            else:
                self.debug_text += 'Open Command Pallete : Show Build Errors'
        except:
            self.debug_text += 'Install with Package Control : Highlight Build Errors'

    def on_data(self, proc, json_data):
        result_str = json_data.decode(self.encoding)
        json_str, success_str = result_str.split('\n', 1)
        decode_error = lambda dict: self.format_error(**dict) if 'type' in dict else dict
        error_list = json.loads(json_str, object_hook=decode_error)
        error_list.append(success_str)
        error_str = '\n'.join(error_list)
        error_data = error_str.encode(self.encoding)
        super(ElmMakeCommand, self).on_data(proc, error_data)

    def format_error(self, type, file, region, overview, details, **kwargs):
        line = region['start']['line']
        column = region['start']['column']
        message = overview
        if details:
            message += '\n' + re.sub(r'(\n)+', r'\1', details)
        return self.error_format.format(**locals())
