from telegram.ext import ConversationHandler

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

(
    # State definitions for top level conversation
    START_SELECTORS,
    # Constants
    SIGN_UP_AS_PATIENT, SIGN_UP_AS_PATRONAGE
) = map(chr, range(3))

(
    # State definitions for patient registration conversation
    PATIENT_REGISTRATION_ACTION,
    TYPING_CODE,
    # Constants
    CONF_NOTIFICATIONS,
    CONF_CODE,
    CONF_TZ,
) = map(chr, range(3, 8))

(
    # States for Time Zone settings
    CONF_TZ_ACTION,
    TYPING_TZ,
    # Constants
    CONF_LOCATION
) = map(chr, range(8, 11))

(
    # States for Notification settings
    CONF_NOTIF_ACTIONS,
    TIME_CHANGE,
) = map(chr, range(11, 13))

(
    # State definitions for specialist (CC1) registration conversation
    PATRONAGE_REGISTRATION_ACTION,
) = map(chr, range(13, 14))

(
    # Other states
    STOPPING,
    # Other constants
    START_OVER,
    LOCATION_OVER,
    REGISTRATION_OVER,
    CONF_TZ_OVER,
    FINISH_REGISTRATION,
) = map(chr, range(14, 20))


(
    RECEIVE_TOKEN,
    TYPING_TOKEN,
    DEFAULT_JOB,
    SOMETHING,
    MESSAGE_HANDLER,
    SEND_USER_DATA_PAT,
    PATRONAGE_ACTION,
    ENTER_TOKEN
) = map(chr, range(20, 28))

PATRONAGE_JOB = 'PATRONAGE_JOB'

