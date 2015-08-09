import sublime
import sublime_plugin
import os.path as fs

def is_ST2():
    return sublime.version().startswith('2')

def get_string(key, *args):
    strings = sublime.load_settings('Elm User Strings.sublime-settings')
    return strings.get('logging.prefix') + strings.get(key).format(*args)

def log_string(key, *args):
    _log_string(True, key, *args)

def _log_string(retry, key, *args):
    try:
        # ST2: RuntimeError: Must call on main thread
        settings = sublime.load_settings('Elm Language Support.sublime-settings')
    except RuntimeError:
        if retry:
            sublime.set_timeout(lambda: _log_string(False, key, *args), 0)
        else:
            import traceback
            traceback.print_exc()
    else:
        if settings.get('debug'):
            print(get_string(key, *args))

def patch_class(cls, name):
    try:
        cls.__bases__ = cls._import_bases()
    except ImportError:
        log_string('logging.missing_plugin', name)
        cls.is_patched = False
    else:
        cls.is_patched = True
    finally:
        return cls.is_patched
