"""The Push Dashboard (/app/push-dashboard): how the push notifications
fared -- sent, delivered, read (the app's receipts, frappe_fcm.api), failed,
sent again -- over a period: by day, by kind (data.type), by contact, and the
latest ones. A notification sent before the receipts has no status: counted
apart (Untracked)."""

import frappe
from frappe.utils import add_days, cint, getdate, today

ROLES = ("System Manager",)
PERIODS = (1, 7, 30, 90)
STATUSES = ("Sent", "Delivered", "Read", "Failed")
# The kind of a notification: its data's "type".
KIND = "if(json_valid(data), json_unquote(json_extract(data, '$.type')), null)"


@frappe.whitelist()
def get_dashboard(days: int = 7, status: str | None = None):
	"""{totals, daily, kinds, contacts, recent} for the last `days` days
	(1: today); `status` narrows the latest ones."""
	frappe.only_for(ROLES)
	days = cint(days) if cint(days) in PERIODS else 7
	since = getdate(add_days(today(), -(days - 1)))
	args = {"since": since}
	where = "docstatus = 1 and creation >= %(since)s"

	totals = frappe.db.sql(
		f"""select count(*) total,
			sum(delivery_status = 'Sent') sent,
			sum(delivery_status = 'Delivered') delivered,
			sum(delivery_status = 'Read') `read`,
			sum(delivery_status = 'Failed') failed,
			sum(ifnull(delivery_status, '') = '') untracked,
			sum(retry_count > 0) retried,
			avg(timestampdiff(second, creation, delivered_at)) delivery_seconds,
			avg(timestampdiff(second, creation, read_at)) read_seconds
		from `tabFCM Notification` where {where}""",
		args,
		as_dict=True,
	)[0]
	for key in ("total", "sent", "delivered", "read", "failed", "untracked", "retried"):
		totals[key] = cint(totals[key])
	# Delivered counts what was read too (read is delivered).
	tracked = totals.total - totals.untracked
	totals.tracked = tracked
	totals.delivered_any = totals.delivered + totals.read

	daily = frappe.db.sql(
		f"""select date(creation) day,
			sum(delivery_status = 'Read') `read`,
			sum(delivery_status = 'Delivered') delivered,
			sum(delivery_status = 'Sent') sent,
			sum(delivery_status = 'Failed') failed,
			sum(ifnull(delivery_status, '') = '') untracked
		from `tabFCM Notification` where {where}
		group by date(creation) order by day""",
		args,
		as_dict=True,
	)
	by_day = {str(row.day): row for row in daily}
	days_list = []
	for i in range(days):
		day = str(add_days(since, i))
		row = by_day.get(day) or {}
		days_list.append({"day": day, **{k: cint(row.get(k)) for k in ("read", "delivered", "sent", "failed", "untracked")}})

	kinds = frappe.db.sql(
		f"""select ifnull({KIND}, '') kind, count(*) total,
			sum(delivery_status in ('Delivered', 'Read')) delivered,
			sum(delivery_status = 'Read') `read`,
			sum(delivery_status in ('Sent', 'Delivered', 'Read', 'Failed')) tracked
		from `tabFCM Notification` where {where}
		group by kind order by total desc limit 20""",
		args,
		as_dict=True,
	)

	contacts = frappe.db.sql(
		f"""select contact, count(*) total,
			sum(delivery_status in ('Delivered', 'Read')) delivered,
			sum(delivery_status = 'Read') `read`,
			sum(delivery_status = 'Sent') pending,
			sum(delivery_status in ('Sent', 'Delivered', 'Read', 'Failed')) tracked,
			max(delivered_at) last_delivered
		from `tabFCM Notification` where {where} and ifnull(contact, '') != ''
		group by contact order by pending desc, total desc limit 30""",
		args,
		as_dict=True,
	)
	names = dict(frappe.get_all("Contact", filters={"name": ["in", [c.contact for c in contacts] or [""]]},
		fields=["name", "full_name"], as_list=True))
	for c in contacts:
		c.full_name = names.get(c.contact) or c.contact

	recent_where = where
	if status in STATUSES:
		recent_where += " and delivery_status = %(status)s"
		args["status"] = status
	elif status == "Untracked":
		recent_where += " and ifnull(delivery_status, '') = ''"
	recent = frappe.db.sql(
		f"""select name, title, body, contact, delivery_status status, creation, delivered_at, read_at,
			retry_count, {KIND} kind
		from `tabFCM Notification` where {recent_where}
		order by creation desc limit 50""",
		args,
		as_dict=True,
	)
	for r in recent:
		r.full_name = names.get(r.contact) or frappe.db.get_value("Contact", r.contact, "full_name") if r.contact else None

	return {
		"days": days,
		"since": str(since),
		"totals": totals,
		"daily": days_list,
		"kinds": kinds,
		"contacts": contacts,
		"recent": recent,
	}
