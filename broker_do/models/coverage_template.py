# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError


class CoverageTemplate(models.Model):
    _name = "coverage.template"
    _description = """Plantilla comercial por ramo"""

    @api.depends("branch_id", "short_name")
    def _compute_name(self):
        for this in self:
            branch_name = this.branch_id.name if this.branch_id else ""
            short_name = this.short_name if this.short_name else ""
            this.name = "{branch_name} - {short_name}".format(branch_name=branch_name,
                                                              short_name=short_name)

    name = fields.Char(
        string="Nombre",
        readonly=True,
        compute="_compute_name"
    )
    short_name = fields.Char(
        string="Nombre Corto"
    )
    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo de seguros',
        required=True
    )
    active = fields.Boolean(
        default=True,
        string="Activo",
        help="Permite activar o deshabilitar la plantilla de cobertura"
    )
    coverage_line_ids = fields.One2many(
        'coverage.template.line',
        'coverage_id',
        string='Características'
    )
    default = fields.Boolean(
        string="Predeterminado",
        default=False
    )

    @api.constrains('active', 'branch_id', 'default')
    def _check_active_branch(self):
        for coverage in self:
            templates = self.search([('branch_id', '=', coverage.branch_id.id)], limit=1)
            if coverage.active and coverage.default and templates:
                if templates.filtered(lambda cove: cove.active and cove.default) and not coverage.id == templates.id:
                    raise ValidationError(
                        "Error no se puede tener dos plantillas activas por defecto con el mismo Ramo")

    @api.onchange("coverage_line_ids")
    def _onchange_line_sequence(self):
        line_id = None
        for coverage in self:
            line_order = sorted(coverage.coverage_line_ids, key=lambda x: x.sequence, reverse=False)
            for line in line_order:
                if line.display_type == 'line_section':
                    line_id = line.id
                else:
                    line.title_line = line_id

    def unlink(self):
        self.coverage_line_ids.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        for tmp in templates:
            tmp._onchange_line_sequence()
        return templates

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            "default": False,
            "short_name": self.short_name + "-custom"
        })
        coverage = super(CoverageTemplate, self).copy(default=default)
        list_lines = []
        for line in self.coverage_line_ids:
            list_lines.append(Command.create({
                "sequence": line.sequence,
                "display_type": line.display_type,
                "name": line.name,
                "field": line.field,
                "internal": line.internal,
                "is_amount_fee": line.is_amount_fee,
                "is_coverage": line.is_coverage,
                "is_deductible": line.is_deductible,
                "tooltip": line.tooltip,
                "is_limit": line.is_limit,
            }))
        coverage.coverage_line_ids = list_lines
        coverage._onchange_line_sequence()
        return coverage


class CoverageTemplateLine(models.Model):
    _name = "coverage.template.line"
    order = "sequence asc"

    sequence = fields.Integer(
        string='Secuencia',
        default=lambda x: int(x.id)
    )
    display_type = fields.Selection(
        selection=[
            ('line_section', "Título"),
            ('attribute', 'Atributo')
        ],
        default=False)
    name = fields.Char(
        string='Título',
        required=False
    )
    field = fields.Char(
        string='Atributo',
        required=False
    )
    coverage_id = fields.Many2one(
        'coverage.template',
        ondelete='cascade',
        string='Plantilla de coberturas'
    )
    internal = fields.Boolean(
        u'¿Editable?',
        default=False
    )
    title_line = fields.Many2one(
        'coverage.template.line',
        string="Padre"
    )
    is_amount_fee = fields.Boolean(
        string=u"¿Prima Neta?",
        default=False
    )
    is_coverage = fields.Boolean(
        string="¿Cobertura?",
        default=False
    )
    is_deductible = fields.Boolean(
        string="¿Deducible?",
        default=False
    )
    is_limit = fields.Boolean(
        string="¿Límite?",
        default=False
    )
    tooltip = fields.Text(
        string="Sugerencia"
    )
    visible = fields.Boolean(
        string="Visible?",
        default=True
    )

    @api.onchange("is_coverage")
    def _onchange_is_coverage(self):
        if self.is_coverage:
            self.internal = True
            self.is_amount_fee = True
        else:
            self.internal = False
            self.is_amount_fee = False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(CoverageTemplateLine, self).create(vals_list)
        agreement_obj = self.env['agreements.insurer']
        agreement_line_obj = self.env['agreements.insurer.line']
        for line in lines:
            agreements = agreement_obj.search([('coverage_id', '=', line.coverage_id.id)])
            for agre in agreements:
                agreement_line_obj.create({
                    "coverage_line_id": line.id,
                    "agreements_id": agre.id,
                })
        return lines


class TemplateLeadLine(models.Model):
    _name = 'template.lead.line'
    _inherits = {'coverage.template.line': 'template_line_id'}
    _order = "sequence asc"

    template_line_id = fields.Many2one(
        'coverage.template.line',
        'Líneas de la Plantilla de Cobertura',
        auto_join=True,
        index=True,
        required=True,
        ondelete='cascade'
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto asegurado",
        ondelete='cascade'
    )
    visible = fields.Boolean(
        string="Visible?",
        default=True
    )
