import datetime as dt
import pytz

from threading import Thread

from telegram import Update
from telegram.ext import CallbackContext

from modules.location import Location
from modules.notification_dailogs import PillTakingDialog, DataCollectionDialog
from modules.timer import create_daily_notification
from tools.tools import convert_tz


class BasicUser:
    def __init__(self):
        self.is_registered = False

    def registered(self):
        return self.is_registered

    def register(self, *args):
        self.is_registered = True


class Patient(BasicUser):
    def __init__(self):
        super().__init__()
        self._code = self._location = None
        self._times = {
            'MOR': dt.datetime(1212, 12, 12, 8, 00, 0, tzinfo=pytz.utc),
            'EVE': dt.datetime(1212, 12, 12, 20, 00, 0, tzinfo=pytz.utc)
        }
        # Ограничители времени
        self._time_limiters = {
            'MOR': [dt.datetime(1212, 12, 12, 6, 00, 0, tzinfo=pytz.utc),
                    dt.datetime(1212, 12, 12, 12, 00, 0, tzinfo=pytz.utc)],
            'EVE': [dt.datetime(1212, 12, 12, 17, 00, 0, tzinfo=pytz.utc),
                    dt.datetime(1212, 12, 12, 21, 00, 0, tzinfo=pytz.utc)]
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
        delta = dt.timedelta(minutes=int(minutes))
        self._times[time] += delta
        if not (self._time_limiters[time][0] <= self._times[time]
                <= self._time_limiters[time][1]):
            self._times[time] -= delta
            return False
        return True

    def register(self, update, context):
        super().register()
        thread = Thread(target=self._threading_reg, args=(update, context))
        thread.start()
        thread.join()

    def _threading_reg(self, update: Update, context: CallbackContext):
        time_zone = pytz.timezone(
            convert_tz(self._location.get_coords(),
                       self._location.time_zone()))

        # Нормализируем UTC по часовому поясу пользователя
        self._times = {k: time_zone.normalize(self._times[k])
                       for k in self._times.keys()}
        context.user_data['user'] = UserNotifications(
            context, update.effective_chat.id, self._times,
            self._time_limiters, time_zone)

        print(time_zone)
        # TODO
        # Регистрация в БД
        # Создание таймера

        print(self.times)


class UserNotifications(BasicUser):
    def __init__(self, context: CallbackContext, chat_id, times, limiters, tz):
        super().__init__()
        self.chat_id = chat_id
        self.times = times
        self.time_limiters = limiters
        self.tz = tz

        self.msg = None
        self.rep_task_name = None

        self.notification_states = {
            'MOR': [PillTakingDialog, DataCollectionDialog],
            'EVE': [DataCollectionDialog]
        }
        self.curr_state = []  # [name, index]

        self.create_notification(context)

    def create_notification(self, context: CallbackContext):
        for name, datetime in list(self.times.items())[:1]:
            create_daily_notification(
                context=context,
                user=self,
                time=datetime.time(),
                name=name,
                task_data={
                    'interval': dt.timedelta(hours=1) if name == 'MOR'
                    else dt.timedelta(minutes=30),
                    'last': self.tz.normalize(
                        self.time_limiters[name][1]).time(),

                },
            )

    def state(self):
        return self.curr_state

    def set_curr_state(self, name):
        self.curr_state = [name, 0]

    def next_curr_state_index(self):
        self.curr_state[1] += 1


class Patronage(BasicUser):
    pass
