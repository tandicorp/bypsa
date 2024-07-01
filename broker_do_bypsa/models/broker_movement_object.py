from odoo import fields, models, api


class BrokerMovementObject(models.Model):
    _inherit = 'broker.movement.object'

    depreciation_id = fields.Many2one(
        "broker.depreciation",
        string="Depreciación"
    )

    @api.onchange("name")
    def _onchange_name_depreciation(self):
        depreciation_obj = self.env['broker.depreciation']
        for this in self:
            depreciation_id = depreciation_obj.search([
                ("model_ids.name","ilike", this.name)
            ])
            if depreciation_id:
                this.depreciation_id =  depreciation_id[0]



