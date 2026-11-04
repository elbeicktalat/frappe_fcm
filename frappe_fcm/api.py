"""Receipts for FCM Notifications, as WhatsApp's ticks: FCM never tells the
server whether a phone got a push, nor whether it was read -- the app does.
Each push carries its FCM Notification's name and a random key
(fcm_notification, fcm_ack in its data); the app sends them back here when
the phone gets it (delivered) and when the user opens it (read).

Open to a guest: the app answers from the background too, where it isn't
signed in -- the key, known only to that push, is what's checked."""

import hmac

import frappe
from frappe.utils import add_to_date, now_datetime

EVENTS = ("delivered", "read")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def acknowledge(notification: str, key: str, event: str):
	"""The phone got FCM Notification `notification` (event "delivered"), or
	its user opened it ("read" -- which is delivered too). Only with its key;
	a receipt again changes nothing (the first time stays)."""
	if event not in EVENTS:
		frappe.throw("Unknown event.", frappe.ValidationError)
	row = frappe.db.get_value(
		"FCM Notification", notification, ["ack_key", "delivery_status", "delivered_at", "read_at"], as_dict=True
	)
	if not row or not row.ack_key or not hmac.compare_digest(str(row.ack_key), str(key or "")):
		frappe.throw("Unknown notification.", frappe.PermissionError)

	now = now_datetime()
	values = {}
	if not row.delivered_at:
		values["delivered_at"] = now
	if event == "read" and not row.read_at:
		values["read_at"] = now
	status = "Read" if (event == "read" or row.read_at) else "Delivered"
	if row.delivery_status != status:
		values["delivery_status"] = status
	if values:
		frappe.db.set_value("FCM Notification", notification, values, update_modified=False)
	return {"status": status}


def receipt(notification: str):
	"""Where a notification is: {status, delivered_at, read_at} -- for the
	apps that send them (e.g. whether a store saw its cash receipt)."""
	return frappe.db.get_value(
		"FCM Notification", notification, ["delivery_status as status", "delivered_at", "read_at"], as_dict=True
	)


# Not delivered: sent again after these minutes from the last time (then
# given up: the phone's off, or the app uninstalled), within a day of it.
RETRY_AFTER_MINUTES = (5, 15, 45)
RETRY_WITHIN_HOURS = 24


def retry_undelivered():
	"""Scheduler: the notifications FCM took but no phone confirmed (Sent, not
	Delivered) sent again -- the same name and key, so a phone that gets both
	shows it once (on Android, the second takes the first's place)."""
	now = now_datetime()
	for row in frappe.get_all(
		"FCM Notification",
		filters={
			"docstatus": 1,
			"delivery_status": "Sent",
			"delivered_at": ["is", "not set"],
			"retry_count": ["<", len(RETRY_AFTER_MINUTES)],
			"creation": [">", add_to_date(now, hours=-RETRY_WITHIN_HOURS)],
		},
		fields=["name", "retry_count", "last_sent_at", "creation"],
		limit=200,
	):
		wait = RETRY_AFTER_MINUTES[row.retry_count or 0]
		if add_to_date(row.last_sent_at or row.creation, minutes=wait) > now:
			continue
		doc = frappe.get_doc("FCM Notification", row.name)
		doc.db_set("retry_count", (row.retry_count or 0) + 1, update_modified=False)
		doc.send(throw=False)
		frappe.db.commit()
