from odoo import models, api, fields


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        res = super(MailComposer, self)._action_send_mail(auto_commit=auto_commit)
        if self.render_model == 'crm.lead' and self.res_id:
            crm = self.env['crm.lead'].browse(self.res_id)
            if crm.stage_id.id == self.env.ref("crm.stage_lead2").id:
                crm.stage_id = self.env.ref("crm.stage_lead3").id
        if self.render_model == 'sale.order' and self.res_id:
            self.env['sale.order'].browse(self.res_id).status = 'insurance_release'
        if self.render_model == 'broker.claim' and self.res_id:
            self.env['broker.claim'].browse(self.res_id).state = 'insurer'
        return res
