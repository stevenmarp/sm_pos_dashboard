# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta

import pytz

from odoo import api, fields, models

PERIOD_DAYS = {"today": 1, "7d": 7, "30d": 30}


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self.env["bus.bus"]._sendone("sm_pos_dashboard", "SM_POS_DASH_UPDATE", {})
        return res

    def _sm_dash_orders(self, start_utc, end_utc):
        return self.search([
            ("date_order", ">=", start_utc),
            ("date_order", "<", end_utc),
            ("state", "in", ["paid", "done", "invoiced"]),
        ])

    @api.model
    def sm_dashboard_data(self, period="today"):
        """POS activity for the dashboard, aggregated over the period."""
        days = PERIOD_DAYS.get(period, 1)
        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_local = fields.Datetime.now().astimezone(tz)
        today = now_local.date()
        start_day = today - timedelta(days=days - 1)

        def to_utc(local_date):
            local_dt = tz.localize(
                fields.Datetime.to_datetime(local_date.strftime("%Y-%m-%d")))
            return local_dt.astimezone(pytz.utc).replace(tzinfo=None)

        start_utc = to_utc(start_day)
        end_utc = to_utc(today + timedelta(days=1))
        prev_start_utc = to_utc(start_day - timedelta(days=days))

        orders = self._sm_dash_orders(start_utc, end_utc)
        prev_orders = self._sm_dash_orders(prev_start_utc, start_utc)

        currency = self.env.company.currency_id
        revenue = sum(orders.mapped("amount_total"))
        count = len(orders)
        avg = revenue / count if count else 0.0
        prev_revenue = sum(prev_orders.mapped("amount_total"))
        prev_count = len(prev_orders)
        prev_avg = prev_revenue / prev_count if prev_count else 0.0

        def trend(cur, prev):
            if not prev:
                return None
            return round((cur - prev) / prev * 100, 1)

        per_config = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
        products = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0})
        payments = defaultdict(float)
        recent = []

        if days == 1:
            series_labels = [f"{h:02d}" for h in range(24)]
            series_values = [0.0] * 24
        else:
            series_dates = [start_day + timedelta(days=i) for i in range(days)]
            series_labels = [d.strftime("%d/%m") for d in series_dates]
            series_values = [0.0] * days

        for order in orders:
            cfg = order.config_id.display_name
            per_config[cfg]["revenue"] += order.amount_total
            per_config[cfg]["orders"] += 1
            local_dt = pytz.utc.localize(order.date_order).astimezone(tz)
            if days == 1:
                series_values[local_dt.hour] += order.amount_total
            else:
                idx = (local_dt.date() - start_day).days
                if 0 <= idx < days:
                    series_values[idx] += order.amount_total
            for line in order.lines:
                name = line.full_product_name or line.product_id.display_name
                products[name]["qty"] += line.qty
                products[name]["revenue"] += line.price_subtotal_incl
            for payment in order.payment_ids:
                payments[payment.payment_method_id.name] += payment.amount

        for order in orders.sorted("date_order", reverse=True)[:10]:
            recent.append({
                "name": order.pos_reference or order.name,
                "config": order.config_id.display_name,
                "amount": order.amount_total,
                "time": pytz.utc.localize(order.date_order)
                        .astimezone(tz).strftime("%d/%m %H:%M"),
            })

        top_products = sorted(
            ({"name": k, **v} for k, v in products.items()),
            key=lambda p: p["revenue"], reverse=True)[:10]

        return {
            "period": period,
            "currency_symbol": currency.symbol,
            "currency_position": currency.position,
            "date": now_local.strftime("%d/%m/%Y %H:%M"),
            "revenue": revenue,
            "orders": count,
            "avg_ticket": avg,
            "open_sessions": self.env["pos.session"].search_count(
                [("state", "=", "opened")]),
            "trend_revenue": trend(revenue, prev_revenue),
            "trend_orders": trend(count, prev_count),
            "trend_avg": trend(avg, prev_avg),
            "series_labels": series_labels,
            "series_values": series_values,
            "per_config": [
                {"name": k, **v} for k, v in sorted(
                    per_config.items(), key=lambda i: i[1]["revenue"],
                    reverse=True)
            ],
            "top_products": top_products,
            "payments": [
                {"name": k, "amount": v} for k, v in sorted(
                    payments.items(), key=lambda i: i[1], reverse=True)
            ],
            "recent": recent,
        }
