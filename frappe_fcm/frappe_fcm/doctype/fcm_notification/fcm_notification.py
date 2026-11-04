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
        # This registration token comes from the client FCM SDKs.
        registration_token = self.token

        # Handle Data Map (must be a flat dict with string values)
        data_payload = {}
        if self.data:
            try:
                raw_data = json.loads(self.data) if isinstance(self.data, str) else self.data
                if isinstance(raw_data, dict):
                    data_payload = {str(k): str(v) for k, v in raw_data.items()}
            except (ValueError, TypeError):
                frappe.throw(_("Invalid Data Map. It must be a valid JSON dictionary."))

        # Construct AndroidConfig if platform is Android
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
                )
            )
        elif self.get('android_channel_id') and (self.title or self.body):
            # Any platform: on Android, shown on the app's channel -- its sound.
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(channel_id=self.android_channel_id)
            )

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
        elif android_config is None:
            android_config = messaging.AndroidConfig(priority="high")

        # Construct the message
        message = messaging.Message(
            token=registration_token,
            notification=notification,
            data=data_payload if data_payload else None,
            android=android_config,
        )

        # Send message
        try:
            response = send_fcm_message(message)
            self.timestamp = datetime.now()
            self.db_set('response', str(response))
            frappe.msgprint(_("FCM Notification sent successfully: {0}").format(response))
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "FCM Notification Send Error")
            frappe.throw(_("Failed to send FCM Notification: {0}").format(str(e)))
