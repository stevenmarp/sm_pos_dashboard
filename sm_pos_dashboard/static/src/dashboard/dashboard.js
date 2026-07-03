/** @odoo-module **/

import {
    Component,
    onWillStart,
    onMounted,
    onPatched,
    onWillDestroy,
    useState,
    useRef,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

// fixed categorical order for the payment doughnut, never cycled
const SERIES_COLORS = ["#667eea", "#22c55e", "#f59e0b", "#ec4899", "#06b6d4"];

export class SmPosDashboard extends Component {
    static template = "sm_pos_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.busService = useService("bus_service");
        this.state = useState({
            data: null,
            period: "today",
            chartType: "bar",
            dark: window.localStorage.getItem("sm_pos_dash_dark") === "1",
        });
        this.destroyed = false;
        this.revenueCanvas = useRef("revenueCanvas");
        this.paymentCanvas = useRef("paymentCanvas");
        this.charts = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.load();
        });
        this.busService.addChannel("sm_pos_dashboard");
        this.busService.subscribe("SM_POS_DASH_UPDATE", () => this.scheduleLoad());
        onMounted(() => this.renderCharts());
        onPatched(() => this.renderCharts());
        onWillDestroy(() => {
            this.destroyed = true;
            clearTimeout(this.loadTimeout);
            this.destroyCharts();
        });
    }

    async load() {
        if (this.destroyed) {
            return;
        }
        this.state.data = await this.orm.call(
            "pos.order", "sm_dashboard_data", [], { period: this.state.period });
    }

    scheduleLoad() {
        clearTimeout(this.loadTimeout);
        this.loadTimeout = setTimeout(() => this.load(), 500);
    }

    async setPeriod(period) {
        this.state.period = period;
        await this.load();
    }

    setChartType(type) {
        this.state.chartType = type;
    }

    toggleDark() {
        this.state.dark = !this.state.dark;
        window.localStorage.setItem("sm_pos_dash_dark", this.state.dark ? "1" : "0");
    }

    fmt(value) {
        const d = this.state.data;
        const amount = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        });
        return d.currency_position === "before"
            ? `${d.currency_symbol} ${amount}`
            : `${amount} ${d.currency_symbol}`;
    }

    trendClass(pct) {
        return pct >= 0 ? "sm-dash-trend-up" : "sm-dash-trend-down";
    }

    trendLabel(pct) {
        const arrow = pct >= 0 ? "↗" : "↘";
        return `${arrow} ${Math.abs(pct)}%`;
    }

    get maxProductRevenue() {
        const tops = this.state.data.top_products;
        return tops.length ? tops[0].revenue : 0.01;
    }

    get maxConfigRevenue() {
        const cfgs = this.state.data.per_config;
        return cfgs.length ? Math.max(...cfgs.map((c) => c.revenue)) : 0.01;
    }

    destroyCharts() {
        for (const chart of Object.values(this.charts)) {
            chart.destroy();
        }
        this.charts = {};
    }

    renderCharts() {
        const d = this.state.data;
        if (!d || !window.Chart) {
            return;
        }
        this.destroyCharts();
        const ink = this.state.dark ? "#9ca3af" : "#6b7280";
        const grid = this.state.dark ? "#374151" : "#e5e7eb";

        if (this.revenueCanvas.el) {
            this.charts.revenue = new window.Chart(this.revenueCanvas.el, {
                type: this.state.chartType,
                data: {
                    labels: d.series_labels,
                    datasets: [{
                        label: "Revenue",
                        data: d.series_values,
                        backgroundColor: "rgba(102, 126, 234, 0.85)",
                        borderColor: "#667eea",
                        borderWidth: 2,
                        borderRadius: 4,
                        fill: this.state.chartType === "line"
                            ? { target: "origin", above: "rgba(102, 126, 234, 0.12)" }
                            : false,
                        tension: 0.35,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => this.fmt(ctx.parsed.y),
                            },
                        },
                    },
                    scales: {
                        x: { ticks: { color: ink }, grid: { display: false } },
                        y: {
                            ticks: { color: ink },
                            grid: { color: grid },
                            beginAtZero: true,
                        },
                    },
                },
            });
        }

        if (this.paymentCanvas.el && d.payments.length) {
            this.charts.payment = new window.Chart(this.paymentCanvas.el, {
                type: "doughnut",
                data: {
                    labels: d.payments.map((p) => p.name),
                    datasets: [{
                        data: d.payments.map((p) => p.amount),
                        backgroundColor: SERIES_COLORS.slice(0, d.payments.length),
                        borderWidth: 2,
                        borderColor: this.state.dark ? "#1f2937" : "#ffffff",
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { color: ink, boxWidth: 10, usePointStyle: true },
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.label}: ${this.fmt(ctx.parsed)}`,
                            },
                        },
                    },
                },
            });
        }
    }
}

registry.category("actions").add("sm_pos_dashboard.dashboard", SmPosDashboard);
