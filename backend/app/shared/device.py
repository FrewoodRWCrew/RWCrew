# Telling a PC from a phone or tablet by the browser's "User-Agent" header,
# for the admin "Login History" screen. Plain regular expressions on purpose:
# no extra package (see CLAUDE.md, Python 3.14 wheel constraint), and good
# enough for "what kind of device was this", which is all the screen shows.
#
# Known limitation: since iPadOS 13, Safari on an iPad presents itself as a
# Mac, so an iPad counts as "desktop" here. The login's "source" ("pwa" for
# the phone section /m) still shows it was the phone app.

import re
from typing import Literal

DeviceType = Literal["desktop", "mobile", "tablet"]

# Checked first: tablets often also mention "Android" (without "Mobile").
_TABLET_PATTERN = re.compile(r"iPad|Tablet|PlayBook|Silk|Kindle", re.IGNORECASE)
# Android phones say "Android ... Mobile"; an Android without "Mobile" is a tablet.
_ANDROID_PATTERN = re.compile(r"Android", re.IGNORECASE)
_MOBILE_PATTERN = re.compile(r"Mobi|iPhone|iPod|Windows Phone|BlackBerry|Opera Mini", re.IGNORECASE)


def classify_device(user_agent: str | None) -> DeviceType | None:
    """Return "desktop", "mobile" or "tablet" for a User-Agent string, or None
    when there is none to go on (e.g. a script that sends no header)."""
    if user_agent is None or not user_agent.strip():
        return None
    if _TABLET_PATTERN.search(user_agent):
        return "tablet"
    if _ANDROID_PATTERN.search(user_agent):
        return "mobile" if re.search(r"Mobile", user_agent, re.IGNORECASE) else "tablet"
    if _MOBILE_PATTERN.search(user_agent):
        return "mobile"
    return "desktop"
