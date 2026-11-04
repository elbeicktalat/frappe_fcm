import frappe
from frappe import _
import json


@frappe.whitelist()
def send_notification(
        title,
        body,
        token=None,
        contact_name=None,
        data=None,
        image=None,
        sticky=0,
        priority='default',
        icon=None,
        color=None,
        click_action=None,
        notification_platform='All',
        android_channel_id=None,
):
    """
    Whitelisted function to create and submit an FCM Notification document.
    Excludes contacts that do not have an FCM Token.
    """
    try:
        fcm_token = token

        if contact_name:
            # Fetch token from contact
            fcm_token = frappe.db.get_value('Contact', contact_name, 'fcm_token')
            if not fcm_token:
                # Skip silently or log a message if the contact has no token
                frappe.logger().debug(f"Skipping notification for {contact_name}: No FCM Token found.")
                return None

        if not fcm_token:
            # If no token is provided or found, skip
            return None

        doc = frappe.new_doc('FCM Notification')
        doc.title = title
        doc.body = body
        doc.data = json.dumps(data) if isinstance(data, dict) else data
        doc.image = image
        doc.sticky = sticky
        doc.priority = priority
        doc.icon = icon
        doc.color = color
        doc.click_action = click_action
        doc.notification_platform = notification_platform
        doc.android_channel_id = android_channel_id
        doc.token = fcm_token

        if contact_name:
            doc.notification_type = 'Contact'
            doc.contact = contact_name
        else:
            doc.notification_type = 'Token'

        doc.insert()
        doc.submit()
        return doc.name
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "FCM Notification Creation Error")
        frappe.throw(_("Failed to create or submit FCM Notification document: {0}").format(str(e)))
