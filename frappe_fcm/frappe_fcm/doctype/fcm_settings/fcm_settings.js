// Copyright (c) 2025, Talat El Beick and contributors
// For license information, please see license.txt

frappe.ui.form.on("FCM Settings", {
    refresh(frm) {
        frm.add_custom_button(__('Initialize Firebase App'), function () {
            frappe.call('frappe_fcm.frappe_fcm.doctype.fcm_settings.fcm_settings.initialize_firebase');
        });
    },
});