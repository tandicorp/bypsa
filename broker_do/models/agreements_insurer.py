# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from itertools import groupby


def is_numeric_value(value):
    if value:
        return value.replace('.', '', 1).isdigit() or value.replace(',', '', 1).isdigit()
    return False


class AgreementsInsurer(models.Model):
    _name = "agreements.insurer"
    _description = """Acuerdos con aseguradoras"""
    _order = "default"

    @api.depends("insurer_id", "coverage_id", "short_name")
    def _compute_name(self):
        for this in self:
            insurer_name = this.insurer_id.name if this.insurer_id else ""
            coverage_name = this.coverage_id.name if this.coverage_id else ""
            short_name = this.short_name if this.short_name else ""
            this.name = "{insurer_name} - {coverage_name} - {short_name}".format(insurer_name=insurer_name,
                                                                                 coverage_name=coverage_name,
                                                                                 short_name=short_name)

    name = fields.Char(
        string="Nombre",
        readonly=True,
        compute="_compute_name"
    )
    short_name = fields.Char(
        string="Nombre Corto"
    )
    insurer_id = fields.Many2one(
        'res.partner',
        string='Aseguradora',
    )
    coverage_id = fields.Many2one(
        'coverage.template',
        string='Plantilla de coberturas',
        required=True
    )
    agreements_line_ids = fields.One2many(
        'agreements.insurer.line',
        'agreements_id',
        string='Acuerdos Aseguradora'
    )
    contract_id = fields.Many2one(
        "broker.contract",
        string="Contrato Asociado"
    )
    default = fields.Boolean(
        string="¿Es producto cerrado?",
        default=False
    )
    amount_fee = fields.Float(
        string="Prima Neta",
        compute="get_amount_fee"
    )
    base_product_id = fields.Many2one(
        "agreements.insurer",
        string="Acuerdo Base"
    )
    is_quotation = fields.Boolean(
        string="Es Cotización?",
        default=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        agreement_object_obj = self.env['movement.object.agreement'].sudo()
        agreements = super().create(vals_list)
        list_object = []
        if self.env.context.get("object_id") and self.env.context.get("lead_id"):
            for agree in agreements:
                res = {
                    "agreement_id": agree.id,
                    "object_id": self.env.context.get("object_id"),
                    "state": "draft",
                }
                list_object.append(res)
            agreement_object_obj.create(list_object)
            params = {
                "default_identification": self.env.context.get("object_id")
            }
        return agreements

    @api.depends("agreements_line_ids")
    def get_amount_fee(self):
        value = False
        if self.agreements_line_ids:
            values = self.agreements_line_ids.filtered(
                lambda line: line.is_amount_fee and is_numeric_value(line.value)).mapped("value")
            value = sum([float(val) for val in values])
        self.amount_fee = value

    @api.onchange("coverage_id")
    def _onchange_coverage(self):
        for this in self:
            for line in this.agreements_line_ids:
                line.unlink()
            list_lines = []
            coverage_lines = this.coverage_id.coverage_line_ids
            if coverage_lines:
                line_order = sorted(coverage_lines, key=lambda x: x.sequence, reverse=False)
                for line in line_order:
                    list_lines.append(fields.Command.create({
                        "field": line.field,
                        "sequence": line.sequence,
                        "name": line.name,
                        "display_type": line.display_type,
                        "name_title": line.title_line.id if line.title_line else None,
                        "coverage_line_id": line.id
                    }))
            this.write({'agreements_line_ids': list_lines})

    def create_data_agreement(self, object_id):
        for this in self:
            data = {
                "nombre": this.name,
                "company": this.insurer_id.id,
                "id": this.id,
            }
            groups = {}
            lines_visible = object_id.coverage_template_id.coverage_line_ids.filtered(lambda tmp: tmp.visible).mapped(
                "id")
            agreements_sorted = sorted(
                this.agreements_line_ids.filtered(
                    lambda l: not l.display_type == 'line_section' and l.coverage_line_id.id in lines_visible),
                key=lambda x: x.sequence)
            for key, group in groupby(agreements_sorted, key=lambda x: x.name_title.name):
                groups[key] = list(group)
            section = []
            for key, groups in groups.items():
                res_section = {
                    "name": key,
                }
                lines = []
                for line in groups:
                    edit = line.coverage_line_id.internal
                    coverage = line.coverage_line_id.is_coverage
                    res = {
                        "value": line.value if line.value else "N/A",
                        "id": line.id,
                        "edit": edit,
                        "rate": line.rate,
                        "amount_insured": line.amount_insured,
                        "coverage": coverage
                    }
                    lines.append(res)
                res_section.update({
                    "line": lines
                })
                section.append(
                    res_section
                )
            data.update({
                "section": section
            })
        return data

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        amount_insured = False
        rate = False
        if default.get("amount_insured"):
            amount_insured = default.get("amount_insured")
        if default.get("rate"):
            rate = default.get("rate")
        default.pop("amount_insured",None)
        default.pop("rate",None)
        coverage_id = self.coverage_id.id if not default.get("coverage_id") else default.get("coverage_id")
        default.update({
            "default": False,
            "short_name": self.short_name,
            "name": self.name,
            "amount_fee": self.amount_fee,
            "insurer_id": self.insurer_id.id,
            "base_product_id": self.id,
            "coverage_id": coverage_id,
        })
        agreement = super(AgreementsInsurer, self).copy(default=default)
        agreement._onchange_coverage()
        lines_origin = self.agreements_line_ids.filtered(lambda line_origin: line_origin.display_type == 'attribute')
        for line in agreement.agreements_line_ids.filtered(lambda line_new: line_new.display_type == 'attribute'):
            line_origin = lines_origin.filtered(lambda l_origin: l_origin.field == line.field)
            if line_origin:
                line.amount_insured = (amount_insured or line_origin[0].amount_insured) if line.is_coverage  else 0.0
                line.rate = (rate * 100 or line_origin[0].rate) if not line.is_limit else 0.0
                line.value = (amount_insured * rate) if line.is_coverage else line_origin[0].value
        return agreement


class AgreementsInsurerLine(models.Model):
    _name = "agreements.insurer.line"

    agreements_id = fields.Many2one(
        'agreements.insurer',
        string='Acuerdo con aseguradoras'
    )
    coverage_line_id = fields.Many2one(
        "coverage.template.line",
        string="Linea de plantilla"
    )
    sequence = fields.Integer(
        related='coverage_line_id.sequence',
        store=True
    )
    display_type = fields.Selection(
        related='coverage_line_id.display_type',
        store=True
    )
    name = fields.Char(
        related='coverage_line_id.name',
        store=True
    )
    field = fields.Char(
        related='coverage_line_id.field',
        store=True
    )
    tooltip = fields.Text(
        related='coverage_line_id.tooltip',
        string="Sugerencia"
    )
    is_amount_fee = fields.Boolean(
        related='coverage_line_id.is_amount_fee',
        store=True
    )
    amount_insured = fields.Float(
        string="Valor Asegurado"
    )
    rate = fields.Char(
        string="Tasa"
    )
    is_coverage = fields.Boolean(
        related='coverage_line_id.is_coverage',
        store=True
    )
    is_deductible = fields.Boolean(
        related='coverage_line_id.is_deductible',
        store=True
    )
    is_limit = fields.Boolean(
        related='coverage_line_id.is_limit',
        store=True
    )
    value = fields.Text(
        'Valor'
    )
    name_title = fields.Many2one(
        related='coverage_line_id.title_line',
        store=True
    )

    def name_get(self):
        result = []
        for record in self:
            name = record.field if record.field else record.name
            result.append((record.id, name))
        return result

    def set_value_line(self, value, field):
        for this in self:
            values = {
                field: value
            }
            this.write(values)
            if field != 'value':
                this.onchange_value()

    @api.onchange("rate", "amount_insured")
    def onchange_value(self):
        if self.rate and is_numeric_value(self.rate):
            value_data = self.amount_insured * (float(
                self.rate.replace(",", ".")) / 100) if self.amount_insured and self.amount_insured > 0 else None
            self.value = round(value_data, 2)
        elif self.rate and not is_numeric_value(self.rate):
            self.value = "SIN COSTO"



