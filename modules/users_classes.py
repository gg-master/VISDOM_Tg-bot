import re

import pytz
import logging
import datetime as dt
from threading import Thread
from typing import Dict

from telegram import Update
from telegram.ext import CallbackContext

from data.record import Record
from modules.location import Location
from modules.notification_dailogs import PillTakingDialog, DataCollectionDialog
from modules.timer import create_daily_notification, remove_job_if_exists, \
    repeating_task
from tools.tools import convert_tz

from data.patronage import Patronage
from data.patient import Patient

from db_api import get_patient_by_chat_id, add_patient, change_accept_time, \
    change_patients_time_zone, get_last_record_by_accept_time, add_patronage, \
    get_patronage_by_chat_id

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

        self.location = self.tz = self.accept_times = None
        self.times = self.default_times.copy()
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

    def str_times(self):
        return dict(map(lambda x: (x, self.times[x].strftime("%H:%M")),
                        self.times.keys()))

    def add_minutes(self, time, minutes):
        # Добавление минут
        delta = dt.timedelta(minutes=int(minutes))
        self.times[time] += delta
        # Ограничение времени
        if not (self.time_limiters[time][0] <= self.times[time]
                <= self.time_limiters[time][1]):
            self.times[time] -= delta
            return False
        return True

    def create_notification(self, context: CallbackContext):
        for name, notification_time in list(self.times.items())[:]:
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

    def restore_repeating_task(self, context: CallbackContext):
        """Восстановление повторяющихся сообщений"""
        state_name = self.state()[0]
        now = dt.datetime.now(tz=self.tz).time()

        # Проверяем время в которое произошел рестарт.
        # Если рестар был между лимитами определенного уведомления, то
        # восстанавливаем репитер, чтобы отправить уведомление
        first = self.tz.localize(self.times[state_name]).time()
        last = self.tz.localize(self.time_limiters[state_name][1]).time()
        if now < first or now > last:
            return None
        print(first, last, now, state_name)
        self.rep_task_name = f'{self.chat_id}-rep_task'
        job = context.job_queue.run_repeating(
            callback=repeating_task,
            # interval=5,
            # last=dt.datetime.now(pytz.utc) + dt.timedelta(seconds=20*4),
            interval=dt.timedelta(hours=1) if state_name == 'MOR' \
            else dt.timedelta(minutes=30),
            first=first, last=last,
            context={'user': self, 'name': state_name},
            name=self.rep_task_name
        )
        try:
            # Если время следующего запуска не определено, то удаляем.
            if not job.next_t:
                remove_job_if_exists(self.rep_task_name, context)
        except AttributeError as e:
            pass

    def state(self):
        """Возвращает имя временного таймера и состояние
        (т.е. в каком диалоге находится пользователь)"""
        return self.curr_state

    def set_curr_state(self, name):
        """Устанавливает новое состояние"""
        self.curr_state = [name, 0]

    def next_curr_state_index(self):
        """Переключает индекс текущего состояния"""
        self.curr_state[1] = min(1, self.curr_state[1] + 1)

    def clear_responses(self):
        self.pill_response = None
        self.data_response = {'sys': None, 'dias': None, 'heart': None}

    def is_msg_updated(self):
        return self.active_dialog_msg and \
               self.msg_to_del != self.active_dialog_msg

    def drop_notif_time(self):
        if self.times == self.default_times:
            return False
        self.times = self.default_times.copy()
        return True

    def cancel_updating(self):
        """Возвращение значений времени и ЧП к начальным значениям"""
        self.times = self.orig_t.copy()
        self.location = self.orig_loc

    def save_updating(self, context: CallbackContext, check_usr=True):
        """Сохранение изменение настроект ЧП и времени уведомлений"""
        # Проверка существует ли пользователь в бд
        if check_usr and (not get_patient_by_chat_id(self.chat_id)
                          or not self.accept_times):
            raise ValueError()
        ch_times = ch_tz = False
        if self.times != self.orig_t or self.location != self.orig_loc:
            if self.location != self.orig_loc:
                self.tz = pytz.timezone(convert_tz(self.location.get_coords(),
                                                   self.location.time_zone()))
                self.orig_loc = self.location = Location(tz=-int(re.search(
                    pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))
                ch_tz = True
            if self.times != self.orig_t:
                self.orig_t = self.times.copy()
                ch_times = True
            if self.tz.localize(self.times['MOR']).time() < \
                    dt.datetime.now(tz=self.tz).time() < \
                    self.tz.localize(self.times['EVE']).time():
                self.set_curr_state('MOR')
            else:
                self.set_curr_state('EVE')

            if check_usr:
                Thread(target=self._threading_save,
                       args=(ch_times, ch_tz)).start()
                # thread.start()
                # thread.join()

            # Восстанавливливаем уведомления
            self.recreate_notification(context)
            if not context.job_queue.get_jobs_by_name(
                    f'{self.chat_id}-rep_task'):
                self.restore_repeating_task(context)

    def _threading_save(self, ch_times, ch_tz):
        if ch_times:
            change_accept_time(self.accept_times['MOR'],
                               self.times['MOR'].time())
            change_accept_time(self.accept_times['EVE'],
                               self.times['EVE'].time())
        if ch_tz:
            change_patients_time_zone(self.chat_id, self.tz.zone)

        # self.check_user_records(
        #     get_last_record_by_accept_time(self.accept_times['MOR']),
        #     get_last_record_by_accept_time(self.accept_times['EVE']))

    def restore(self, times: Dict[str, dt.time], tz_str: str,
                accept_times=None):
        super().register()
        # Конвертирование часового пояса из строки в объект
        self.tz = pytz.timezone(tz_str)

        self.location = Location(tz=-int(re.search(
            pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))

        # Преобразуем dt.time в dt.datetime
        self.times = {k: self.default_times[k].replace(
            hour=times[k].hour, minute=times[k].minute) for k in times.keys()}

        self.accept_times = accept_times
        self.orig_t = self.times
        self.orig_loc = self.location

        # Восстановление состояния диалога после рестарта бота
        now = dt.datetime.now(tz=self.tz)
        if self.tz.localize(self.times['MOR']).time() < now.time() < \
                self.tz.localize(self.times['EVE']).time():
            self.set_curr_state('MOR')
        else:
            self.set_curr_state('EVE')

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW USER: '
                     f'{update.effective_user.id} - {self.code}')
        Thread(target=self._threading_reg, args=(update, context)).start()
        # thread.start()
        # thread.join()

    def _threading_reg(self, update: Update, context: CallbackContext):
        self.tz = pytz.timezone('Etc/GMT-3')
        self.times = {
            'MOR': dt.datetime(1212, 12, 12, 8, 00, 0),
            'EVE': dt.datetime(1212, 12, 12, 20, 43, 0)
        }

        self.save_updating(context, check_usr=False)

        self.accept_times = add_patient(
            time_morn=self.times['MOR'].time(),
            time_even=self.times['EVE'].time(),
            name=update.effective_user.full_name,
            user_code=self.code,
            time_zone=self.tz.zone,
            chat_id=self.chat_id
        )

    def check_user(self):
        patient = get_patient_by_chat_id(self.chat_id)
        patronage = get_patronage_by_chat_id(self.chat_id)
        if patient or patronage:
            if not patient.member:
                return False
            return None
        return True

    def check_user_records(self, mor_records, eve_records):
        # TODO проверка последней даты
        # TODO вызов аларма для патронажа
        if not mor_records and not eve_records:
            return
        if mor_records:
            rec: Record = mor_records[-1]
            now = dt.datetime.now(tz=self.tz).time()
            print(rec.time - now)


class PatronageUser(BasicUser):
    def __init__(self, chat_id):
        super().__init__()
        self.chat_id = chat_id

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW PATRONAGE: {update.effective_user.id}')
        Thread(target=self._threading_reg, args=(update, context)).start()

    def restore(self, context):
        super().register()

    def _threading_reg(self, update: Update, context: CallbackContext):
        add_patronage(
            chat_id=self.chat_id
        )

    @staticmethod
    def make_file_by_patient(patient):
        # with db_session.create_session() as db_sess:
        arr_sys_press, arr_dias_press, arr_heart_rate, arr_time, \
        arr_time_zone, arr_id = [], [], [], [], [], []
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
