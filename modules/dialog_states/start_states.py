from telegram.ext import ConversationHandler

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# State definitions for top level conversation
START_SELECTORS, SIGN_UP_AS_PATIENT, SIGN_UP_AS_CC1 = map(chr, range(3))

# State definitions for patient registration conversation
(
    PATIENT_REGISTRATION_ACTION,
    CONF_CODE,
    TYPING_CODE,
    CONF_TZ
) = map(chr, range(3, 7))

# States for Time Zone settings
(
    CONF_TZ_ACTION,
    TYPING_TZ,
    CONF_LOCATION
) = map(chr, range(7, 10))

# State definitions for specialist (CC1) registration conversation
(
    CC1_REGISTRATION_ACTION,
) = map(chr, range(10, 11))

# Other states
(
    START_OVER,
    LOCATION_OVER,
    REGISTRATION_OVER,
    CONF_TZ_OVER,


) = map(chr, range(11, 15))
STOPPING = "STOPPING"
