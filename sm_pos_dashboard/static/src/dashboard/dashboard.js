/** @odoo-module **/

import { Component, onWillStart, onWillDestroy, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SmPosDashboard extends Component {
    static template = "sm_pos_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.busService = useService("bus_service");
        this.state = useState({ data: null });
        this.destroyed = false;

        onWillStart(() => this.load());
        this.busService.addChannel("sm_pos_dashboard");
        this.busService.subscribe("SM_POS_DASH_UPDATE", () => this.scheduleLoad());
        onWillDestroy(() => {
            this.destroyed = true;
            clearTimeout(this.loadTimeout);
        });
    }

    async load() {
        if (this.destroyed) {
            return;
        }
        this.state.data = await this.orm.call("pos.order", "sm_dashboard_data", []);
    }

    scheduleLoad() {
        clearTimeout(this.loadTimeout);
        this.loadTimeout = setTimeout(() => this.load(), 500);
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

    get maxHourly() {
        return Math.max(...this.state.data.hourly, 0.01);
    }

    get maxHourIndex() {
        const h = this.state.data.hourly;
        return h.indexOf(Math.max(...h));
    }

    get maxProductRevenue() {
        const tops = this.state.data.top_products;
        return tops.length ? tops[0].revenue : 0.01;
    }

    get totalPayments() {
        return this.state.data.payments.reduce((s, p) => s + p.amount, 0) || 0.01;
    }
}

registry.category("actions").add("sm_pos_dashboard.dashboard", SmPosDashboard);
