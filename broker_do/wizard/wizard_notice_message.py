# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


class WizardNoticeMessage(models.TransientModel):
    _name = 'wizard.notice.message'

    message = fields.Text(
        string="Mensaje alerta"
    )

    def action_confirm(self):
        claim_notice_id = self.env.context.get('claim_notice_id')
        if claim_notice_id:
            self.env['broker.claim.notice'].browse(claim_notice_id).create_new_claim()
        claim_id = self.env.context.get('claim_id')
        if claim_id:
            self.env['broker.claim'].browse(claim_id).write({
                'reject_note': self.message,
                'state': 'rejected'
            })
