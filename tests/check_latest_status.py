"""Check if the bot has updated its status in the last 24 hours.

This is not actually testing the code. It's a way to alert if something is wrong with the bot.
"""

# standard library
import datetime

# third party
import pytz
from mastodon import Mastodon


def test_latest_status():
    """Check if the bot has updated its status in the last 24 hours."""

    # lookup latest status
    mastodon = Mastodon(api_base_url="https://mastodon.social")
    account = mastodon.account_lookup("s2coastalbot")
    status = mastodon.account_statuses(id=account.id, only_media=True, limit=1)[0]

    # check latest status date
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday = pytz.UTC.localize(yesterday)
    assert status.created_at > yesterday
