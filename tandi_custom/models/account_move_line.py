# -*- coding: utf-8 -*-
from odoo import models, api, fields, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # -------------------------------------------------------------------------
    # ACCOUNT MOVE LINE OVERRIDDEN METHODS TO AVOID PRODUCT UPDATE MODIFICATIONS
    # -------------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_name(self):
        if True not in self.mapped('move_id').mapped('tandi_xml_imported'):
            super(AccountMoveLine, self)._compute_name()

    @api.depends('display_type')
    def _compute_quantity(self):
        if True not in self.mapped('move_id').mapped('tandi_xml_imported'):
            super(AccountMoveLine, self)._compute_quantity()

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        if True not in self.mapped('move_id').mapped('tandi_xml_imported'):
            super(AccountMoveLine, self)._compute_price_unit()