# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from dateutil.relativedelta import relativedelta


class BrokerContract(models.Model):
    _inherit = 'broker.contract'

    num_insured_items = fields.Integer(
        string="No. Items asegurados",
        compute="_compute_items_num",
        tracking=True
    )

    @api.depends("branch_id", "contract_num", "annex_num")
    def _compute_name(self):
        for this in self:
            branch_code = this.branch_id and this.branch_id.code or ""
            contract_num = this.contract_num or ''
            this.name = " - ".join([x for x in [branch_code, contract_num, str(this.annex_num) or ''] if x])

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start + relativedelta(months=12)
            type = self.env.ref("broker_do.policy_movement")
            for line in self.movement_ids.filtered(lambda x: x.type_id.id == type.id):
                line.date_start = self.date_start
                line.date_end = self.date_end

    def _compute_items_num(self):
        """Numero de items dentro de la poliza"""
        for record in self:
            record.num_insured_items = len(record.contract_object_ids or [])
