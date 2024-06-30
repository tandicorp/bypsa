from odoo import fields, models, api


class AgreementInsurerWizard(models.TransientModel):
    _name = 'agreements.insurer.wizard'
    _description = 'Wizard para la creación de acuerdos'

    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo de seguros',
        required=True
    )
    insurer_ids = fields.Many2many(
        'res.partner',
        string='Aseguradora',
    )
    agreements_line_ids = fields.One2many(
        'agreements.insurer.wizard.line',
        'wizard_id',
        string="Acuerdos"
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado"
    )
    template_id = fields.Many2one(
        "coverage.template",
        string="Plantilla"
    )

    @api.onchange('branch_id', 'insurer_ids')
    def _onchange_branch_insures(self):
        agreements_obj = self.env['agreements.insurer']
        for this in self:
            domain = [('default', '=', True)]
            if this.branch_id:
                domain.append(('coverage_id.branch_id', '=', this.branch_id.id))
            if this.insurer_ids:
                domain.append(('insurer_id', 'in', this.insurer_ids.ids))
            if domain:
                this.agreements_line_ids = False
                agreements = agreements_obj.search(domain)
                list_agreement = []
                for agreement in agreements:
                    check = True
                    if this.object_id.agreements_line_ids:
                        check = False
                    list_agreement.append(fields.Command.create({
                        "agreement_id": agreement.id,
                        "check": check
                    }))
                this.agreements_line_ids = list_agreement

    def create_agreement(self):
        for this in self:
            agreements = this.agreements_line_ids.filtered(lambda line: line.check)
            agreements_uncheck = this.agreements_line_ids.filtered(lambda line: not line.check)
            if agreements_uncheck:
                agreements_uncheck = agreements_uncheck.mapped("agreement_id")
                for agree_id in this.object_id.agreements_line_ids:
                    if agree_id.agreement_id.id in agreements_uncheck.ids:
                        agree_id.unlink()
                        agree_id.agreement_id.unlink()

            if agreements:
                lines = []
                lead_agreement = this.object_id.agreements_line_ids.mapped("agreement_id.base_product_id")
                agreements = agreements.filtered(lambda ag: ag.agreement_id.id not in lead_agreement.ids)
                for agree in agreements:
                    agree_cp = agree.agreement_id.copy(
                        {"coverage_id": this.template_id.id, "amount_insured": this.object_id.amount_insured})
                    lines.append(fields.Command.create({
                        "agreement_id": agree_cp.id
                    }))
                this.object_id.write({'agreements_line_ids': lines})
            params = {
                "default_identification": this.object_id.id,
                "default_template_id": this.template_id.id,
            }
            return {
                'type': 'ir.actions.client',
                'tag': 'broker_do.agreement_compare_action_js',
                'params': params,
                'identification': this.object_id.id,
                'lead_id': this.object_id.lead_id.id or False,
                'template_id': this.template_id.id,
            }


class AgreementsInsurerWizardLine(models.TransientModel):
    _name = 'agreements.insurer.wizard.line'
    _description = 'Líneas de Acuerdos'

    check = fields.Boolean(
        string="Seleccionado",
        default=True
    )
    agreement_id = fields.Many2one(
        "agreements.insurer",
        string="Acuerdo"
    )
    wizard_id = fields.Many2one(
        "agreements.insurer.wizard",
        string="Wizard"
    )
