# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    tandi_xml_imported = fields.Boolean(
        string="Ecuador XML imported invoice?",
        help="This field is used to identify Ecuadorian XML imported invoices",
        default=False
    )
    tandi_xml_import_validation = fields.Char(
        string="XML imported invoice Warning message validation",
        compute="_compute_tandi_xml_import_validation",
        precompute=True,
        help="Warning message when invoice has been imported from XML",
    )

    def _post(self, soft=True):
        # Inherit of the function from account.move to validate that invoice does not contain
        # provisional product move lines
        if self.env.company.country_id.code == "EC":
            provisional_prod = self.env.ref('tandi_custom.provisional_product_import')
            for invoice in self:
                provisional_prod_lines = self.invoice_line_ids.filtered(
                    lambda line: line.product_id.id == provisional_prod.id)
                if provisional_prod_lines:
                    raise ValidationError(
                        _("""Document: %s has Provisional product on it's invoice lines, 
                        you need to change that to an appropriate product""" % invoice.name)
                    )
        return super()._post(soft)

    @api.depends('state')
    def _compute_tandi_xml_import_validation(self):
        # Method to compute imported warning message
        for move in self:
            move.tandi_xml_import_validation = False
            if move.tandi_xml_imported and move.state == 'draft':
                move.tandi_xml_import_validation = _(
                    "This invoice has been imported from an XML, take the following considerations: \n"
                    "Invoice was loaded without taxes (IVA), so totals may change when provisional "
                    "product gets updated. "
                    "Change default provisional products upon invoice posting.")
