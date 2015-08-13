import sublime
import sublime_plugin
import os.path as fs

def is_ST2():
    return sublime.version().startswith('2')

def get_string(key, *args):
    strings = sublime.load_settings('Elm User Strings.sublime-settings')
    return strings.get('logging.prefix') + strings.get(key).format(*args)

def log_string(key, *args):
    def log_string_with_retry(retry):
        try:
            # ST2: RuntimeError: Must call on main thread
            settings = sublime.load_settings('Elm Language Support.sublime-settings')
        except RuntimeError:
            if retry:
                sublime.set_timeout(lambda: log_string_with_retry(False), 0)
            else:
                import traceback
                traceback.print_exc()
        else:
            if settings.get('debug'):
                print(get_string(key, *args))

    log_string_with_retry(True)

def import_module(path):
    names = path.split('.')
    index = 1 if is_ST2() else 0
    base = __import__(names[index])
    for name in names[index + 1:]:
        base = getattr(base, name)
    return base

# defer import as long as possible in case plugin not loaded
def monkey_patch(path):
    def splice_bases(old_base, *extra_bases):
        try:
            new_base = import_module(path)
        except ImportError:
            module_name = path[:path.index('.')]
            log_string('logging.missing_plugin', module_name)
            return None
        else:
            return (new_base,) + extra_bases

    def decorator(old_cls):
        def method_new(new_cls, *args, **kwargs):
            if not hasattr(old_cls, 'is_patched'):
                new_bases = splice_bases(old_cls.__bases__)
                old_cls.is_patched = bool(new_bases)
                if new_bases:
                    old_cls.__bases__ = new_bases
            new = super(MonkeyPatch, new_cls).__new__
            # TypeError: object() takes no parameters
            return new(new_cls) if new is object.__new__ else new(new_cls, *args, **kwargs)

        MonkeyPatch = type(old_cls.__name__, (old_cls,), dict(__new__=method_new))
        return MonkeyPatch

    return decorator
