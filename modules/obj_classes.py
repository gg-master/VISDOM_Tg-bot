import datetime as dt

from modules.location import Location
from modules.smart_timer import set_timer


class User:
    def __init__(self):
        self.is_registered = False

    def registered(self):
        return self.is_registered

    def register(self, *args):
        self.is_registered = True


class Patient(User):
    def __init__(self):
        super().__init__()
        self._code = self._location = None
        self._times = {
            'MOR': dt.datetime(1212, 12, 12, 8, 00, 0),
            'EVE': dt.datetime(1212, 12, 12, 20, 00, 0)
        }

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        self._code = code

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, location: Location):
        self._location = location

    @property
    def times(self):
        return dict(map(lambda x: (x, self._times[x].strftime("%H:%M")),
                        self._times.keys()))

    def add_minutes(self, sort, minutes):
        self._times[sort] += dt.timedelta(minutes=int(minutes))

    def register(self, update, context):
        super().register()
        set_timer(update, context, 10)


class Specialist(User):
    pass
