# Copyright (c) 2025, Talat El Beick and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from firebase_admin import messaging
from frappe.model.document import Document
from datetime import datetime
from frappe_fcm.setup import send_fcm_message


class FCMNotification(Document):
    def on_submit(self):
        # Its receipts: the app answers with this name and key when the
        # phone gets it and when it's opened (frappe_fcm.api.acknowledge),
        # as WhatsApp's ticks -- FCM itself never tells. Not delivered, it's
        # sent again (frappe_fcm.api.retry_undelivered).
        self.ack_key = frappe.generate_hash(length=24)
        self.db_set('ack_key', self.ack_key, update_modified=False)
        self.send()

    def send(self, throw=True):
        """Sends it to FCM (again, for a retry: the same name and key, so the
        phone shows it once). Sent, or Failed -- thrown unless `throw` is
        off (a retry, which mustn't stop the others)."""
        try:
            response = send_fcm_message(self.build_message())
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "FCM Notification Send Error")
            self.db_set('delivery_status', 'Failed', update_modified=False)
            if throw:
                frappe.throw(_("Failed to send FCM Notification: {0}").format(str(e)))
            return False
        self.timestamp = datetime.now()
        self.db_set({
            'response': str(response),
            'timestamp': self.timestamp,
            'last_sent_at': frappe.utils.now_datetime(),
            'delivery_status': 'Sent',
        }, update_modified=False)
        if throw:
            frappe.msgprint(_("FCM Notification sent successfully: {0}").format(response))
        return True

    def build_message(self):
        # Handle Data Map (must be a flat dict with string values)
        data_payload = {}
        if self.data:
            try:
                raw_data = json.loads(self.data) if isinstance(self.data, str) else self.data
                if isinstance(raw_data, dict):
                    data_payload = {str(k): str(v) for k, v in raw_data.items()}
            except (ValueError, TypeError):
                frappe.throw(_("Invalid Data Map. It must be a valid JSON dictionary."))
        data_payload['fcm_notification'] = self.name
        data_payload['fcm_ack'] = self.ack_key or ''

        # No title nor body: a data-only message, handed to the app itself
        # even in the background (e.g. to ring an alarm) -- sent with high
        # priority, so Android delivers it to a sleeping phone at once.
        notification = None
        if self.title or self.body:
            notification = messaging.Notification(
                title=self.title,
                body=self.body,
                image=f'{frappe.utils.get_url()}{self.image}' if self.image else None,
            )

        # On Android, shown with this name as its tag: sent again, it takes
        # the place of the first in the tray instead of a second one beside it.
        android_config = None
        if self.notification_platform == 'Android':
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sticky=True if self.sticky == 1 else False,
                    priority=self.priority,
                    icon=self.icon,
                    color=self.color,
                    click_action=self.click_action,
                    channel_id=self.get('android_channel_id') or None,
                    tag=self.name,
                )
            )
        elif notification is not None:
            # Any platform: on Android, shown on the app's channel (its sound).
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    channel_id=self.get('android_channel_id') or None,
                    tag=self.name,
                )
            )
        if notification is None:
            android_config = messaging.AndroidConfig(priority="high")

        return messaging.Message(
            token=self.current_token(),
            notification=notification,
            data=data_payload if data_payload else None,
            android=android_config,
        )

    def current_token(self):
        """The phone's token: its Contact's now (a retry may find it renewed),
        else the one it was sent to."""
        if self.contact:
            token = frappe.db.get_value('Contact', self.contact, 'fcm_token')
            if token:
                return token
        return self.token
