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
def replace_base_class(path):
    def splice_bases(old_base, *extra_bases):
        try:
            new_base = import_module(path)
        except ImportError:
            module_name = path[:path.index('.')]
            log_string('logging.missing_plugin', module_name)
            return None
        else:
            return (new_base,) + extra_bases

    def monkey_patch(target_cls):
        if not hasattr(target_cls, 'is_patched'):
            new_bases = splice_bases(target_cls.__bases__)
            target_cls.is_patched = bool(new_bases)
            if new_bases:
                target_cls.__bases__ = new_bases

    def decorator(target_cls):
        def new(cls, *args, **kwargs):
            monkey_patch(target_cls)
            super_ = super(target_cls, cls).__new__
            # TypeError: object() takes no parameters
            return super_(cls) if super_ is object.__new__ else super_(cls, *args, **kwargs)

        assert '__new__' not in target_cls.__dict__
        # ST2: TypeError: unbound method new()
        target_cls.__new__ = classmethod(new)
        return target_cls

    return decorator
