# -*- coding: utf-8 -*-
from odoo import models, api, fields, Command, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ec_is_purchase_liquidation = fields.Boolean(
        related='journal_id.l10n_ec_is_purchase_liquidation',
        string="Purchase Liquidation",
        help="Check if this move is a purchase liquidation"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.company.country_id.code == "EC" and 'invoice_line_ids' in vals:
                contrib_included_line_ids = self._l10n_ec_compute_contribution_lines(
                    create_vals=vals.get('invoice_line_ids'))
                vals['invoice_line_ids'] = contrib_included_line_ids if contrib_included_line_ids else vals[
                    'invoice_line_ids']
        return super().create(vals_list)

    def write(self, vals):
        if self.env.company.country_id.code == "EC" and 'invoice_line_ids' in vals:
            contrib_included_line_ids = self._l10n_ec_compute_contribution_lines(
                write_vals=vals.get('invoice_line_ids'))
            vals['invoice_line_ids'] = contrib_included_line_ids if contrib_included_line_ids else vals[
                'invoice_line_ids']
        return super().write(vals)

    def is_invoice(self, include_receipts=False):
        '''
        Account move original method inherited to include Ecuadorian Purchase Liquidations for email sending.
        '''
        res = super().is_invoice(include_receipts)
        if self.env.company.country_id.code == "EC":
            return self.is_sale_document(include_receipts) or self.is_purchase_document(
                include_receipts) or self.l10n_ec_is_purchase_liquidation
        return res

    @api.constrains('l10n_ec_authorization_number')
    def _check_l10n_ec_authorization_number(self):
        for move in self:
            if self.env.company.country_id.code == "EC" and move.move_type in ['in_invoice',
                                                                               'in_refund'] and move.l10n_ec_authorization_number:
                if len(move.l10n_ec_authorization_number) not in [10, 35, 49]:
                    raise UserError(_(u"El número de autorización debe tener 10, 35 o 49 dígitos"))
                if not move.l10n_ec_authorization_number.isnumeric():
                    raise UserError(_(u"El número de autorización debe ser un valor numérico"))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def _l10n_ec_compute_contribution_lines(self, create_vals=None, write_vals=None):
        # In Ecuador, Insurance Companies have to withhold specific amounts based on the values of the Insurance Premium called contributions
        # As these values are not "taxes" (even if it works similar as a tax) these values have to be part of Invoice details
        product_obj = self.env['product.product']
        move_line_obj = self.env['account.move.line']
        # First we evaluate if it is a create or write operation
        line_vals_list, return_vals_list = [], []
        if create_vals:
            line_vals_list = create_vals.copy()
            return_vals_list = create_vals.copy()
        elif write_vals:
            line_vals_list = write_vals.copy()
            return_vals_list = write_vals.copy()
        # We delete contribution products lines from list to return, to recompute them after
        for index, line_vals in enumerate(line_vals_list):
            product = product_obj.browse(line_vals[2].get('product_id')) if (
                        create_vals or (write_vals and isinstance(line_vals[1], str))) else move_line_obj.browse(
                line_vals[1]).product_id
            if product.is_contribution:
                if create_vals:
                    return_vals_list.remove(line_vals)
                else:
                    return_vals_list[index][0] = 2
                line_vals_list.remove(line_vals)
        vals = {}
        for contribution_line in line_vals_list:
            changed_values = contribution_line[2] if (write_vals and contribution_line[2]) else dict()
            contribution_line_vals = contribution_line[2] if create_vals else move_line_obj.browse(contribution_line[1])
            if create_vals:
                product = product_obj.browse(contribution_line_vals.get('product_id'))
            elif write_vals:
                product = product_obj.browse(changed_values.get(
                    'product_id')) if 'product_id' in changed_values else contribution_line_vals.product_id
            if product.contribution_product_ids:
                for contrib_product in product.contribution_product_ids:
                    if create_vals:
                        qty = contribution_line_vals.get('quantity')
                        price_unit = contribution_line_vals.get('price_unit')
                    elif write_vals:
                        qty = changed_values.get(
                            'quantity') if 'quantity' in changed_values else contribution_line_vals.quantity
                        price_unit = changed_values.get(
                            'price_unit') if 'price_unit' in changed_values else contribution_line_vals.price_unit
                    line_subtotal = qty * price_unit
                    amount = line_subtotal * (contrib_product.contrib_percent / 100)
                    if vals.get(contrib_product.id, False):
                        vals[contrib_product.id] += amount
                    else:
                        vals.update({
                            contrib_product.id: amount
                        })
            for contrib_product_id, value in vals.items():
                contrib_product = product_obj.browse(contrib_product_id)
                contrib_line_values = {
                    'product_id': contrib_product_id,
                    'quantity': 1,
                    'price_unit': value,
                    'tax_ids': [Command.set([tax.id for tax in contrib_product.taxes_id])],
                }
                contrib_line = Command.create(contrib_line_values)
                return_vals_list.append(contrib_line)
        return return_vals_list

    def _l10n_ec_get_invoice_additional_info(self):
        '''
        Overrides l10n_ec_edi method and deletes unnecessary data from PDF EDI reports
        '''
        return {
            "Referencia": self.name  # Reference
        }

    def _l10n_ec_get_move_common_domain(self):
        '''
        Method to get domain for automated authorized email sending, can be inherited to add conditions
        '''
        common_domain = [
            ("state", "=", "posted"),
            ("is_move_sent", "=", False),
            ("l10n_ec_authorization_date", "!=", False)
        ]
        return common_domain

    @api.model
    def l10n_ec_send_mail_to_partner(self, limit=100):
        '''
        Send EDI authorized documents via email to partner
        '''
        common_domain = self._l10n_ec_get_move_common_domain()
        account_moves = self.env["account.move"].search(
            common_domain
            + [
                ("partner_id.vat", "not in", ["9999999999999", "9999999999"]),
            ],
            limit=limit
        )
        for account_move in account_moves:
            account_move.l10n_ec_send_email()

        # Update documents with final consumer
        account_moves_with_final_consumer = self.env["account.move"].search(
            common_domain
            + [
                ("partner_id.vat", "in", ["9999999999999", "9999999999"]),
            ]
        )
        account_moves_with_final_consumer.write({"is_move_sent": True})

    def l10n_ec_send_email(self):
        '''
        Creates an account.invoice.send or mail.compose.message instance to send the email of the corresponding invoice/withhold
        '''
        self.ensure_one()
        if self.is_invoice(include_receipts=True):
            # If account.move object is an invoice we use default account.invoice.send method
            WizardInvoiceSent = self.env["account.invoice.send"]
            res = self.with_context(discard_logo_check=True).action_invoice_sent()
            context = res["context"]
            send_mail = WizardInvoiceSent.with_context(**context).create({})
            # Send email simulating onchange methods
            send_mail.onchange_template_id()
            send_mail.send_and_print_action()
        else:
            # If account.move object is not an invoice or credit note we assume it is a withhold, then we use localization compose mail method
            WizardWithholdSent = self.env["mail.compose.message"]
            res = self.l10n_ec_action_send_withhold()
            context = res["context"]
            send_mail = WizardWithholdSent.with_context(**context).create({})
            send_mail.action_send_mail()
            self.write({'is_move_sent': True})
