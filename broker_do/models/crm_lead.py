# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError
from itertools import groupby
from dateutil.relativedelta import relativedelta
import base64
from odoo.addons.broker_do.models.agreements_insurer import is_numeric_value
from datetime import datetime


class CrmLead(models.Model):
    _inherit = "crm.lead"

    contract_ids = fields.One2many(
        'broker.contract',
        "lead_id",
        string="Contratos"
    )
    branch_id = fields.Many2one(
        "broker.branch",
        string="Ramo"
    )
    is_renewal = fields.Boolean(
        string="Es renovación",
        default=False
    )
    object_line_ids = fields.One2many(
        "broker.movement.object",
        "lead_id",
        string="Objetos Asegurados"
    )
    business_id = fields.Many2one(
        'broker.business',
        string="Linea de Negocio"
    )
    renewal_id = fields.Many2one(
        "broker.contract",
        string="Contrato a Renovar"
    )
    object_type = fields.Selection([
        ("blanket", "Agrupado"),
        ("normal", "Normal"),
    ], string="Tipo Objeto",
        default="normal"
    )

    def action_process(self):
        self.write({'stage_id': self.env.ref('crm.stage_lead2').id})

    def action_proposal(self):
        self.write({'stage_id': self.env.ref('crm.stage_lead3').id})

    def action_accept_proposal(self):
        self.write({'stage_id': self.env.ref('broker_do.stage_lead5').id})

    def action_emit_policy(self):
        self.write({'stage_id': self.env.ref('crm.stage_lead4').id})

    def action_reject_policy(self):
        self.write({'stage_id': self.env.ref('broker_do.stage_lead7').id})

    def action_view_contract(self):
        self.ensure_one()
        if not self.contract_ids:
            raise ValidationError("No existe contratos asociados")
        action = self.env["ir.actions.actions"]._for_xml_id("broker_do.sale_order_action")
        type_id = self.env.ref("broker_do.policy_movement")
        if not self.contract_ids.ids:
            raise ValidationError("No existe contratos creados")
        movements = self.contract_ids.mapped("movement_ids").filtered(lambda mov: mov.type_id.id == type_id.id)
        action['domain'] = [('id', 'in', movements.ids)]
        action['context'] = {
            'active_test': False,
            'create': False
        }
        return action

    def create_contract_lead(self):
        for this in self:
            cont = 0
            for obj in this.object_line_ids:
                agree = obj.agreements_line_ids.filtered(lambda obj: obj.state == 'accept')
                if agree:
                    cont += 1
            if not cont == len(this.object_line_ids):
                raise ValidationError("Existen Objetos Asegurados sin un Acuerdo Aceptado")
            groups = {}
            agreements = this.object_line_ids.mapped('agreements_line_ids')
            agreement_order = sorted(agreements.filtered(lambda agr: agr.state == 'accept'),
                                     key=lambda x: x.agreement_id.insurer_id.id)
            for key, group in groupby(agreement_order, key=lambda x: x.agreement_id.insurer_id.id):
                groups[key] = list(group)
            contracts = []
            for key, group_item in groups.items():
                agreements = []
                value_net = 0.0
                for agree in group_item:
                    list_value = agree.agreement_id.mapped("agreements_line_ids").filtered(
                        lambda agr: agr.is_amount_fee and is_numeric_value(agr.value)).mapped("value")
                    value_net += sum([float(x) for x in list_value])
                contract = this.create_broker_contract(agreements, key, value_net)
                movement = contract.movement_ids[0]
                for agree in group_item:
                    if agree.object_id.type == 'normal':
                        agree.object_id.movement_id = movement.id
                    else:
                        list_object = []
                        for obj in range(1, agree.object_id.amount + 1):
                            list_object.append(
                                fields.Command.create({
                                    "type": "normal",
                                    "name": "%s - %s" % (str(agree.object_id.name), str(obj))
                                })
                            )
                        movement.write({
                            "object_line_ids": list_object
                        })
                contracts.append(contract)
            name_contracts = ",".join(contract.name for contract in contracts)
            this.message_post(
                body=u'Se crearon los contratoss: %s \n Fecha Actual: %s' % (
                    str(name_contracts), str(fields.Date.today())))
            this.stage_id = self.env.ref("crm.stage_lead4").id

    def create_broker_contract(self, agreements, insurer_id, value):
        type_pol = self.env.ref("broker_do.policy_movement")
        contract_obj = self.env['broker.contract']
        date_start = fields.Date.today()
        date_end = date_start + relativedelta(years=1)
        line_contract = fields.Command.create({
            "type_id": type_pol.id,
            "amount_fee": value,
            "partner_id": self.partner_id.id,
            "date_start": date_start,
            "date_end": date_end,
            "payment_period": 'monthly',
            "number_period": 12,
        })
        contract_data = {
            "branch_id": self.branch_id.id,
            "date_start": date_start,
            "date_end": date_end,
            "insurer_id": insurer_id,
            "client_id": self.partner_id.id,
            "lead_id": self.id,
            "business_id": self.business_id.id,
            "version": 1,
            "agreement_ids": [fields.Command.set([agree for agree in agreements])
                              ],
            "movement_ids": [line_contract]
        }
        if self.renewal_id:
            contract_data.update({
                "version": self.renewal_id.version + 1,
                "parent_contract_id": self.renewal_id.id,
                "contract_num": self.renewal_id.contract_num
            })
            self.renewal_id.in_renewal = False
        current_contract = contract_obj.create(contract_data)
        current_contract.onchange_insurance_company()
        current_contract.movement_ids[0].onchange_amounts_for_commission()
        current_contract._onchange_type_period()
        current_contract.movement_ids[0].action_calculate_fee()
        return current_contract

    def send_email_client(self, object_id=False, quotation=False):
        """Permite enviar un correo electrónico al cliente con las propuestas"""
        report_obj = self.env['ir.actions.report']
        quotation = self.env.context.get('quotation') or quotation
        attachment_obj = self.env['ir.attachment']
        if not self.object_line_ids:
            raise ValidationError("Se deben agregar objetos asegurados")
        if not self.object_line_ids.agreements_line_ids:
            raise ValidationError("Error: Debe generar primero una comparativa")
        object_line_ids = self.object_line_ids
        if object_id:
            object_line_ids = self.object_line_ids.filtered(lambda object_line: object_line.id == object_id)
        attachment_ids = []
        for line in object_line_ids:
            data = {
                "client_name": self.partner_id.name,
                "branch_name": self.branch_id.name,
                "today": str(datetime.today().strftime('%d DE %B %Y').upper()),
                "quotation": quotation,
            }
            pdf = report_obj._render_qweb_pdf("broker_do.action_report_broker_movement_object_comparison",
                                              line.id, data=data)[0]
            pdf = base64.b64encode(pdf).decode()
            data_attach = {
                'name': line.name + ".pdf",
                'datas': pdf,
                'res_model': 'mail.compose.message',
                'res_id': 0,
                'type': 'binary',
            }
            attachment_ids.append(attachment_obj.create(data_attach).id)
        self.ensure_one()
        template = self.env.ref('broker_do.mail_template_send_email_client', raise_if_not_found=False)
        if quotation:
            template = self.env.ref('broker_do.mail_template_send_email_request_quotation', raise_if_not_found=False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='crm.lead',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid='mail.mail_notification_light',
            mark_coupon_as_sent=True,
            force_email=True,
            default_attachment_ids=attachment_ids
        )
        return {
            'name': 'Enviar correo',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def get_agreement_data(self):
        data = [self.get_label_agreement()]
        for agreement in self.agreements_line_ids:
            dict_agreement = agreement.agreement_id.create_data_agreement(self)
            if agreement.state == 'accept':
                dict_agreement.update({
                    "accepted": "bg-info"
                })
            else:
                dict_agreement.update({
                    "accepted": ""
                })
            data.append(dict_agreement)
        return data

    def get_movement_branch(self, branch_id=False):
        movement_branch_obj = self.env['broker.movement.branch'].sudo()
        type = self.env.ref('broker_do.policy_movement')
        branch_id = self.branch_id.id if self.branch_id else branch_id
        if not branch_id:
            raise ValidationError("Debe agregar un ramo")
        movement_branch_id = movement_branch_obj.search(
            [('type_id', '=', type.id), ("branch_id", '=', branch_id)], limit=1)
        return movement_branch_id

    def import_object_data(self):
        self.ensure_one()
        template = self.env.ref('broker_do.broker_presettlement_wizard_form')
        movement_branch_id = self.get_movement_branch()
        if not movement_branch_id:
            raise ValidationError(
                "Debe crear una configuración para el ramo {branch}".format(branch=self.branch_id.name))
        return {
            'name': 'Escoja su archivo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.presettlement.wizard',
            'context': {
                'action_from': 'import_object',
                'lead_id': self.id,
                'movement_branch_id': movement_branch_id.id
            },
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }

    def export_object_data(self):
        broker_object = self.env['broker.movement.object']
        movement_branch = self.get_movement_branch()
        return broker_object.export_object_data(movement_branch=movement_branch)


class CrmLeadAgreement(models.Model):
    _name = "crm.lead.agreement"
    _description = "Acuerdos Vinculados a una oportunidad"

    agreement_id = fields.Many2one(
        "agreements.insurer",
        string="Acuerdo"
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad"
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("accept", "Aceptada"),
        ],
        string="Estado",
        default="draft"
    )
