import pytz
import datetime as dt
import logging
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
    # Ограничители времени
    time_limiters = {
        'MOR': [dt.datetime(1212, 12, 12, 6, 00, 0),
                dt.datetime(1212, 12, 12, 12, 00, 0)],
        'EVE': [dt.datetime(1212, 12, 12, 17, 00, 0),
                dt.datetime(1212, 12, 12, 21, 00, 0)]
    }

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
        delta = dt.timedelta(minutes=int(minutes))
        self._times[time] += delta
        if not (self.time_limiters[time][0] <= self._times[time]
                <= self.time_limiters[time][1]):
            self._times[time] -= delta
            return False
        return True

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER new user: {update.effective_user.id}'
                     f'-{self._code}')
        thread = Thread(target=self._threading_reg, args=(update, context))
        thread.start()
        thread.join()

    def _threading_reg(self, update: Update, context: CallbackContext):
        time_zone = pytz.timezone(
            convert_tz(self._location.get_coords(),
                       self._location.time_zone()))

        # Нормализируем UTC по часовому поясу пользователя
        self._times = {k: time_zone.localize(self._times[k])
                       for k in self._times.keys()}
        context.user_data['user'] = UserNotifications(
            context, update.effective_chat.id, self._times, time_zone)
        print(time_zone)
        # TODO
        # Регистрация в БД


class UserNotifications(BasicUser):
    def __init__(self, context: CallbackContext, chat_id, times, tz):
        super().__init__()
        self.chat_id = chat_id
        # Время уведомлений.
        self.times = times
        # Ограничители для времени уведомлений
        self.time_limiters = Patient.time_limiters
        # Часовой пояс в строков представлении. Например "Europe\Moscow"
        self.tz = tz

        # Сообщения, которые отправляются пользователю при получении
        # уведомлений. Сохраняем их для функции удаления старых сообщений
        # при обновлении уведомления.
        self.msg_to_del = self.active_dialog_msg = None
        self.rep_task_name = None

        self.notification_states = {
            'MOR': [PillTakingDialog, DataCollectionDialog],
            'EVE': [DataCollectionDialog]
        }
        self.curr_state = []  # [name, index]

        # Ответы от пользователя на уведомления
        self.pill_response = None
        self.data_response = {'sys': None, 'dias': None, 'heart': None}

        self.create_notification(context)

    def create_notification(self, context: CallbackContext):
        for name, notification_time in list(self.times.items())[:2]:
            create_daily_notification(
                context=context,
                time=notification_time,
                name=name,
                user=self,
                task_data={
                    'interval': dt.timedelta(hours=1) if name == 'MOR'
                    else dt.timedelta(minutes=30),
                    'last': self.tz.localize(
                        self.time_limiters[name][1]).time()},
            )

    def state(self):
        """Возвращает имя временного таймера и состояние
        (т.е. в каком диалоге находится пользователь)"""
        return self.curr_state

    def set_curr_state(self, name):
        """Устанавливает новое состояние"""
        self.curr_state = [name, 0]

    def next_curr_state_index(self):
        """Переключает индекс текущего состояния"""
        self.curr_state[1] += 1

    def clear_responses(self):
        self.pill_response = None
        self.data_response = {'sys': None, 'dias': None, 'heart': None}


class Patronage(BasicUser):
    pass
