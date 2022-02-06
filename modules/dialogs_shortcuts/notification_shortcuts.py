from telegram.ext import ConversationHandler

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

(
    # State definitions for top level conversation
    PILL_TAKING_ACTION,
    DATA_COLLECT_ACTION,
    # Constants
    PILL_TAKING,
    DATA_COLLECT,
) = map(chr, range(100, 100 + 4))

(
    # State
    TYPING,
    # Constants
    CONFIRM_PILL_TAKING,
    CANT_PILL_TAKING,
) = map(chr, range(100 + 4, 100 + 7))

(
    # Constants
    PILL_TAKING_OVER,
    DATA_COLLECT_OVER
) = map(chr, range(100 + 7, 100 + 9))

