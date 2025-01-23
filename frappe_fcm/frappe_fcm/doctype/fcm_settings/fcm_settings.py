# Copyright (c) 2025, Talat El Beick and contributors
# For license information, please see license.txt

import json
import frappe
import firebase_admin

from firebase_admin import credentials
from frappe.model.document import Document


class FCMSettings(Document):
    pass

@frappe.whitelist()
def initialize_firebase():
    fcm_setting = frappe.get_doc('FCM Settings')
    with open('firebase-adminsdk.json', 'w', encoding='utf-8') as file:
        json.dump(json.loads(fcm_setting.credential), file)
    cred = credentials.Certificate('firebase-adminsdk.json')
    firebase_admin.initialize_app(cred)
    frappe.msgprint('Firebase app has been initialized')
