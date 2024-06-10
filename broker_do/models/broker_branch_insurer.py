from odoo import models, api, fields


class BrokerBranchInsurer(models.Model):
    _name = 'broker.branch.insurer'

    @api.depends("branch_id", "insurer_id")
    def _compute_name(self):
        for this in self:
            branch_name = this.branch_id.name if this.branch_id else ""
            insurer_name = this.insurer_id.name if this.insurer_id else ""
            this.name = "{} - {}".format(insurer_name, branch_name)

    name = fields.Char(
        string='Nombre'
    )
    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo'
    )
    insurer_id = fields.Many2one(
        'res.partner',
        string='Aseguradora'
    )
    config_line_ids = fields.One2many(
        "broker.branch.insurer.line",
        "broker_branch_id",
        string="Configuraciones"
    )

    def get_values_config(self):
        """Este método ayuda a obtener los valores para conocer las metas por cumplir y las cumplidas"""
        date_now = fields.Date.today()
        contract_obj = self.env["broker.contract"].sudo()
        branch_insurers = self.search([]).sudo()
        valid_config = branch_insurers.mapped("config_line_ids").filtered(
            lambda line: line.date_from <= date_now <= line.date_to)
        list_config = []
        if valid_config:
            for config in valid_config:
                percent = 0
                res = {
                    "id": config.id,
                    "name": config.broker_branch_id.insurer_id.name,
                    "branch": config.broker_branch_id.branch_id.name,
                    "type": dict(config._fields['type'].selection).get(config.type),
                    "current": 0,
                    "percent": str(round(percent, 2)) + "%",
                    "max": config.value,
                    "color": "bg-danger"
                }
                contracts = contract_obj.search(
                    [('date_start', '>=', config.date_from), ("date_start", "<=", config.date_to),
                     ('state', '=', 'valid')])
                if config.type == 'budget_quantity' and contracts:
                    if len(contracts) > 0 and config.value > 0:
                        percent = (len(contracts) * 100) / config.value
                        percent = 100 if percent > 100 else percent
                        value = len(contracts)
                        res.update({
                            "current": value,
                            "percent": str(round(percent, 2)) + "%",
                        })
                elif config.type == 'budget_amount' and contracts:
                    value_contract = sum(contracts.mapped("movement_ids.amount_fee"))
                    if value_contract > 0 and config.value > 0:
                        percent = (value_contract * 100) / config.value
                        percent = 100 if percent > 100 else percent
                        res.update({
                            "current": value_contract,
                            "percent": str(round(percent, 2)) + "%",
                        })
                if percent < 25:
                    res.update({
                        "color": "bg-danger"
                    })
                elif 25 <= percent < 50:
                    res.update({
                        "color": "bg-warning"
                    })
                elif 50 <= percent < 75:
                    res.update({
                        "color": "bg-info"
                    })
                elif 75 <= percent <= 100:
                    res.update({
                        "color": "bg-success"
                    })
                list_config.append(res)
        return list_config


class BrokerBranchInsurerLine(models.Model):
    _name = 'broker.branch.insurer.line'

    broker_branch_id = fields.Many2one(
        "broker.branch.insurer",
        string="Configuración"
    )

    type = fields.Selection([
        ("budget_quantity", "Presupuesto por Cantidad"),
        ("budget_amount", "Presupuesto por Prima"),
    ], string="Tipo"
    )
    value = fields.Float(
        string="Valor"
    )
    date_from = fields.Date(
        string="Desde"
    )
    date_to = fields.Date(
        string="Hasta"
    )
