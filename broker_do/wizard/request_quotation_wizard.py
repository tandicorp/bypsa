from odoo import models, api, fields


class RequestQuotationWizard(models.Model):
    _name = 'request.quotation.wizard'
    _description = 'Wizard para ayudar'

    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado"
    )
    insurer_ids = fields.Many2many(
        'res.partner',
        string='Aseguradora',
    )

    def send_emails(self):
        mail_template = self.env.ref('broker_do.mail_template_send_email_request_quotation')
        emails = ','.join(insurer.email for insurer in self.insurer_ids)
        email_values = {
            'email_to': emails
        }
        mail_template.send_mail(self.object_id.id, force_send=True, email_values=email_values)
