import logging
from typing import Dict, Optional

from telegram import error
from telegram.ext import CallbackContext


def remove_job_if_exists(name, context: CallbackContext):
    """Удаляем задачу по имени.
    Возвращаем True если задача была успешно удалена."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


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
        context.bot.send_message(chat_id, 'Произошла ошибка про попытке '
                                          'включить таймер. Обратитесь к '
                                          'администратору')


def daily_task(context: CallbackContext):
    """Таски, которые выполняются ежедневно утром и вечером"""
    job = context.job
    data: Optional[Dict] = job.context

    user = data['user']

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
            logging.exception(f'Cant find message id to delete in daily task. '
                              f'More:{e}')
    remove_job_if_exists(f'{user.chat_id}-rep_task', context)

    # Если с момента последней записи прошло более 24 часов, то устанавливаем
    if not user.check_last_record_by_name(data['name'])[0]:
        # Создание диалога для сбора данных
        user.notification_states[data['name']][
            user.state()[1]].pre_start(context, data)

        context.job_queue.run_repeating(
            callback=repeating_task,
            interval=data['task_data']['interval'],
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

    user.check_user_records(context)

    # Запускаем новое уведомление
    user.notification_states[data['name']][user.state()[1]].pre_start(
        context, data)


def deleting_pre_start_msg_task(context: CallbackContext):
    """Удаление сообщения после временного лимита"""
    job = context.job
    data: Optional[Dict] = job.context
    try:
        user = data['user']

        context.bot.delete_message(user.chat_id, user.msg_to_del.message_id)
        user.msg_to_del = None

        user.check_user_records(context)
    except error.TelegramError:
        remove_job_if_exists(f'{data["chat_id"]}-pre_start_msg', context)
