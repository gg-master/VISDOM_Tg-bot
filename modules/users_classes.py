import re

import pytz
import logging
import datetime as dt
from threading import Thread
from typing import Dict, Tuple

from telegram import Update
from telegram.ext import CallbackContext

from modules.location import Location
from modules.notification_dailogs import PillTakingDialog, DataCollectionDialog
from modules.timer import create_daily_notification, remove_job_if_exists, \
    repeating_task
from tools.tools import convert_tz

from db_api import get_patient_by_chat_id, add_patient, change_accept_time, \
    change_patients_time_zone, get_last_record_by_accept_time, add_patronage, \
    get_patronage_by_chat_id, add_record, get_all_patronages

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
    notification_states = {
        'MOR': [PillTakingDialog, DataCollectionDialog],
        'EVE': [DataCollectionDialog]
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

        self.alarmed = {'MOR': False, 'EVE': False}

        # Текущее состояние диалога
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
        if not (self.default_times[time].replace(
                hour=self.default_times[time].hour - 1) <= self.times[time]
                <= self.default_times[time].replace(
                    hour=self.default_times[time].hour + 1)):
            self.times[time] -= delta
            return False
        return True

    def create_notification(self, context: CallbackContext, **kwargs):
        """Создание уведомлений при регистрации или
        после изменения времени в настройках"""
        for name, notification_time in list(self.times.items())[:]:
            time = self.tz.localize(notification_time)

            now = dt.datetime.now(tz=self.tz)
            next_r_time = None
            if kwargs.get('register') and name == 'MOR':
                next_r_time = now.replace(
                    day=now.day + 1, hour=time.hour, minute=time.minute,
                    second=0, microsecond=0)
            # TODO проверить время уведомлений
            create_daily_notification(
                context=context,
                time=time,
                next_run_time=next_r_time,
                name=name,
                user=self,
                task_data={
                    'interval': dt.timedelta(hours=1) if name == 'MOR'
                    else dt.timedelta(minutes=30),
                    'last': self.tz.localize(self.time_limiters[name][1]
                                             ).astimezone(pytz.utc).time()},
            )

    def recreate_notification(self, context: CallbackContext, **kwargs):
        remove_job_if_exists(f'{self.chat_id}-rep_task', context)
        self.create_notification(context, **kwargs)

    def restore_repeating_task(self, context: CallbackContext, **kwargs):
        """Восстановление повторяющихся сообщений"""
        state_name = self.state()[0]

        # После регистрации первое утреннее уведомление придет на след. день
        if self.check_last_record_by_name(state_name)[0] or \
                (kwargs.get('register') and state_name == 'MOR'):
            return None

        # Проверяем время в которое произошел рестарт.
        # Если рестар был между лимитами определенного уведомления, то
        # восстанавливаем репитер, чтобы отправить уведомление
        now = dt.datetime.now(tz=self.tz).time()
        first = self.tz.localize(self.times[state_name])
        last = self.tz.localize(self.time_limiters[state_name][1])

        if now < first.time() or now > last.time():
            return None
        # TODO подправить время интервала
        interval = dt.timedelta(minutes=2) if state_name == 'MOR' \
            else dt.timedelta(minutes=2)

        f = dt.timedelta(hours=first.hour, minutes=first.minute)
        n = dt.timedelta(hours=now.hour, minutes=now.minute)

        first = first + interval * (abs(f - n) // interval + 1)

        context.job_queue.run_repeating(
            callback=repeating_task,
            interval=interval,
            first=first,
            last=last.astimezone(pytz.utc).time(),
            context={'user': self, 'name': state_name},
            name=f'{self.chat_id}-rep_task'
        )

    def state(self):
        """Возвращает имя временного таймера и состояние
        (т.е. в каком диалоге находится пользователь)"""
        return self.curr_state

    def set_curr_state(self, name):
        """Устанавливает новое состояние"""
        self.curr_state = [name, 0]

    def _set_curr_state_by_time(self):
        # Устанавливаем состояние диалога исходя из текущего времени
        if self.tz.localize(self.times['MOR']).time() < \
                dt.datetime.now(tz=self.tz).time() < \
                self.tz.localize(self.times['EVE']).time():
            self.set_curr_state('MOR')
        else:
            self.set_curr_state('EVE')

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
        """Сброс времени уведомлений до дефолтных"""
        if self.times == self.default_times:
            return False
        self.times = self.default_times.copy()
        return True

    def cancel_updating(self):
        """Возвращение значений времени и ЧП к начальным значениям"""
        self.times = self.orig_t.copy()
        self.location = self.orig_loc

    def save_updating(self, context: CallbackContext, check_user=True):
        """Сохранение изменение настроект ЧП и времени уведомлений"""
        # Проверка существует ли пользователь в бд
        if check_user and (not get_patient_by_chat_id(self.chat_id)
                           or not self.accept_times):
            raise ValueError()
        # Флаги, чтобы узнать изменилось ли время или часовой пояс
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

            self._set_curr_state_by_time()

            if check_user:
                Thread(target=self._threading_save_sett,
                       args=(ch_times, ch_tz)).start()

            # Восстанавливливаем уведомления
            self.recreate_notification(context, register=not check_user)
            self.restore_repeating_task(context, register=not check_user)

            self.check_user_records(context)

    def _threading_save_sett(self, ch_times, ch_tz):
        if ch_times:
            change_accept_time(self.accept_times['MOR'],
                               self.times['MOR'].time())
            change_accept_time(self.accept_times['EVE'],
                               self.times['EVE'].time())
        if ch_tz:
            change_patients_time_zone(self.chat_id, self.tz.zone)

    def restore(self, code: str, times: Dict[str, dt.time], tz_str: str,
                accept_times):
        super().register()
        self.code = code

        # Конвертирование часового пояса из строки в объект
        self.tz = pytz.timezone(tz_str)

        self.location = Location(tz=-int(re.search(
            pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))

        # Преобразуем dt.time в dt.datetime
        self.times = {k: self.default_times[k].replace(
            hour=times[k].hour, minute=times[k].minute) for k in times.keys()}

        self.accept_times = accept_times
        self.orig_t, self.orig_loc = self.times, self.location

        self._set_curr_state_by_time()

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW USER: '
                     f'{update.effective_user.id} - {self.code}')
        Thread(target=self._threading_reg, args=(update, context)).start()

    def _threading_reg(self, update: Update, context: CallbackContext):
        # TODO удалить кастомные настройки перед деплоем
        self.tz = pytz.timezone('Etc/GMT-3')
        self.times = {
            'MOR': dt.datetime(1212, 12, 12, 8, 41, 0),
            'EVE': dt.datetime(1212, 12, 12, 8, 42, 0)
        }

        # Обрабатываем часовой пояс паципента при регистрации
        self.tz = pytz.timezone(convert_tz(self.location.get_coords(),
                                           self.location.time_zone()))
        self.orig_loc = self.location = Location(tz=-int(re.search(
            pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))

        # Добавляем пациента в бд
        self.accept_times = add_patient(
            time_morn=self.times['MOR'].time(),
            time_even=self.times['EVE'].time(),
            name=update.effective_user.full_name,
            user_code=self.code,
            time_zone=self.tz.zone,
            chat_id=self.chat_id
        )
        self.save_updating(context, check_user=False)

    def save_patient_record(self):
        # print(self.data_response)
        self.alarmed[self.state()[0]] = False
        Thread(target=self._threading_save_record).start()

    def _threading_save_record(self):
        add_record(
            time_zone=self.tz.zone,
            time=self.times[self.state()[0]].time(),
            response_time=dt.datetime.now(self.tz),
            accept_time_id=self.accept_times[self.state()[0]],
            sys_press=self.data_response['sys'],
            dias_press=self.data_response['dias'],
            heart_rate=self.data_response['heart'],
            comment=self.pill_response[self.pill_response.find(':') + 2:]
            if self.pill_response and ':' in self.pill_response
            else self.pill_response
        )

    def check_user_reg(self):
        patient = get_patient_by_chat_id(self.chat_id)
        patronage = get_patronage_by_chat_id(self.chat_id)
        # TODO добавить проверку по патронажу
        if patient:
            if not patient.member:
                return False
            return None
        return True

    def check_user_records(self, context: CallbackContext):
        # Если аларм у пользователя уже сработал, то заново не активируем
        if any(self.alarmed.values()) or not self.accept_times:
            return None
        Thread(target=self._thread_check_user_records, args=(context,)).start()

    def _thread_check_user_records(self, context: CallbackContext):
        mor_record = self.check_last_record_by_name('MOR')
        eve_record = self.check_last_record_by_name('EVE')
        if (not mor_record[0] and mor_record[1] >= 25) or \
                (not eve_record[0] and eve_record[1] >= 25):
            self.alarmed['MOR' if mor_record[1] >= 25 else "EVE"] = True
            PatronageUser.send_alarm(
                context=context,
                user=self,
                days=int(mor_record[1] / 24) if self.alarmed['MOR']
                else int(eve_record[1] / 24)
            )

    def check_last_record_by_name(self, name) -> Tuple[bool, int]:
        """
        :param name:
        :return: True if all right and last record time less than 24 hour
        :return: False if last record time more then 24 hour
        """
        recs = get_last_record_by_accept_time(self.accept_times[name])
        hours = 24
        if recs:
            now = dt.datetime.now(tz=self.tz)
            hours = abs(now - recs[-1].response_time.astimezone(
                self.tz)).total_seconds() // 3600
            if hours < 24:
                return True, hours
        return False, hours


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
        add_patronage(chat_id=self.chat_id)

    @staticmethod
    def send_alarm(context, **kwargs):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        user = kwargs['user']
        # TODO проработать общение касаемо аларма
        patronage = get_all_patronages()
        if patronage:
            patronage = patronage[0]
            text = f'❗️ Внимание ❗️\n' \
                   f'В течении суток пациент {user.code} не принял ' \
                   f'лекарство/не отправил данные давления и ЧСС.\n' \
                   f'Дней без ответа: {kwargs["days"]}'

            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    'Получить данные о пациенте',
                    callback_data=f'A_PATIENT_DATA&{user.code}')]],
                one_time_keyboard=True)

            context.bot.send_message(patronage.chat_id, text, reply_markup=kb)
