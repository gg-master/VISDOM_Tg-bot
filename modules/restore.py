from telegram.ext import CallbackContext


class Restore:
    def __init__(self, dispatcher):
        self.callback = CallbackContext(dispatcher)
