"""
    PyHSS GSUP Event Publisher
    Copyright (C) 2025  Lennart Rosam <hello@takuto.de>

    SPDX-License-Identifier: AGPL-3.0-or-later

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from messaging import RedisMessaging
from .event.subscriber_updated_event import SubscriberUpdatedEvent


class GsupEventPublisher:
    """
    Publisher for GSUP events to Redis queue.
    """

    def __init__(self, redis_messaging: RedisMessaging):
        self.redis_messaging = redis_messaging
        self.queue_name = "gsup_events"

    def publish_subscriber_updated(
        self,
        imsi: str,
        msisdn: str,
        apns: list,
        disabled: bool
    ) -> bool:
        """
        Publishes a subscriber updated event to the GSUP events queue.

        Args:
            imsi: The IMSI of the subscriber
            msisdn: The MSISDN of the subscriber
            apns: List of APNs for the subscriber
            disabled: Whether the subscriber is disabled

        Returns:
            bool: True if event was published successfully, False otherwise
        """
        try:
            event = SubscriberUpdatedEvent(
                imsi=imsi,
                msisdn=msisdn,
                apns=apns,
                disabled=disabled
            )

            event_json = event.model_dump_json()
            result = self.redis_messaging.sendMessage(
                queue=self.queue_name,
                message=event_json,
                queueExpiry=3600  # 1 hour expiry
            )

            return bool(result)

        except Exception as e:
            print(f"Failed to publish subscriber updated event: {e}")
            return False

