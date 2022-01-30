from telegram import Update
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


def set_timer(update: Update, context: CallbackContext, time):
    """Добавляем задачу в очередь"""
    chat_id = update.effective_chat.id
    try:
        # args[0] должен содержать значение аргумента
        # (секунды таймера)
        due = int(time)
        if due < 0:
            context.bot.send_message(
                chat_id, 'Извините, не умеем возвращаться в прошлое')
            return
        # Добавляем задачу в очередь
        # и останавливаем предыдущую (если она была)
        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(
            task,
            due,
            context=chat_id,
            name=str(chat_id)
        )
        text = f'Вернусь через {due} секунд!'
        if job_removed:
            text += ' Старая задача удалена.'
        # Присылаем сообщение о том, что всё получилось.
        context.bot.send_message(chat_id, text)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id, 'Использование: /set <секунд>')


def task(context: CallbackContext):
    """Выводит сообщение"""
    job = context.job
    context.bot.send_message(job.context, text='Вернулся!')


def unset_timer(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Хорошо, вернулся сейчас!' if job_removed else 'Нет активного таймера'
    update.message.reply_text(text)