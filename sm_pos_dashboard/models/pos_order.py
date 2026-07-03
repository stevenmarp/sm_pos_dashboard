# -*- coding: utf-8 -*-
from collections import defaultdict

import pytz

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self.env["bus.bus"]._sendone("sm_pos_dashboard", "SM_POS_DASH_UPDATE", {})
        return res

    @api.model
    def sm_dashboard_data(self):
        """Today's POS activity, aggregated for the live dashboard."""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        today = fields.Datetime.now().astimezone(tz).date()
        start_local = tz.localize(
            fields.Datetime.to_datetime(today.strftime("%Y-%m-%d")))
        start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)

        orders = self.search([
            ("date_order", ">=", start_utc),
            ("state", "in", ["paid", "done", "invoiced"]),
        ])

        currency = self.env.company.currency_id
        revenue = sum(orders.mapped("amount_total"))
        count = len(orders)

        per_config = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
        hourly = [0.0] * 24
        products = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0})
        payments = defaultdict(float)
        recent = []

        for order in orders:
            cfg = order.config_id.display_name
            per_config[cfg]["revenue"] += order.amount_total
            per_config[cfg]["orders"] += 1
            local_dt = pytz.utc.localize(order.date_order).astimezone(tz)
            hourly[local_dt.hour] += order.amount_total
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
                        .astimezone(tz).strftime("%H:%M"),
            })

        top_products = sorted(
            ({"name": k, **v} for k, v in products.items()),
            key=lambda p: p["revenue"], reverse=True)[:10]

        return {
            "currency_symbol": currency.symbol,
            "currency_position": currency.position,
            "date": today.strftime("%d/%m/%Y"),
            "revenue": revenue,
            "orders": count,
            "avg_ticket": revenue / count if count else 0.0,
            "open_sessions": self.env["pos.session"].search_count(
                [("state", "=", "opened")]),
            "per_config": [
                {"name": k, **v} for k, v in sorted(
                    per_config.items(), key=lambda i: i[1]["revenue"],
                    reverse=True)
            ],
            "hourly": hourly,
            "top_products": top_products,
            "payments": [
                {"name": k, "amount": v} for k, v in sorted(
                    payments.items(), key=lambda i: i[1], reverse=True)
            ],
            "recent": recent,
        }
