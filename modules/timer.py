import pytz
import datetime as dt

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
    """Добавляем задачу в очередь"""
    chat_id = kwargs['user'].chat_id
    try:
        # Добавляем задачу в очередь

        # Удаляем старую задачу с таким же именем
        remove_job_if_exists(f'{chat_id} - {kwargs["name"]}', context)

        job = context.job_queue.run_daily(
            callback=daily_task,
            # when=5,
            time=kwargs['time'],
            context=kwargs,
            name=f'{chat_id}-{kwargs["name"]}'
        )
    except (IndexError, ValueError):
        context.bot.send_message(chat_id, 'Произошла ошибка про попытке '
                                          'включить таймер. Обратитесь к '
                                          'администратору')


def daily_task(context: CallbackContext):
    """Таски, которые выполняются ежедневно утром и вечером"""
    job = context.job
    data = job.context

    # Устанавливаем пользователю состояние диалога
    data['user'].set_curr_state(data['name'])

    # Стираем старые ответы пользователя
    data['user'].clear_responses()

    # Создание диалога для сбора данных
    data['user'].notification_states[data['name']][
        data['user'].state()[1]].pre_start(context, data)

    data['user'].rep_task_name = f'{data["user"].chat_id}' \
                                 f'-{data["user"].msg_to_del.message_id}'

    # Создаем новую циклическую задачу
    context.job_queue.run_repeating(
        callback=repeating_task,
        # interval=20,
        # last=dt.datetime.now(pytz.utc) + dt.timedelta(seconds=20*4),
        interval=data['task_data']['interval'],
        last=data['task_data']['last'],
        context=data,
        name=data['user'].rep_task_name
    )


def repeating_task(context: CallbackContext):
    job = context.job
    data = job.context

    # Удаляем старое сообщение
    context.bot.delete_message(data['user'].chat_id,
                               data['user'].msg_to_del.message_id)

    # Запускаем новое уведомление
    data['user'].notification_states[data['name']][
        data['user'].state()[1]].pre_start(context, data)

