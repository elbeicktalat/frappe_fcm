// Push Dashboard: how the push notifications fared -- the Vue app in
// frappe_fcm/public/js/push_dashboard (push_dashboard.bundle.js), its data
// from push_dashboard.py.

frappe.pages["push-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Push Dashboard"),
		single_column: true,
	});
	frappe.require("push_dashboard.bundle.js", () => {
		wrapper.dashboard = frappe_fcm.push_dashboard.mount(page);
	});
};

// Back on the page: what came meanwhile.
frappe.pages["push-dashboard"].on_page_show = function (wrapper) {
	if (wrapper.dashboard) wrapper.dashboard.load();
};
