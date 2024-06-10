# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    broker_account_insurer_payment_id = fields.Many2one(
        related='company_id.broker_account_insurer_payment_id',
        readonly=False,
    )
    broker_journal_insurer_payment_id = fields.Many2one(
        related='company_id.broker_journal_insurer_payment_id',
        readonly=False,
    )
    percent_commission_special = fields.Float(
        related='company_id.percent_commission_special',
        readonly=False,
    )
    tax_insurance_peasant_id = fields.Many2one(
        related='company_id.tax_insurance_peasant_id',
        readonly=False,
    )
    tax_super_cias_id = fields.Many2one(
        related='company_id.tax_super_cias_id',
        readonly=False,
    )
