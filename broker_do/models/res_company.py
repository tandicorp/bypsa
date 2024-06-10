# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    broker_account_insurer_payment_id = fields.Many2one(
        'account.account',
        string='Cuenta contable para cobros recibidos hacia aseguradoras'
    )
    broker_journal_insurer_payment_id = fields.Many2one(
        'account.journal',
        string='Diario contable para cobros recibidos hacia aseguradoras'
    )
    percent_commission_special = fields.Float(
        string="Porcentaje Comisiones Especiales"
    )
    tax_insurance_peasant_id = fields.Many2one(
        'account.tax',
        string='Impuesto campesino'
    )
    tax_super_cias_id = fields.Many2one(
        'account.tax',
        string='Impuesto super compañías'
    )
