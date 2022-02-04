import re

import pytz
import logging
import datetime as dt
from threading import Thread
from typing import Dict

from telegram import Update
from telegram.ext import CallbackContext

from modules.location import Location
from modules.notification_dailogs import PillTakingDialog, DataCollectionDialog
from modules.timer import create_daily_notification, remove_job_if_exists
from tools.tools import convert_tz

from data.patronage import Patronage
from data.patient import Patient

from pandas import DataFrame
from data import db_session


db_session.global_init()
db_sess = db_session.create_session()


class BasicUser:
    def __init__(self):
        self.is_registered = False

    def registered(self):
        return self.is_registered

    def register(self, *args):
        self.is_registered = True


class PatientUser(BasicUser):
    # Ограничители времени
    time_limiters = {
        'MOR': [dt.datetime(1212, 12, 12, 6, 00, 0),
                dt.datetime(1212, 12, 12, 12, 00, 0)],
        'EVE': [dt.datetime(1212, 12, 12, 17, 00, 0),
                dt.datetime(1212, 12, 12, 21, 00, 0)]
    }
    default_times = {
        'MOR': dt.datetime(1212, 12, 12, 8, 00, 0),
        'EVE': dt.datetime(1212, 12, 12, 20, 00, 0)
    }

    def __init__(self, chat_id: int):
        super().__init__()
        # Id чата с пользователем
        self.chat_id = chat_id

        self.code = None

        self.location = self.tz = None
        self._times = self.default_times.copy()
        self.orig_loc = self.orig_t = None

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

    def times(self):
        return dict(map(lambda x: (x, self._times[x].strftime("%H:%M")),
                        self._times.keys()))

    def add_minutes(self, time, minutes):
        # Добавление минут
        delta = dt.timedelta(minutes=int(minutes))
        self._times[time] += delta
        # Ограничение времени
        if not (self.time_limiters[time][0] <= self._times[time]
                <= self.time_limiters[time][1]):
            self._times[time] -= delta
            return False
        return True

    def create_notification(self, context: CallbackContext):
        for name, notification_time in list(self._times.items())[:]:
            create_daily_notification(
                context=context,
                time=self.tz.localize(notification_time),
                name=name,
                user=self,
                task_data={
                    'interval': dt.timedelta(hours=1) if name == 'MOR'
                    else dt.timedelta(minutes=30),
                    'last': self.tz.localize(
                        self.time_limiters[name][1]).time()},
            )

    def recreate_notification(self, context: CallbackContext):
        remove_job_if_exists(self.rep_task_name, context)
        self.create_notification(context)

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

    def drop_notif_time(self):
        if self._times == self.default_times:
            return False
        self._times = self.default_times.copy()
        return True

    def cancel_updating(self):
        """Возвращение значений времени и ЧП к начальным значениям"""
        self._times = self.orig_t.copy()
        self.location = self.orig_loc

    def save_updating(self, context: CallbackContext):
        """Сохранение изменение настроект ЧП и времени уведомлений"""
        # TODO запрос в бд на изменение времени
        # TODO запрос на проверку времеи последней записи
        if self._times != self.orig_t or self.location != self.orig_loc:
            if self.location != self.orig_loc:
                self.tz = pytz.timezone(convert_tz(self.location.get_coords(),
                                                   self.location.time_zone()))
                self.orig_loc = self.location = Location(tz=-int(re.search(
                    pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))
            if self._times != self.orig_t:
                self.orig_t = self._times.copy()
            self.recreate_notification(context)

    def is_msg_updated(self):
        return self.active_dialog_msg and \
               self.msg_to_del != self.active_dialog_msg

    def restore(self, context: CallbackContext,
                times: Dict[str, dt.time], tz_str: str):
        # Конвертирование часового пояса из строки в объект
        self.tz = pytz.timezone(tz_str)

        self.location = Location(tz=-int(re.search(
            pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))

        # Преобразуем dt.time в dt.datetime
        self._times = {k: self.default_times[k].replace(
            hour=times[k].hour, minute=times[k].minute) for k in times.keys()}

        self.save_updating(context)

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW USER: '
                     f'{update.effective_user.id} - {self.code}')
        thread = Thread(target=self._threading_reg, args=(update, context))
        thread.start()
        thread.join()

    def _threading_reg(self, update: Update, context: CallbackContext):
        # self.tz = pytz.timezone('Etc/GMT-3')
        # self._times = {
        #     'MOR': dt.time(19, 13, 0),
        #     'EVE': dt.time(19, 14, 0)
        # }
        self.save_updating(context)
        # TODO Регистрация в БД

    @staticmethod
    def get_patient_by_id(user_code):
        return db_sess.query(Patient).filter(
            Patient.user_code == user_code).first()


class PatronageUser(BasicUser):
    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW PATRONAGE: {update.effective_user.id}')
        # thread = Thread(target=self._threading_reg, args=(update, context))
        # thread.start()
        # thread.join()

    def _threading_reg(self, update: Update, context: CallbackContext):
        patronage = Patronage(chat_id=update.effective_chat.id)
        db_sess.add(patronage)
        db_sess.commit()

    @staticmethod
    def make_file_by_patient(patient):
        arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, arr_time_zone, \
        arr_id = [], [], [], [], [], []
        for accept_time in patient.accept_time:
            for record in accept_time.record:
                arr_sys_press.append(record.sys_press)
                arr_dias_press.append(record.dias_press)
                arr_heart_rate.append(record.heart_rate)
                arr_time.append(record.time)
                arr_time_zone.append(record.time_zone)
        df = DataFrame({'Систолическое давление': arr_sys_press,
                        'Диастолическое давление': arr_dias_press,
                        'Частота сердечных сокращений': arr_heart_rate,
                        'Время приема таблеток и измерений': arr_time,
                        'Часовой пояс': arr_time_zone})
        df.to_excel('static/' + patient.user_code + '.xlsx')

    @staticmethod
    def make_file_patients():
        arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, arr_time_zone, \
        patient_user_code = [], [], [], [], [], []
        patients = db_sess.query(Patient).all()
        for patient in patients:
            for accept_time in patient.accept_time:
                for record in accept_time.record:
                    patient_user_code.append(patient.id)
                    arr_sys_press.append(record.sys_press)
                    arr_dias_press.append(record.dias_press)
                    arr_heart_rate.append(record.heart_rate)
                    arr_time.append(record.time)
                    arr_time_zone.append(record.time_zone)
        df = DataFrame({'Код пациента': patient_user_code,
                        'Систолическое давление': arr_sys_press,
                        'Диастолическое давление': arr_dias_press,
                        'Частота сердечных сокращений': arr_heart_rate,
                        'Время приема таблеток и измерений': arr_time,
                        'Часовой пояс': arr_time_zone})
        df.to_excel(f'static/statistics.xlsx')
