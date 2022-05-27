import logging
import datetime as dt
from typing import Dict, Optional

import pytz
from telegram import error
from telegram.ext import CallbackContext


def remove_job_if_exists(name, context: CallbackContext):
    """Удаляем задачу по имени.
    Возвращаем True если задача была успешно удалена."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        logging.info(f'REMOVED TASK: {name}')
        job.schedule_removal()
    return True


def calc_start_time(now, first, interval):
    f = dt.timedelta(hours=first.hour, minutes=first.minute)
    n = dt.timedelta(hours=now.hour, minutes=now.minute)

    return first + interval * (abs(f - n) // interval + 1)


def restore_repeating_task(user, context: CallbackContext, **kwargs):
    """Восстановление повторяющихся сообщений"""
    state_name = user.state()[0]

    # После регистрации первое утреннее уведомление придет на след. день
    from db_api import get_all_records_by_accept_time
    if user.check_last_record_by_name(state_name)[0] or \
            (state_name == 'MOR' and (
                    kwargs.get('register') or
                    (not get_all_records_by_accept_time(
                        user.accept_times['EVE']) and
                     not get_all_records_by_accept_time(
                         user.accept_times['MOR'])))):
        return None

    # Проверяем время в которое произошел рестарт.
    # Если рестар был между лимитами определенного уведомления, то
    # восстанавливаем репитер, чтобы отправить уведомление
    now = dt.datetime.now(tz=user.p_loc.tz).time()
    first = user.p_loc.tz.localize(user.times.time_limiters[state_name][0])
    last = user.p_loc.tz.localize(user.times.time_limiters[state_name][1])

    if now < user.p_loc.tz.localize(user.times[state_name]).time() or \
            now > last.time():
        return None

    interval = dt.timedelta(hours=1) if state_name == 'MOR' \
        else dt.timedelta(minutes=30)

    remove_job_if_exists(f'{user.chat_id}-rep_task', context)
    context.job_queue.run_repeating(
        callback=repeating_task,
        interval=interval,
        first=calc_start_time(now, first, interval),
        last=last.astimezone(pytz.utc).time(),
        context={'user': user, 'name': state_name},
        name=f'{user.chat_id}-rep_task'
    )


def create_daily_notification(context: CallbackContext, **kwargs):
    """Создаем уведомление которое будет срабатывать ежедневно"""
    chat_id = kwargs['user'].chat_id
    try:
        # Удаляем старую задачу с таким же именем
        remove_job_if_exists(f'{chat_id}-{kwargs["name"]}', context)

        context.job_queue.run_daily(
            callback=daily_task,
            time=kwargs['time'],
            context=kwargs,
            name=f'{chat_id}-{kwargs["name"]}',
            job_kwargs={'next_run_time': kwargs['next_run_time']}
            if kwargs['next_run_time'] else {},
        )
    except (IndexError, ValueError):
        try:
            context.bot.send_message(chat_id, 'Произошла ошибка про попытке '
                                              'включить таймер. Обратитесь к '
                                              'администратору')
        except error.Unauthorized:
            pass


def daily_task(context: CallbackContext):
    """Таски, которые выполняются ежедневно утром и вечером"""
    from modules.users_classes import PatientUser
    job = context.job
    data: Optional[Dict] = job.context

    user: PatientUser = data['user']

    user.alarmed[data['name']] = False

    user.check_user_records(context)
    user.set_curr_state(data['name'])
    user.clear_responses()

    # Если пользователь не ответил на предыдущее сообщение (уведомление),
    # то удаляем его
    if user.msg_to_del:
        try:
            context.bot.delete_message(user.chat_id,
                                       user.msg_to_del.message_id)
        except Exception as e:
            logging.info(f'Cant find message id to delete in daily task. '
                         f'More:{e}')

    remove_job_if_exists(f'{user.chat_id}-rep_task', context)

    # Если с момента последней записи прошло более 24 часов, то устанавливаем
    if not user.check_last_record_by_name(data['name'])[0]:
        # Создание диалога для сбора данных
        user.notification_states[data['name']][
            user.state()[1]].pre_start(context, data)

        n = dt.datetime.now(tz=user.p_loc.tz).time()
        f = user.p_loc.tz.localize(user.times.time_limiters[data['name']][0])

        context.job_queue.run_repeating(
            callback=repeating_task,
            interval=data['task_data']['interval'],
            first=calc_start_time(n, f, data['task_data']['interval']),
            last=data['task_data']['last'],
            context=data,
            name=f'{user.chat_id}-rep_task'
        )


def repeating_task(context: CallbackContext):
    """Повторяющиеся уведомления в рамках временого лимита"""
    job = context.job
    data: Optional[Dict] = job.context

    user = data['user']

    if user.msg_to_del:
        context.bot.delete_message(user.chat_id, user.msg_to_del.message_id)

    user.set_curr_state(data['name'])
    user.check_user_records(context)

    # Запускаем новое уведомление
    user.notification_states[data['name']][user.state()[1]].pre_start(
        context, data)


def deleting_pre_start_msg_task(context: CallbackContext):
    """Удаление сообщения после временного лимита"""
    job = context.job
    data: Optional[Dict] = job.context
    user = data['user']
    try:
        if user.msg_to_del:
            context.bot.delete_message(user.chat_id, user.msg_to_del.message_id)
            user.msg_to_del = None

        user.clear_responses()
        user.save_patient_record()

        user.check_user_records(context)
    except error.TelegramError:
        remove_job_if_exists(f'{user.chat_id}-pre_start_msg', context)
