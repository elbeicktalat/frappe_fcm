import json
import os
import frappe
import firebase_admin

from firebase_admin import credentials
from firebase_admin import messaging

def get_firebase_app():
	"""Ensures Firebase is initialized and returns the app instance."""
	if not firebase_admin._apps:
		initialize_firebase_app()
	return firebase_admin.get_app()

def initialize_firebase_app():
	"""Initializes the Firebase Admin SDK using credentials from FCM Settings."""
	fcm_setting = frappe.get_doc("FCM Settings")
	if not fcm_setting.credential:
		frappe.throw(frappe._("Please provide Firebase Credentials in FCM Settings."))

	try:
		cred_path = frappe.get_site_path("private", "firebase-adminsdk.json")
		os.makedirs(os.path.dirname(cred_path), exist_ok=True)

		with open(cred_path, "w", encoding="utf-8") as file:
			json.dump(json.loads(fcm_setting.credential), file)
		
		cred = credentials.Certificate(cred_path)
		firebase_admin.initialize_app(cred)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Firebase Initialization Error")
		frappe.throw(frappe._("Failed to initialize Firebase: {0}").format(str(e)))

def send_fcm_message(message):
	"""Sends a pre-constructed messaging.Message object using the initialized app."""
	try:
		app = get_firebase_app()
		response = messaging.send(message, app=app)
		return response
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FCM Send Message Error")
		frappe.throw(frappe._("Failed to send FCM notification: {0}").format(str(e)))
