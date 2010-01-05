# TODO: Rewrite this.

from gpyconf import Configuration as _Configuration

from .backend import CreamXMLBackend
from .frontend import CreamFrontend
from cream.util import flatten

class ProfileNotEditable(Exception):
    pass

class ConfigurationProfile(object):
    """ A configuration profile. Holds name and assigned values. """
    is_editable = True

    def __init__(self, name, values, editable=True):
        self.name = name
        self.default_values = values
        self.is_editable = editable
        self._values = values

    @classmethod
    def fromdict(cls, dct, default_profile):
        values = default_profile.values.copy()
        values.update(dct.get('values', ()))
        return cls(dct.pop('name'), values, dct.pop('editable', True))

    @property
    def values(self):
        return self._values

    # TODO: Very repetitive
    @values.setter
    def values(self, value):
        if not self.is_editable:
            raise ProfileNotEditable(self)
        else:
            self._values = value

    def update(self, iterable):
        if not self.is_editable:
            raise ProfileNotEditable(self)
        self.values.update(iterable)

    def set(self, name, value):
        if not self.is_editable:
            raise ProfileNotEditable(self)
        self.values[name] = value

    def __repr__(self):
        return "<Profile '%s'%s>" % (self.name,
            not self.is_editable and ' (not editable)' or '')

class DefaultProfile(ConfigurationProfile):
    """ Default configuration profile (using in-code defined values) """
    def __init__(self, values):
        ConfigurationProfile.__init__(self, 'Default Profile',
                                      values, editable=False)


class ProfileExistsError(Exception):
    def __init__(self, name):
        Exception.__init__(self, "A profile named '%s' already exists" % name)

class ProfileList(list):
    """ List of profiles """
    default = None
    active = None
    active_index = 0

    def __init__(self, default_profile):
        list.__init__(self)
        list.append(self, default_profile)
        self.default = default_profile

    def insert(self, index, profile, overwrite=False, set_active=False):
        assert index

        if not isinstance(profile, ConfigurationProfile):
            profile = ConfigurationProfile.fromdict(profile, self.default)

        old_profile = self.by_name(profile.name)
        if old_profile is not None:
            if not overwrite:
                raise ProfileExistsError(profile)
            else:
                old_profile.values = profile.values
        else:
            list.insert(self, index, profile)

        if set_active:
            self.active_index = index

    def append(self, *args, **kwargs):
        self.insert(len(self), *args, **kwargs)
    add = append

    def by_name(self, name):
        """
        Returns the `Profile` instance holding `name` as `name` attribute
        (or `None` if no such profile exists)
        """
        for profile in self:
            if profile.name == name:
                return profile

    def _use(self, profile):
        if isinstance(profile, int):
            self.active = self[profile]
            self.active_index = profile
        else:
            self.active = profile
            self.active_index = self.index(profile)


class Configuration(_Configuration):
    """
    Base class for all cream configurations.
    """
    frontend = CreamFrontend
    backend = CreamXMLBackend
    profiles = ()
    _ingore_frontend = False

    def __init__(self, **kwargs):
        predefined_profiles = self.profiles
        self.profiles = ProfileList(self.create_profile(default=True))
        self.use_profile(0)

        _Configuration.__init__(self, **kwargs)

        backend = self.backend_instance
        # add profiles loaded by the backend
        for profile in flatten((backend.profiles, predefined_profiles)):
            self.profiles.insert(profile.pop('position'), profile,
                    overwrite=True, set_active=profile.pop('selected', False))

        for field_name, value in backend.static_options.iteritems():
            setattr(self, field_name, value)

    def create_profile(self, name=None, default=False):
        nonstatics = dict(((name, field.value) for name, field in
                           self.fields.iteritems() if not field.static))
        if default:
            return DefaultProfile(nonstatics)
        else:
            return ConfigurationProfile(name, nonstatics)

    def __setattr__(self, attr, value):
        new_value = super(Configuration, self).__setattr__(attr, value)
        if new_value is not None and not self.fields[attr].static:
            self.profiles.active.set(attr, new_value)

    def __getattr__(self, name):
        if name in ('frontend', 'window'):
            # window as alias
            return self.get_frontend()

        field = self.fields.get(name, None)
        if field is not None:
            if field.static:
                return field.value
            else:
                return self.profiles.active.values[name]
        else:
            raise AttributeError("No such attribute '%s'" % name)

    def use_profile(self, profile):
        self.profiles._use(profile)
        for name, instance in self.fields.iteritems():
            if instance.static: continue
            instance.value = self.profiles.active.values[name]


    # FRONTEND:
    def _init_frontend(self, fields):
        _Configuration._init_frontend(self, fields)

        self.window.add_profiles(self.profiles)

        self.window.connect('profile-changed', self.frontend_profile_changed)
        self.window.connect('add-profile', self.frontend_add_profile)
        self.window.connect('remove-profile', self.frontend_remove_profile)

        self.window.set_active_profile_index(self.profiles.active_index)

    def frontend_field_value_changed(self, *args):
        if not self._ignore_frontend:
            super(Configuration, self).frontend_field_value_changed(*args)


    def frontend_profile_changed(self, sender, profile_name, index):
        """ Profile selection was changed by the frontend (user) """
        self._ignore_frontend = True
        self.use_profile(index)
        self._ignore_frontend = False
        self.window.editable = self.profiles.active.is_editable

    def frontend_add_profile(self, sender, profile_name, position):
        """ User added a profile using the "add profile" button """
        profile = self.create_profile(profile_name)
        self.profiles.insert(position, profile)
        self.window.insert_profile(profile, position)
        self.window.set_active_profile_index(position)

    def frontend_remove_profile(self, sender, position):
        """ User removed a profile using the "remove profile" button """
        del self.profiles[position]
        self.window.remove_profile(position)


    def run_frontend(self):
        _Configuration.run_frontend(self)
        del self.frontend_instance
