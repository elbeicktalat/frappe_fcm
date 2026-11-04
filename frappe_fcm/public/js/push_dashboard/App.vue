<!-- How the push notifications fared over a period: sent, delivered, read
     (the app's receipts), failed, sent again -- by day, by kind, by contact,
     and the latest ones with their ticks. -->
<template>
	<div class="pd">
		<div class="pd-bar">
			<div class="pd-periods">
				<button
					v-for="p in periods"
					:key="p.days"
					class="btn btn-xs"
					:class="days === p.days ? 'btn-primary' : 'btn-default'"
					@click="setDays(p.days)"
				>
					{{ p.label }}
				</button>
			</div>
			<span class="text-muted small" v-if="data">{{ __("Since {0}", [frappe.datetime.str_to_user(data.since)]) }}</span>
		</div>

		<div v-if="!data" class="pd-empty">{{ loading ? __("Loading...") : "" }}</div>
		<template v-else>
			<!-- The period in numbers. -->
			<div class="pd-kpis">
				<div class="pd-kpi">
					<div class="pd-kpi-label">{{ __("Sent") }}</div>
					<div class="pd-kpi-value">{{ fmt(t.total) }}</div>
					<div class="pd-kpi-sub" v-if="t.untracked">{{ __("{0} before receipts", [fmt(t.untracked)]) }}</div>
				</div>
				<div class="pd-kpi">
					<div class="pd-kpi-label"><span class="pd-ticks">✓✓</span> {{ __("Delivered") }}</div>
					<div class="pd-kpi-value">{{ pct(t.delivered_any, t.tracked) }}</div>
					<div class="pd-kpi-sub">{{ fmt(t.delivered_any) }} / {{ fmt(t.tracked) }} · {{ __("in {0} on average", [duration(t.delivery_seconds)]) }}</div>
				</div>
				<div class="pd-kpi">
					<div class="pd-kpi-label"><span class="pd-ticks pd-read">✓✓</span> {{ __("Read") }}</div>
					<div class="pd-kpi-value">{{ pct(t.read, t.tracked) }}</div>
					<div class="pd-kpi-sub">{{ fmt(t.read) }} · {{ __("after {0} on average", [duration(t.read_seconds)]) }}</div>
				</div>
				<div class="pd-kpi" :class="{ 'pd-warn': t.sent }">
					<div class="pd-kpi-label"><span class="pd-ticks">✓</span> {{ __("Not confirmed") }}</div>
					<div class="pd-kpi-value">{{ fmt(t.sent) }}</div>
					<div class="pd-kpi-sub">{{ __("{0} sent again", [fmt(t.retried)]) }}</div>
				</div>
				<div class="pd-kpi" :class="{ 'pd-bad': t.failed }">
					<div class="pd-kpi-label"><span class="pd-fail">✕</span> {{ __("Failed") }}</div>
					<div class="pd-kpi-value">{{ fmt(t.failed) }}</div>
					<div class="pd-kpi-sub">{{ __("FCM refused them") }}</div>
				</div>
			</div>

			<!-- By day. -->
			<div class="pd-card">
				<div class="pd-card-head">{{ __("By day") }}</div>
				<div ref="chart" class="pd-chart"></div>
			</div>

			<div class="pd-grid">
				<!-- By kind. -->
				<div class="pd-card">
					<div class="pd-card-head">{{ __("By kind") }}</div>
					<table class="pd-table">
						<tr>
							<th>{{ __("Kind") }}</th>
							<th class="n">{{ __("Sent") }}</th>
							<th>{{ __("Delivered / read") }}</th>
						</tr>
						<tr v-for="k in data.kinds" :key="k.kind">
							<td>{{ k.kind || __("(none)") }}</td>
							<td class="n">{{ fmt(k.total) }}</td>
							<td>
								<div class="pd-meter" :title="`${pct(k.delivered, k.tracked)} · ${pct(k.read, k.tracked)}`">
									<span class="pd-meter-delivered" :style="{ width: share(k.delivered, k.tracked) }"></span>
									<span class="pd-meter-read" :style="{ width: share(k.read, k.tracked) }"></span>
								</div>
								<span class="text-muted small">{{ pct(k.delivered, k.tracked) }} · {{ pct(k.read, k.tracked) }}</span>
							</td>
						</tr>
						<tr v-if="!data.kinds.length"><td colspan="3" class="text-muted">{{ __("Nothing sent in the period.") }}</td></tr>
					</table>
				</div>

				<!-- By contact: who gets them, and who doesn't. -->
				<div class="pd-card">
					<div class="pd-card-head">{{ __("By contact") }}</div>
					<table class="pd-table">
						<tr>
							<th>{{ __("Contact") }}</th>
							<th class="n">{{ __("Sent") }}</th>
							<th class="n">{{ __("Not confirmed") }}</th>
							<th>{{ __("Last delivered") }}</th>
						</tr>
						<tr
							v-for="c in data.contacts"
							:key="c.contact"
							class="pd-link"
							:class="{ 'pd-row-warn': c.tracked && !c.last_delivered }"
							@click="frappe.set_route('Form', 'Contact', c.contact)"
						>
							<td>{{ c.full_name }}</td>
							<td class="n">{{ fmt(c.total) }}</td>
							<td class="n" :class="{ 'pd-warn-text': c.pending }">{{ fmt(c.pending) }}</td>
							<td>
								<span v-if="c.last_delivered">{{ ago(c.last_delivered) }}</span>
								<span v-else-if="c.tracked" class="pd-warn-text" :title="__('Its phone never confirmed one: an old token, or the app gone?')">{{ __("never") }}</span>
							</td>
						</tr>
						<tr v-if="!data.contacts.length"><td colspan="4" class="text-muted">{{ __("Nothing sent in the period.") }}</td></tr>
					</table>
				</div>
			</div>

			<!-- The latest ones, with their ticks. -->
			<div class="pd-card">
				<div class="pd-card-head">
					<span>{{ __("Latest") }}</span>
					<div class="pd-filters">
						<button
							v-for="f in filters"
							:key="f.value"
							class="btn btn-xs"
							:class="status === f.value ? 'btn-primary' : 'btn-default'"
							@click="setStatus(f.value)"
						>
							{{ f.label }}
						</button>
					</div>
				</div>
				<table class="pd-table">
					<colgroup>
						<col style="width: 40px" />
						<col />
						<col style="width: 18%" />
						<col style="width: 12%" />
						<col style="width: 11%" />
						<col style="width: 11%" />
					</colgroup>
					<tr>
						<th></th>
						<th>{{ __("Notification") }}</th>
						<th>{{ __("To") }}</th>
						<th>{{ __("Sent") }}</th>
						<th>{{ __("Delivered") }}</th>
						<th>{{ __("Read") }}</th>
					</tr>
					<tr v-for="r in data.recent" :key="r.name" class="pd-link" @click="frappe.set_route('Form', 'FCM Notification', r.name)">
						<td class="pd-tick-cell" :title="statusLabel(r.status)">
							<span :class="tick(r.status).cls">{{ tick(r.status).text }}</span>
						</td>
						<td>
							<div class="ellipsis pd-title">{{ r.title || __("(data only)") }}</div>
							<div class="text-muted small ellipsis">
								<span v-if="r.kind">{{ r.kind }} · </span>{{ r.body }}
								<span v-if="r.retry_count" class="pd-warn-text"> · {{ __("sent {0} more times", [r.retry_count]) }}</span>
							</div>
						</td>
						<td class="ellipsis">{{ r.full_name || r.contact || "" }}</td>
						<td class="text-muted small">{{ ago(r.creation) }}</td>
						<td class="text-muted small">{{ after(r.creation, r.delivered_at) }}</td>
						<td class="text-muted small">{{ after(r.creation, r.read_at) }}</td>
					</tr>
					<tr v-if="!data.recent.length"><td colspan="6" class="text-muted">{{ __("None.") }}</td></tr>
				</table>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

const METHOD = "frappe_fcm.frappe_fcm.page.push_dashboard.push_dashboard.get_dashboard";
const COLORS = { read: "#34b7f1", delivered: "#7cb342", sent: "#f5a623", failed: "#e24c4c", untracked: "#c8ccd0" };

const periods = [
	{ days: 1, label: __("Today") },
	{ days: 7, label: __("7 days") },
	{ days: 30, label: __("30 days") },
	{ days: 90, label: __("90 days") },
];
const filters = [
	{ value: null, label: __("All") },
	{ value: "Sent", label: __("Not confirmed") },
	{ value: "Delivered", label: __("Delivered") },
	{ value: "Read", label: __("Read") },
	{ value: "Failed", label: __("Failed") },
];

const days = ref(7);
const status = ref(null);
const data = ref(null);
const loading = ref(false);
const chart = ref(null);
const t = computed(() => data.value?.totals || {});

async function load() {
	loading.value = true;
	try {
		data.value = await frappe.xcall(METHOD, { days: days.value, status: status.value });
		await nextTick();
		drawChart();
	} finally {
		loading.value = false;
	}
}

function setDays(value) {
	days.value = value;
	load();
}

function setStatus(value) {
	status.value = value;
	load();
}

function drawChart() {
	if (!chart.value || !data.value) return;
	const rows = data.value.daily;
	const series = [
		["read", __("Read")],
		["delivered", __("Delivered")],
		["sent", __("Not confirmed")],
		["failed", __("Failed")],
		["untracked", __("Before receipts")],
	].filter(([key]) => rows.some((r) => r[key]));
	chart.value.innerHTML = "";
	if (!series.length) {
		chart.value.innerHTML = `<div class="text-muted small pd-empty">${__("Nothing sent in the period.")}</div>`;
		return;
	}
	new frappe.Chart(chart.value, {
		type: "bar",
		height: 220,
		data: {
			labels: rows.map((r) => frappe.datetime.str_to_user(r.day).slice(0, 5)),
			datasets: series.map(([key, name]) => ({ name, values: rows.map((r) => r[key]) })),
		},
		colors: series.map(([key]) => COLORS[key]),
		barOptions: { stacked: 1, spaceRatio: 0.4 },
		axisOptions: { xIsSeries: 1, shortenYAxisNumbers: 1 },
	});
}

const fmt = (v) => format_number(v || 0, null, 0);
const pct = (part, whole) => (whole ? `${Math.round(((part || 0) / whole) * 100)}%` : "–");
const share = (part, whole) => (whole ? `${((part || 0) / whole) * 100}%` : "0%");
const ago = (value) => (value ? frappe.datetime.prettyDate(value) : "");

// "12 s", "4 min", "1 h 20 min".
function duration(seconds) {
	if (seconds === null || seconds === undefined) return "–";
	const s = Math.round(seconds);
	if (s < 60) return __("{0} s", [s]);
	const m = Math.round(s / 60);
	if (m < 60) return __("{0} min", [m]);
	return __("{0} h {1} min", [Math.floor(m / 60), m % 60]);
}

// How long after it was sent (empty: not yet).
const after = (sent, at) => (at ? duration(moment(at).diff(moment(sent), "seconds")) : "");

function tick(value) {
	if (value === "Read") return { text: "✓✓", cls: "pd-ticks pd-read" };
	if (value === "Delivered") return { text: "✓✓", cls: "pd-ticks" };
	if (value === "Sent") return { text: "✓", cls: "pd-ticks" };
	if (value === "Failed") return { text: "✕", cls: "pd-fail" };
	return { text: "–", cls: "text-muted" };
}

function statusLabel(value) {
	return (
		{
			Sent: __("Sent: no phone confirmed it yet"),
			Delivered: __("Delivered: the phone got it"),
			Read: __("Read: its user opened it"),
			Failed: __("Failed: FCM refused it"),
		}[value] || __("Sent before receipts")
	);
}

onMounted(load);
defineExpose({ load });
</script>

<style scoped>
.pd { padding: 4px 0 24px; }
.pd-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.pd-periods, .pd-filters { display: flex; gap: 6px; flex-wrap: wrap; }
.pd-empty { padding: 32px; text-align: center; color: var(--text-muted); }
.pd-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px; }
.pd-kpi { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 14px 16px; }
.pd-kpi-label { color: var(--text-muted); font-size: var(--text-sm); }
.pd-kpi-value { font-size: 26px; font-weight: 600; color: var(--text-color); margin-top: 2px; }
.pd-kpi-sub { color: var(--text-muted); font-size: var(--text-xs); margin-top: 2px; }
.pd-kpi.pd-warn .pd-kpi-value { color: var(--orange-600, #e68a00); }
.pd-kpi.pd-bad .pd-kpi-value { color: var(--red-600, #e24c4c); }
.pd-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 12px 16px; margin-bottom: 14px; min-width: 0; }
.pd-card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-weight: 600; margin-bottom: 8px; flex-wrap: wrap; }
.pd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 14px; }
.pd-chart { min-height: 220px; }
.pd-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
.pd-table th { color: var(--text-muted); font-weight: 500; font-size: var(--text-xs); text-align: left; padding: 6px 6px; border-bottom: 1px solid var(--border-color); }
.pd-table td { padding: 7px 6px; border-bottom: 1px solid var(--border-color); vertical-align: middle; overflow: hidden; }
.pd-table .n { text-align: right; width: 90px; }
.pd-tick-cell { width: 34px; text-align: center; }
.pd-title { font-weight: 500; }
.pd-link { cursor: pointer; }
.pd-link:hover { background: var(--subtle-fg); }
.pd-ticks { color: var(--gray-500, #8d99a6); font-weight: 700; letter-spacing: -3px; }
.pd-read { color: #34b7f1; }
.pd-fail { color: var(--red-600, #e24c4c); font-weight: 700; }
.pd-warn-text { color: var(--orange-600, #e68a00); }
.pd-row-warn td:first-child { border-left: 3px solid var(--orange-500, #f5a623); }
.pd-meter { position: relative; height: 8px; border-radius: 4px; background: var(--gray-200, #eef0f2); overflow: hidden; margin-bottom: 2px; }
.pd-meter span { position: absolute; left: 0; top: 0; bottom: 0; }
.pd-meter-delivered { background: #7cb342; }
.pd-meter-read { background: #34b7f1; }
</style>
