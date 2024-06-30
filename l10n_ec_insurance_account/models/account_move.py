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

    def _post(self, soft=True):
        # Inherit of the function from account.move to compute Ecuadorian Insurance Companies contributions
        if self.env.company.country_id.code == "EC":
            for invoice in self:
                invoice._l10n_ec_compute_contribution_lines()
        return super()._post(soft)

    def is_invoice(self, include_receipts=False):
        """
        Account move original method inherited to include Ecuadorian Purchase Liquidations for email sending.
        """
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

    def _l10n_ec_compute_contribution_lines(self):
        """
        Method that computes new contribution invoice line based on (price * qty) * contrib_percent(of the contrib prod)
        of each line that has a product with contribution_product_ids set.
        """
        # In Ecuador, Insurance Companies have to withhold specific amounts based on the values of the Insurance Premium
        # called contributions, as these values are not "taxes" (even if it works similar to a tax) these values have to
        # be part of Invoice lines
        product_obj = self.env['product.product']
        # We delete contribution products lines (if exist) to recompute them after
        for contribution_line in self.invoice_line_ids.filtered(lambda line: line.product_id.is_contribution):
            contribution_line.unlink()

        vals = {}
        # Iter over contribution applying product lines to compute its contribution lines for adding them to invoice
        # Group contribution products in a dict to iter over it then
        for line in self.invoice_line_ids.filtered(lambda line: line.product_id.contribution_product_ids):
            for contrib_product in line.product_id.contribution_product_ids:
                line_subtotal = line.quantity * line.price_unit
                amount = line_subtotal * (contrib_product.contrib_percent / 100)
                if vals.get(contrib_product.id, False):
                    vals[contrib_product.id] += amount
                else:
                    vals.update({
                        contrib_product.id: amount
                    })
        contrib_line_list = []
        # Iter over dict that has contribution product id as key and amount as value, used to create contribution lines
        for contrib_product_id, value in vals.items():
            contrib_product = product_obj.search([('product_tmpl_id', '=', contrib_product_id)], limit=1)
            contrib_line_values = {
                'product_id': contrib_product.id,
                'quantity': 1,
                'price_unit': value,
                'tax_ids': [Command.set([tax.id for tax in contrib_product.taxes_id])],
            }
            contrib_line = Command.create(contrib_line_values)
            contrib_line_list.append(contrib_line)
        if contrib_line_list:
            self.write({
                'invoice_line_ids': contrib_line_list
            })

    def _l10n_ec_get_invoice_additional_info(self):
        """
        Overrides l10n_ec_edi method and deletes unnecessary data from PDF EDI reports
        """
        return {
            "Referencia": self.name  # Reference
        }

    def _l10n_ec_get_move_common_domain(self):
        """
        Method to get domain for automated authorized email sending, can be inherited to add conditions
        """
        common_domain = [
            ("state", "=", "posted"),
            ("is_move_sent", "=", False),
            ("l10n_ec_authorization_date", "!=", False)
        ]
        return common_domain

    @api.model
    def l10n_ec_send_mail_to_partner(self, limit=100):
        """
        Send EDI authorized documents via email to partner
        """
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
        """
        Creates an account.invoice.send or mail.compose.message instance to send the email of the corresponding
        invoice/withhold
        """
        self.ensure_one()
        self.env = self.env(user=self.invoice_user_id) if self.invoice_user_id else self.env(user=self.env.user)
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
            # If account.move object is not an invoice or credit note we assume it is a withhold, then we use
            # localization compose mail method
            WizardWithholdSent = self.env["mail.compose.message"]
            res = self.l10n_ec_action_send_withhold()
            context = res["context"]
            send_mail = WizardWithholdSent.with_context(**context).create({})
            send_mail.action_send_mail()
            self.write({'is_move_sent': True})
