// The Push Dashboard's app (Vue), mounted in its Desk page
// (frappe_fcm/frappe_fcm/page/push_dashboard): the page keeps its title and
// Refresh, the app the rest.
import { createApp } from "vue";
import App from "./push_dashboard/App.vue";

frappe.provide("frappe_fcm.push_dashboard");

frappe_fcm.push_dashboard.mount = function (page) {
	const app = createApp(App);
	// The Desk's own, in the templates too (they don't see window's).
	Object.assign(app.config.globalProperties, { __, frappe });
	const view = app.mount($("<div>").appendTo(page.main)[0]);
	page.set_secondary_action(__("Refresh"), () => view.load());
	return view;
};
