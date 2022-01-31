import datetime as dt

from threading import Thread

from modules.location import Location
from modules.smart_timer import set_timer
from tools.tools import convert_tz


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

    def add_minutes(self, time, minutes):
        # Добавление минут
        self._times[time] += dt.timedelta(minutes=int(minutes))

    def register(self, update, context):
        super().register()
        thread = Thread(target=self._threading_reg, args=(update, context))
        thread.start()
        thread.join()

    def _threading_reg(self, update, context):
        time_zone = convert_tz(self._location.get_coords(),
                               self._location.time_zone())
        print(time_zone)
        # TODO
        # Регистрация в БД
        # Создание таймера
        #
        # set_timer(update, context, 10)
        print(self.times)


class Specialist(User):
    pass
