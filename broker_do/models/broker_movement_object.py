from odoo import models, api, fields
from lxml import etree
from odoo.exceptions import ValidationError
from odoo.addons.broker_do.models.broker_movement_branch import _TYPES
from itertools import groupby
import json
from odoo.tools.misc import xlsxwriter
import io
import base64


class BrokerMovementObject(models.Model):
    _name = 'broker.movement.object'
    _description = 'Objetos Asegurados de Anexo'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nombre'
    )
    # Campos modificatorios
    active = fields.Boolean(
        string="Activo",
        default=True,
    )
    amount = fields.Integer(
        string="Cantidad",
        default=1
    )
    movement_id = fields.Many2one(
        'sale.order',
        string="Anexo"
    )
    contract_id = fields.Many2one(
        'broker.contract',
        string="Contrato",
        store=True
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Modificado",
        help="Nos ayudara a identificar el objeto que se va a excluir"
    )
    parent_object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado Padre"
    )
    # Objeto del contrato
    contract_object_id = fields.Many2one(
        "broker.movement.object",
        string=u"Item pÃ³liza"
    )
    movement_object_ids = fields.One2many(
        "broker.movement.object",
        'contract_object_id',
        string=u"Items generados en mov."
    )
    amount_fee = fields.Float(
        string="Prima Neta",
        default=0.0
    )
    amount_insured = fields.Float(
        string="Valor Asegurado",
        default=0.0
    )
    type = fields.Selection([
        ("normal", "Normal"),
        ("blanket", "Agrupado")
    ], string="Tipo de Objeto Asegurado",
        default="normal",
        required=True
    )
    amount = fields.Integer(
        string="Cantidad",
        default=1
    )
    comment = fields.Text(
        string="ObservaciÃ³n"
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad"
    )
    branch_id = fields.Many2one(
        "broker.branch",
        compute='get_object_branch_id',
        store=True,
        string="Ramo"
    )
    agreements_line_ids = fields.One2many(
        "movement.object.agreement",
        "object_id",
        string="Acuerdos"
    )
    type_id = fields.Many2one(
        related="movement_id.type_id",
        store=True
    )
    movement_branch_id = fields.Many2one(
        "broker.movement.branch",
        string="Ramo de movimiento",
        compute="get_movement_branch",
        store=True
    )
    agreement_id = fields.Many2one(
        "agreements.insurer",
        string="Acuerdo Ganador",
        compute="get_agreement_accept"
    )
    info_line_ids = fields.One2many(
        "broker.movement.object.line",
        "object_id",
        string="InformaciÃ³n Adicional"
    )
    child_line_ids = fields.One2many(
        "broker.movement.object",
        "parent_object_id",
        string="Objetos Asegurados"
    )
    coverage_template_id = fields.Many2one(
        "coverage.template",
        string="Plantilla Asociada"
    )
    deductible_ids = fields.One2many(
        'broker.object.deductible',
        'object_id',
        string="Deducibles"
    )
    data_line_ids = fields.One2many(
        'broker.movement.object.data',
        "object_id",
        string="InformaciÃ³n del Objeto Asegurado"
    )
    rate = fields.Float(
        string="Tasa",
    )

    @api.onchange("lead_id", "movement_id")
    def get_object_branch_id(self):
        """Permite obtener el ramo, dependiendo de donde se genere el objeto asegurado, por lead u contrato"""
        for record in self:
            if record.lead_id:
                record.branch_id = record.lead_id.branch_id.id
            if record.contract_id:
                record.branch_id = record.contract_id.branch_id.id

    @api.depends("agreements_line_ids")
    def get_agreement_accept(self):
        for record in self:
            agreement_id = record.agreements_line_ids.filtered(lambda ag: ag.state == "accept")
            if agreement_id:
                record.agreement_id = agreement_id[0].agreement_id.id
            else:
                record.agreement_id = False

    @api.depends("branch_id")
    def get_movement_branch(self):
        movement_branch_obj = self.env['broker.movement.branch'].sudo()
        type = self.env.ref('broker_do.policy_movement')
        for record in self:
            if record.movement_id and record.movement_id.movement_branch_id:
                record.movement_branch_id = record.movement_id.movement_branch_id.id
            else:
                movement_branch_id = movement_branch_obj.search(
                    [('type_id', '=', type.id), ("branch_id", '=', record.branch_id.id)], limit=1)
                if movement_branch_id:
                    record.movement_branch_id = movement_branch_id.id

    @api.onchange("data_line_ids")
    def _onchange_data_line(self):
        for this in self:
            datas = this.data_line_ids.filtered(
                lambda data: data.add_value and data.type in ('float', 'integer')).mapped("value")
            if datas:
                this.amount_insured = sum([float(data) for data in datas])

    @api.onchange("movement_branch_id")
    def onchange_movement_branch_id(self):
        record = self._origin if self._origin else self
        if record.movement_branch_id and not record.data_line_ids:
            lst_date = []
            for movement in record.movement_branch_id.object_line_ids:
                lst_date.append(
                    fields.Command.create(
                        {
                            "name": movement.name,
                            "type": movement.type,
                            "add_value": movement.add_value,
                            "value_field": movement.value,
                        }
                    )
                )
            record.data_line_ids = lst_date

    def generate_comparison(self):
        self.ensure_one()
        template = self.env.ref('broker_do.agreements_insurer_wizard_form')
        self.get_object_branch_id()
        if not self.branch_id:
            raise ValidationError("Es obligatorio agregar el Ramo")
        self._onchange_branch_id()
        return {
            'name': 'Acuerdos Comerciales',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'agreements.insurer.wizard',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
            'context': {
                'default_object_id': self.id,
                'default_branch_id': self.branch_id.id,
                'default_template_id': self.coverage_template_id.id,
            },
        }

    def _onchange_branch_id(self):
        coverage_template_obj = self.env['coverage.template'].sudo()
        this = self._origin if self._origin else self
        coverage_template = coverage_template_obj.search([('branch_id', '=', this.branch_id.id)], limit=1)
        if coverage_template:
            if not this.coverage_template_id:
                coverage_template_copy = coverage_template.copy()
                this.coverage_template_id = coverage_template_copy.id

    def get_agreement_data(self):
        data = [self.get_label_agreement()]
        for agreement in self.agreements_line_ids:
            dict_agreement = agreement.agreement_id.create_data_agreement(self)
            if agreement.state == 'accept':
                dict_agreement.update({
                    "accepted": "bg-info"
                })
            elif agreement.agreement_id.is_quotation:
                dict_agreement.update({
                    "accepted": "bg-warning"
                })
            else:
                dict_agreement.update({
                    "accepted": ""
                })
            data.append(dict_agreement)
        return data

    def get_insurers(self):
        partner_obj = self.env['res.partner'].sudo()
        partners = partner_obj.search([
            ('partner_type_id', 'in', (self.env.ref('broker_do.insurance_company_data').id))
        ])
        data_insurers = []
        for partner in partners:
            res = {
                "id": str(partner.id),
                "name": partner.name,
            }
            data_insurers.append(res)
        return data_insurers

    def get_label_agreement(self):
        for this in self:
            data = {
                "nombre": "Template",
            }
            groups = {}
            tmp_line_sorted = sorted(
                this.coverage_template_id.coverage_line_ids.filtered(
                    lambda l: not l.display_type == 'line_section' and l.visible),
                key=lambda x: x.sequence)
            for key, group in groupby(tmp_line_sorted, key=lambda x: x.title_line.name):
                groups[key] = list(group)
            section = []
            for key, groups in groups.items():
                res_section = {
                    "name": key
                }
                lines = []
                for line in groups:
                    res = {
                        "value": line.field if line.field else "N/A",
                        "id": line.id,
                        "tooltip": line.tooltip,
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

    def create_agreement_lead(self, data):
        agreement_obj = self.env['agreements.insurer'].sudo()
        template_obj = self.env['coverage.template'].sudo()
        for this in self:
            template = template_obj.search([('branch_id', '=', this.branch_id.id)], limit=1)
            template_coverage_id = template.id
            agreement = agreement_obj.create({
                "insurer_id": int(data.get("company_id")),
                "coverage_id": template_coverage_id,
                "default": False
            })
            agreement._onchange_coverage()
            for line in agreement.agreements_line_ids:
                for key, value in data.items():
                    value_line = "value_" + str(line.coverage_line_id.id)
                    comment_line = "comments_" + str(line.coverage_line_id.id)
                    if key == value_line:
                        line.value = value
                    if key == comment_line:
                        line.comments = value
            this.write({'agreements_line_ids': [fields.Command.create({
                'agreement_id': agreement.id,
            })]})
            return agreement

    def delete_agreement_lead(self, agreement_id):
        for this in self:
            for agreement in this.agreements_line_ids:
                if agreement.agreement_id.id == agreement_id:
                    if not agreement.agreement_id.default:
                        agreement.agreement_id.unlink()
                    agreement.unlink()
                    return 1
        return 0

    def accept_agreement_object(self, agreement):
        agreement_obj = self.env['agreements.insurer'].sudo()
        agreement_id = agreement_obj.browse(agreement)
        if agreement_id.is_quotation:
            raise ValidationError("No se puede aceptar una cotizaciÃ³n")
        result = False
        for this in self:
            agree = this.agreements_line_ids.filtered(lambda line: line.agreement_id.id == agreement_id.id)
            agree.state = 'accept'
            if this.lead_id:
                this.lead_id.stage_id = self.env.ref("broker_do.stage_lead5").id
                result = True
            for agreement in this.agreements_line_ids:
                if not agreement.id == agree.id:
                    agreement.state = 'draft'
        self.clear_caches()
        return result

    def export_object_data(self, movement_branch=False):
        """Permite obtener el formato de Objeto Asegurado"""
        movement_branch_id = self.movement_branch_id if self.movement_branch_id and not movement_branch else movement_branch
        if not movement_branch_id:
            raise ValidationError("No existe una configuraciÃ³n Asociada")
        output = io.BytesIO()
        attachment_obj = self.env['ir.attachment']
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Formato Objeto')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        row, col = 0, 1
        worksheet.write(0, 0, "Nombre Objeto", style_highlight)
        worksheet.set_column(0, 0, 30)
        for object_line in movement_branch_id.object_line_ids:
            name = object_line.name
            worksheet.write(row, col, name, style_highlight)
            worksheet.set_column(col, col, 30)
            col += 1
        workbook.close()
        xlsx_data = output.getvalue()
        data_attach = {
            'name': "Formato Objetos.xlsx",
            'datas': base64.b64encode(xlsx_data).decode(),
            'res_model': 'broker.movement.object',
            'res_id': 0,
            'type': 'binary',
        }
        attach = attachment_obj.create(data_attach)
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(
                attach.id) + "&filename_field=name&field=datas&download=true&name=" + attach.name,
            'target': 'self'
        }
        return action

    def import_object_data(self):
        self.ensure_one()
        template = self.env.ref('broker_do.broker_presettlement_wizard_form')
        return {
            'name': 'Escoja su archivo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.presettlement.wizard',
            'context': {
                'action_from': 'import_object',
                'object_id': self.id
            },
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }

    def send_email_request_quotation(self):
        self.ensure_one()
        template = self.env.ref('broker_do.request_quotation_wizard_form')
        return {
            'name': 'PeticiÃ³n de CotizaciÃ³n',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'request.quotation.wizard',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
            'context': {
                'default_object_id': self.id,
            },
        }

    def get_info_report_object(self):
        broker_value_obj = self.env['broker.movement.object.value']
        if self.type == 'normal':
            objects = self
        else:
            objects = self + self.child_line_ids
        lst_object = []
        title = False
        for object in objects:
            data_lines = object.data_line_ids.filtered(lambda data: not data.value == "")
            if not title:
                lst_object.append(object.data_line_ids.mapped('name'))
                title = True
            lst_object.append(object.data_line_ids.mapped('value'))
        return lst_object

    def get_info_comparison_object(self, is_quotation=False):
        groups = {}
        agreeements = self.agreements_line_ids.mapped("agreement_id").filtered(
            lambda agree: agree.is_quotation == is_quotation)
        sorted_agreements = sorted(agreeements.mapped("agreements_line_ids"),
                                   key=lambda line: line.coverage_line_id.sequence)
        for key, group in groupby(sorted_agreements, key=lambda x: x.coverage_line_id.id):
            groups[key] = list(group)
        section = []
        coverage_line_obj = self.env['coverage.template.line']
        for key, groups in groups.items():
            coverage = coverage_line_obj.browse(key)
            res_section = {
                "name": coverage.name if coverage.display_type == 'line_section' else coverage.field,
                "group": True if coverage.display_type == 'line_section' else False,
                "colspan": len(agreeements) + 1
            }
            lines = []
            for line in groups:
                res = {
                    "value": str(line.value) if line.value else "N/A",
                    "insurer_name": str(line.agreements_id.insurer_id.name if line.agreements_id.insurer_id else "")
                }
                lines.append(res)
            res_section.update({
                "line": lines
            })
            section.append(
                res_section
            )
        return section

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        # copiar informaciÃ³n adicional
        list_info = []
        for object_info in self.info_line_ids:
            list_info.append(fields.Command.Create({
                "name": object_info.name,
                "comment": object_info.comment,
            }))
            # Copiar Acuedo ganador
        lines = []
        for agree in self.agreements_line_ids.filtered(lambda x: x.state == 'accept'):
            agree_cp = agree.agreement_id.copy({"coverage_id": self.coverage_template_id.id})
            lines.append(fields.Command.create({
                "agreement_id": agree_cp.id
            }))
        # Copiar Informacion del objeto asegurado
        datas = []
        for data in self.data_line_ids:
            datas.append(fields.Command.create({
                "name": data.name,
                "value": data.value,
                "value_field": data.value_field,
                "type": data.type,
                "add_value": data.add_value,
            }))
        default.update({
            "name": self.name,
            "amount_fee": self.amount_fee,
            "amount_insured": self.amount_insured,
            "type": self.type,
            "branch_id": self.branch_id.id,
            'info_line_ids': list_info,
            'agreements_line_ids': lines,
            'data_line_ids': datas,
        })
        new_object = super(BrokerMovementObject, self).copy(default=default)
        return new_object

    def config_field(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.movement.object.data',
            'context': {
                'default_object_id': self.id,
            },
            'target': 'new',
        }


class BrokerMovementObjectValue(models.Model):
    _name = 'broker.movement.object.value'
    _description = 'Valores de los Objetos asegurados'

    movement_object_id = fields.Many2one(
        'broker.movement.object',
        u'Objeto Asegurado',
        required=True,
        ondelete='cascade'
    )
    movement_branch_object_id = fields.Many2one(
        'broker.movement.branch.object',
        u'ConfiguraciÃ³n Asociada',
        required=True
    )
    value_char = fields.Char(
        u'Valor textual'
    )

    @api.model
    def get_value(self, movement_object_id, code):
        param_id = int(code.replace('object_info_', ''))
        value = self.search(
            [('movement_object_id', '=', movement_object_id), ('movement_branch_object_id', '=', param_id)])
        value_param = value.value_char
        if value:
            if value.movement_branch_object_id.type == 'integer':
                value_param = int(value.value_char) if self.validate_number(value.value_char) else None
            if value.movement_branch_object_id.type == 'float':
                value_param = float(value.value_char) if self.validate_number(value.value_char) else None
        return value_param

    @api.model
    def set_value(self, movement_object_id, code, value_value):
        param_id = int(code.replace('object_info_', ''))
        if value_value != '<p><br></p>':
            vals = {'value_char': value_value}
            value = self.search(
                [('movement_object_id', '=', movement_object_id), ('movement_branch_object_id', '=', param_id)])
            if value:
                value.write(vals)
            else:
                self.create(dict(vals, movement_object_id=movement_object_id, movement_branch_object_id=param_id))

    def validate_number(self, value):
        try:
            float(value)
            return True
        except:
            return False


class BrokerMovementObjectLine(models.Model):
    _name = 'broker.movement.object.line'
    _description = 'Valores Adicionales'

    name = fields.Char(
        string='Nombre',
        required=True
    )
    comment = fields.Text(
        string="ObservaciÃ³n"
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado"
    )


class BrokerMovementObjectData(models.Model):
    _name = 'broker.movement.object.data'
    _description = 'InformaciÃ³n del Objeto Asegurado'
    _order = "sequence asc"

    sequence = fields.Integer(
        string='Secuencia'
    )

    name = fields.Char(
        string="Nombre",
        required=True
    )
    value = fields.Char(
        string="Valor"
    )
    type = fields.Selection(
        _TYPES,
        string="Tipo",
        required=True,
        default="char"
    )
    value_change = fields.Char(
        string=u"ModificaciÃ³n"
    )
    final_value = fields.Char(
        string=u"Valor final",
        compute='_compute_final_value',
        store=True
    )
    value_field = fields.Text(
        string="Valores por defecto",
        help="Usado para el listado de los campos de tipo Selection"
    )
    add_value = fields.Boolean(
        string="Â¿Suma al Valor?",
        default=False,
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado",
    )

    @api.depends('value_change')
    def _compute_final_value(self):
        for record in self:
            try:
                value_change = float(record.value_change)
                value_change = float(record.value) + value_change
            except Exception as e:
                value_change = record.value_change
            record.final_value = value_change

    def config_field(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.movement.object.data',
            'res_id': self.id,
            'target': 'new',
        }


class MovementObjectAgreement(models.Model):
    _name = "movement.object.agreement"
    _description = "Acuerdos Vinculados a un objeto"

    agreement_id = fields.Many2one(
        "agreements.insurer",
        string="Acuerdo",
        ondelete="cascade"
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado",
        ondelete="cascade"
    )
    state = fields.Selection([
        ("draft", "Borrador"),
        ("accept", "Aceptada"),
    ],
        string="Estado",
        default="draft"
    )