# Copyright (c) 2025, Talat El Beick and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe_fcm.setup import initialize_firebase_app


class FCMSettings(Document):
	pass

@frappe.whitelist()
def initialize_firebase():
	"""Manual initialization from the desk button"""
	initialize_firebase_app()
