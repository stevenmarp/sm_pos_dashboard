# -*- coding: utf-8 -*-
{
    "name": "POS Dashboard | POS Live Dashboard",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Realtime owner dashboard for all your points of sale: live revenue, orders, top products, payment mix on one screen",
    "description": """
POS Live Dashboard
==================

One screen for the owner: what every point of sale is doing right now.

* Today's revenue, order count, average ticket and open sessions
* Updates live over the Odoo bus the moment an order is paid
* Hourly revenue chart of the day
* Breakdown per point of sale
* Top selling products of the day
* Payment method mix
* No configuration: install and open Point of Sale - Live Dashboard
    """,
    "author": "Steven Marp",
    "website": "https://apps.odoo.com/apps/modules/browse?author=Steven Marp",
    "license": "OPL-1",
    "images": ["static/description/banner.gif"],
    "depends": ["point_of_sale"],
    "data": [
        "views/dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sm_pos_dashboard/static/src/dashboard/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "price": 69.80,
    "currency": "USD",
}
