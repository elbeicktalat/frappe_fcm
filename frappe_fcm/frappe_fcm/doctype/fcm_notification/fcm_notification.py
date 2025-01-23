# Copyright (c) 2025, Talat El Beick and contributors
# For license information, please see license.txt

import frappe
import firebase_admin

from firebase_admin import messaging
from firebase_admin import credentials
from frappe.model.document import Document
from datetime import datetime


class FCMNotification(Document):
	def	on_submit(self):
		# This registration token comes from the client FCM SDKs.
		registration_token = self.token

		# See documentation on defining a message payload.
		message = messaging.Message(
			token=registration_token,
			notification=messaging.Notification(
				title=self.title,
				body=self.body,
				image=f'{frappe.utils.get_url()}{self.image}' if self.image is not None else None,
			),
			android=messaging.AndroidConfig(
				notification=messaging.AndroidNotification(
					sticky=True if self.sticky == 1 else False,
					priority=self.priority,
					icon=self.icon,
					color=self.color,
					click_action=self.click_action,
				)
        	) if self.notification_platform == 'Android' else None,
		)

		# Send a message to the device corresponding to the provided
		# registration token.
		response = messaging.send(message)
		self.timestamp = datetime.now()
	
@frappe.whitelist()
def	send_to_token(to, title, body, image, sticky, priority, icon, color, click_action):
	try:
		doc = frappe.get_doc({
			'doctype': 'FCM Notification',
			'token': to,
			'title': title,
			'body': body,
			'image': image,
			'sticky': sticky,
			'priority': priority,
			'icon': icon,
			'color': color,
			'click_action': click_action
		})

		doc.submit()
	except Exception as e:
		raise e
