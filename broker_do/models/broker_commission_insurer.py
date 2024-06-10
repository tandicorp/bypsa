# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command


class BrokerCommissionInsurer(models.Model):
    _name = "broker.commission.insurer"
    _description = """Comisiones con aseguradoras"""
    # _order = "insurer_id.name, date_start"

    name = fields.Char(
        string="Contrato de agenciamiento",
        store=True,
        compute="_compute_name"
    )
    insurer_id = fields.Many2one(
        'res.partner',
        required="1",
        string='Aseguradora'
    )
    commission_line_ids = fields.One2many(
        'broker.commission.insurer.line',
        'agreements_id',
        string='Comisiones Aseguradora'
    )
    date_start = fields.Date(
        'Fecha de inicio'
    )
    date_end = fields.Date(
        'Fecha de fin'
    )
    active = fields.Boolean(
        'Activo',
        default=True
    )

    @api.depends("insurer_id", "date_start", "date_end")
    def _compute_name(self):
        for this in self:
            insurer_name = this.insurer_id and this.insurer_id.name or ""
            year_start = this.date_start and this.date_start.year or ''
            year_end = this.date_end and this.date_end.year or ''
            this.name = "{} - [{} / {}]".format(insurer_name, year_start, year_end)

    @api.onchange("commission_line_ids")
    def _onchange_lines(self):
        branches = set(self.commission_line_ids.mapped('branch_id').filtered(lambda br: br.coverage_groups))
        res = {}
        for branch in branches:
            res.update({
                branch.id: [group.id for group in branch.coverage_groups]
            })
        lines = []
        for this in self.commission_line_ids.filtered(lambda cm: cm.branch_id.coverage_groups):
            if res.get(this.branch_id.id):
                if this.coverage_group_id:
                    res.get(this.branch_id.id).remove(this.coverage_group_id.id)
                else:
                    if len(res.get(this.branch_id.id)) > 0:
                        this.coverage_group_id = res.get(this.branch_id.id)[0]
                        res.get(this.branch_id.id).pop(0)
        for key, values in res.items():
            if values:
                for value in values:
                    lines.append(Command.create({
                        "branch_id": key,
                        "coverage_group_id": value
                    }))
        self.commission_line_ids = lines


class BrokerCommissionInsurerLine(models.Model):
    _name = "broker.commission.insurer.line"
    _order = "branch_id asc, coverage_group_id asc"

    agreements_id = fields.Many2one(
        'broker.commission.insurer',
        string='Comisiones con aseguradoras'
    )
    percentage_fee = fields.Float(
        string="Porcentaje de Prima Neta",
        default=1
    )
    coverage_group_id = fields.Many2one(
        "coverage.group",
        string="Grupo de Cobertura"
    )
    percentage_value = fields.Float(
        'Porcentaje comisión',
        required=True,
        default=0
    )
    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo de seguros',
        required=True
    )
    comments = fields.Text(
        'Observaciones'
    )

    @api.onchange('percentage_value')
    def _onchange_percentage(self):
        for this in self:
            if this.percentage_value < 0:
                this.percentage_value = 0
            if this.percentage_value > 1:
                this.percentage_value = 1
