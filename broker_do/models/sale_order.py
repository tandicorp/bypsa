# -*- coding: utf-8 -*-
from odoo import models, api, fields, Command
from odoo.exceptions import UserError
from odoo.addons.broker_do.models.broker_contract import _OPTIONS_PAYMENT
from odoo.tools import float_round, float_compare
from odoo.exceptions import ValidationError

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

_module = 'broker_do'
_branches_medical_assistance = ['broker_branch_medical_assistance']
_branches_no_taxes = ['broker_branch_individual', 'broker_branch_collective',
                      'broker_branch_accident'] + _branches_medical_assistance


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Anexos del Contrato'
    _order = 'create_date asc, sequence asc'

    name = fields.Char(
        string='Nombre',
        store=True,
        compute='_compute_name'
    )
    sequence = fields.Integer(
        string="No. de endoso",
        default=lambda x: int(x.id),
        tracking=True
    )
    payment_period = fields.Selection(
        _OPTIONS_PAYMENT,
        string='Forma de pago',
        tracking=True
    )
    number_period = fields.Integer(
        string=u'Número de periodos',
        default=1,
        tracking=True
    )
    invoice_number = fields.Char(
        string='Número de factura',
        tracking=True
    )
    amount_fee = fields.Float(
        string='Prima neta',
        tracking=True
    )
    amount_tax_insurance_peasant = fields.Float(
        string='Seguro campesino',
        store=True,
        compute='_compute_amount_taxes_insurance',
        inverse="_set_amounts",
        tracking=True
    )
    amount_tax_super_cias = fields.Float(
        string=u'Super. de compañías',
        store=True,
        compute='_compute_amount_taxes_insurance',
        inverse="_set_amounts",
        tracking=True
    )
    amount_tax_emission_rights = fields.Float(
        string=u'Derechos de emisión',
        tracking=True
    )
    amount_fee_subtotal = fields.Float(
        'Subtotal cuota',
        store=True,
        compute='_compute_amount_taxes_insurance',
        inverse="_set_amounts"
    )
    amount_tax_iva = fields.Float(
        'IVA',
        store=True,
        compute='_compute_amount_taxes_insurance',
        inverse="_set_amounts",
        tracking=True
    )
    amount_other_charges = fields.Float(
        string='Intereses / Otros cargos',
        tracking=True
    )
    amount_due = fields.Float(
        string='Prima total',
        store=True,
        compute='_compute_amounts_for_commission',
        inverse="_set_amounts",
        tracking=True
    )
    commission_percentage = fields.Float(
        string=u'Porcentaje de comisión',
        tracking=True
    )
    amount_total_commission = fields.Float(
        string=u'Valor de comisión',
        compute='get_amount_total_commission',
        store=True,
        tracking=True
    )
    date_start = fields.Date(
        string='Fecha de inicio',
        tracking=True
    )
    date_end = fields.Date(
        string='Fecha de fin',
        tracking=True
    )
    day_number = fields.Integer(
        'No. de días',
        compute='_compute_day_number'
    )
    date_invoice = fields.Date(
        string='Fecha de primera cuota',
        tracking=True
    )
    date_next_payment = fields.Date(
        string='Fecha de siguientes cuotas',
        tracking=True
    )
    amount_accumulate_claim = fields.Float(
        string=u'Valor acumulado de siniestros'
    )
    business_id = fields.Many2one(
        related="contract_id.business_id",
        store=True
    )
    status_movement = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('insurance_release', 'Remitido aseguradora'),
            ('approved', 'Emitido'),
            ('rejected', 'Rechazado'),
            ('cancel', 'Cancelado')
        ],
        string='Estado',
        default='draft',
        tracking=True
    )
    taxes_calculation = fields.Selection(
        [
            ('first_fee', 'Primera cuota'),
            ('fee_distributed', 'Distribuida en las cuotas'),
        ],
        string=u"Distribución impuestos",
        default="first_fee",
        tracking=True
    )
    warning_flag = fields.Boolean(
        'Bandera para mensaje de advertencia comisiones'
    )
    contract_id = fields.Many2one(
        "broker.contract",
        string="Contrato",
        tracking=True
    )
    contract_num = fields.Char(
        related="contract_id.contract_num",
        inverse="_set_contract_num",
        string="No. de Contrato"
    )
    type_id = fields.Many2one(
        "sale.order.type",
        string='Tipo de Anexo',
        tracking=True
    )
    object_line_ids = fields.One2many(
        "broker.movement.object",
        "movement_id",
        string='Objetos Asegurados'
    )
    stakeholder_ids = fields.One2many(
        "broker.movement.stakeholder",
        "movement_id",
        string='Interesados'
    )
    fee_line_ids = fields.One2many(
        'sale.order.fee',
        'movement_id',
        string='Cuotas de movimiento'
    )
    movement_branch_id = fields.Many2one(
        "broker.movement.branch",
        string="Plantilla de movimiento",
        compute="get_movement_branch",
        store=True
    )
    client_id = fields.Many2one(
        related="contract_id.client_id",
        store=True,
        string="Cliente"
    )
    insurer_id = fields.Many2one(
        related="contract_id.insurer_id",
        store=True,
        string="Aseguradora"
    )
    document_line_ids = fields.One2many(
        "sale.order.document",
        "order_id",
        string="Documentos"
    )
    branch_id = fields.Many2one(
        related="contract_id.branch_id",
        store=True,
        string="Ramo"
    )
    is_manual_fee = fields.Boolean(
        string="¿Es prima manual?",
        default=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        contract_obj = self.env['broker.contract']
        for element in vals_list:
            if 'contract_id' in element and element['contract_id']:
                move_draft_ids = contract_obj.browse(element['contract_id']).movement_ids.filtered(
                    lambda x: x.status_movement in ('draft', 'insurance_release'))
                if move_draft_ids:
                    raise ValidationError(
                        u'No se puede crear nuevos movimientos si existen, movimientos anteriores en borrador.'
                        u'\n¡Por favor confirme o elimine los movimientos previos antes de continuar!')
        return super(SaleOrder, self).create(vals_list)

    @api.depends()
    def _set_contract_num(self):
        self.contract_id.contract_num = self.contract_num

    @api.depends("type_id")
    def get_movement_branch(self):
        movement_branch_obj = self.env['broker.movement.branch'].sudo()
        for record in self:
            movement_branch_id = movement_branch_obj.search(
                [('type_id', '=', record.type_id.id), ("branch_id", '=', record.contract_id.branch_id.id)], limit=1)
            if movement_branch_id:
                documents = []
                for document in movement_branch_id.document_line_ids:
                    documents.append(Command.create({
                        "order_id": record.id,
                        "document_id": document.id,
                        "name": document.name
                    }))
                record.document_line_ids = [fields.Command.clear()] + documents
                record.movement_branch_id = movement_branch_id.id
            movement_date_ids = [(move.id, move.date_start) for move in self.contract_id.movement_ids]
            movement_date_ids.sort(key=lambda x: x[1])
            if self.env.ref(_module + '.' + 'monthly_declaration_movement', raise_if_not_found=False) == self.type_id:
                period_id = self.contract_id.get_period_from_date(movement_date_ids[-1][1])
                next_period_id = self.contract_id.get_next_period(period_id)
                self.date_start = next_period_id.date_from
                self.date_end = next_period_id.date_to

    @api.depends("amount_fee")
    def _compute_amount_taxes_insurance(self):
        for record in self:
            if self.env.user.company_id.tax_insurance_peasant_id:
                amount_taxes = self.env.user.company_id.tax_insurance_peasant_id.compute_all(record.amount_fee)
                record.amount_tax_insurance_peasant = amount_taxes['taxes'][0]['amount']
            if self.contract_id.branch_id not in [self.env.ref(_module + '.' + branch, raise_if_not_found=False) for
                                                  branch in _branches_medical_assistance]:
                if self.env.user.company_id.tax_super_cias_id:
                    amount_taxes = self.env.user.company_id.tax_super_cias_id.compute_all(record.amount_fee)
                    record.amount_tax_super_cias = amount_taxes['taxes'][0]['amount']
            record.amount_fee_subtotal = sum([record.amount_fee, record.amount_tax_insurance_peasant,
                                              record.amount_tax_super_cias, record.amount_tax_emission_rights])
            if self.contract_id.branch_id not in [self.env.ref(_module + '.' + branch, raise_if_not_found=False) for
                                                  branch in _branches_no_taxes]:
                amount_taxes = self.env.user.company_id.account_sale_tax_id.compute_all(record.amount_fee_subtotal)
                record.amount_tax_iva = amount_taxes['taxes'][0]['amount']
            record.amount_due = sum([self.amount_fee, self.amount_tax_insurance_peasant,
                                     self.amount_tax_super_cias, self.amount_tax_iva,
                                     self.amount_tax_emission_rights, self.amount_other_charges])

    def _set_amounts(self):
        for record in self:
            record.amount_tax_insurance_peasant = record.amount_tax_insurance_peasant
            record.amount_tax_super_cias = record.amount_tax_super_cias
            record.amount_fee_subtotal = record.amount_fee_subtotal
            record.amount_tax_iva = record.amount_tax_iva

    @api.depends("contract_id", "contract_id.name", "sequence", "type_id")
    def _compute_name(self):
        for this in self:
            insurer_shortname = this.contract_id and this.contract_id.insurer_id.shortname or ""
            type_code = this.type_id and this.type_id.code or ""
            this.name = " - ".join([insurer_shortname, this.contract_id.name or '']) + " | " + " - ".join(
                [type_code, str(this.sequence)])

    @api.depends('date_start', 'date_end')
    def _compute_day_number(self):
        for record in self:
            if record.date_end and record.date_start:
                record.day_number = (record.date_end - record.date_start).days
            else:
                record.day_number = 0

    @api.depends('amount_other_charges', 'amount_tax_iva', "amount_tax_insurance_peasant", "amount_tax_super_cias",
                 "amount_tax_emission_rights")
    def _compute_amounts_for_commission(self):
        self.amount_due = sum([self.amount_fee, self.amount_tax_insurance_peasant,
                               self.amount_tax_super_cias, self.amount_tax_iva,
                               self.amount_tax_emission_rights, self.amount_other_charges])
        if self.fee_line_ids:
            if self.taxes_calculation == 'first_fee':
                fee = self.fee_line_ids.filtered(lambda fee: fee.sequence == 1)
                if fee:
                    taxes = ['amount_tax_insurance_peasant', 'amount_tax_super_cias', 'amount_tax_iva',
                             'amount_tax_emission_rights', 'amount_other_charges']
                    fee[0].amount_insurance_due = fee[0].amount_insurance_fee + sum([self[tax] for tax in taxes])

    @api.onchange('type_id')
    def onchange_amounts_for_commission(self):
        if self.type_id in (self.env.ref('broker_do.transportation_application_movement'),
                            self.env.ref('broker_do.cancel_movement'),
                            self.env.ref('broker_do.exclusion_movement'),):
            self.number_period = 1

    @api.depends("order_line")
    def get_amount_total_commission(self):
        value = sum(self.order_line.mapped("price_unit"))
        self.amount_total_commission = value

    def get_value_amounts(self, mount_fee, mount_due, index=False, list_fee_amount=False, type_taxes=False):
        return mount_fee, mount_due

    def assign_fee_amounts(self, residual_amount_due, residual_amount_fee, fee_vals, type_taxes=False,
                           list_amounts=False):
        decimal_places = self.env.company.currency_id.decimal_places
        period_num = len(fee_vals)
        taxes = ['amount_tax_insurance_peasant', 'amount_tax_super_cias', 'amount_tax_iva',
                 'amount_tax_emission_rights', 'amount_other_charges']
        if period_num:
            equal_mount_due = residual_amount_due / period_num
            equal_mount_fee = residual_amount_fee / period_num
            for index, val in enumerate(fee_vals):
                mount_fee, mount_due = self.get_value_amounts(equal_mount_fee, equal_mount_due, index=index,
                                                              list_fee_amount=list_amounts, type_taxes=type_taxes)
                if type_taxes == 'first_fee' and index == 0:
                    mount_due = mount_fee + sum([self[tax] for tax in taxes])
                    if period_num - 1:
                        equal_mount_due = (residual_amount_due - mount_due) / (period_num - 1)
                val.update(
                    {
                        'amount_insurance_due': float_round(mount_due, decimal_places, rounding_method='HALF-DOWN'),
                        'amount_insurance_fee': float_round(mount_fee, decimal_places, rounding_method='HALF-DOWN'),
                    }
                )
        return fee_vals

    def action_calculate_fee(self):
        decimal_places = self.env.company.currency_id.decimal_places

        def assign_fee_period(num_period, space_period, date_start, init_seq=0, first_date=False):
            list_due = []
            num_period += init_seq
            if num_period <= 0:
                return []
            months_num = len(calendar.month_name) - 1
            delta = lambda x: relativedelta(months=x)
            if space_period == 'yearly':
                delta = lambda x: relativedelta(months=x * (months_num or 12))
            range_period = range(init_seq, num_period)
            if first_date:
                list_due = [
                    {'sequence': 1,
                     'provisional_payment_date': first_date,
                     'period_id': self.contract_id.get_period_from_date(first_date),
                     }]
                range_period = range(init_seq, num_period - 1)
            init_len = len(list_due)
            list_due.extend([
                {'sequence': i + 1 + init_len,
                 'provisional_payment_date': date_start + delta(i),
                 'period_id': self.contract_id.get_period_from_date(date_start + delta(i)),
                 } for i in range_period
            ])
            return list_due

        def adjust_period_amounts(residual_amount_due, residual_amount_fee, fee_line_ids):
            if len(fee_line_ids) <= 1:
                return fee_line_ids
            fee_line4sum = fee_line_ids[:-1]
            fee_line_ids[-1].update(
                {
                    'amount_insurance_due': float_round(residual_amount_due - float_round(sum([
                        i.get('amount_insurance_due') for i in fee_line4sum]), decimal_places),
                                                        decimal_places),
                    'amount_insurance_fee': float_round(residual_amount_fee - float_round(sum([
                        i.get('amount_insurance_fee') for i in fee_line4sum]), decimal_places),
                                                        decimal_places),
                }
            )
            return fee_line_ids

        date_start = self.date_next_payment or self.date_start or datetime.utcnow().date()
        num_period, period, date_begin = self.number_period, 'monthly', date_start
        first_date = self.date_invoice
        if self.amount_due and self.status_movement in ('draft', 'insurance_release'):
            if self.payment_period == 'annually':
                num_period, period = 1, 'yearly'
            elif self.payment_period == 'annully_comision':
                period = 'yearly'
            paid_fee_ids = self.fee_line_ids.filtered(lambda x: x.status_fee != 'no_payment')
            if paid_fee_ids:
                raise ValidationError(
                    "Existen cuotas que ya han sido pagados y no se puede recalcular las cuotas una vez que se han "
                    "realizado pagos, para realizar este proceso, se debe eliminar los pagos asociados a las cuotas.")
            self.fee_line_ids.unlink()
            balance_amount_due = self.amount_due  # CUOTA TOTAL
            balance_amount_fee = self.amount_fee  # PRIMA NETA
            fee_line_ids = assign_fee_period(num_period, period, date_begin, len(paid_fee_ids), first_date=first_date)
            fee_line_ids = self.assign_fee_amounts(balance_amount_due, balance_amount_fee, fee_line_ids,
                                                   type_taxes=self.taxes_calculation, list_amounts=False)
            fee_line_ids = adjust_period_amounts(balance_amount_due, balance_amount_fee, fee_line_ids)
            operation = 1 if self.type_id.operation == 'positive' else -1
            for line in fee_line_ids:
                line['amount_insurance_due'] = line['amount_insurance_due'] * operation
                line['amount_insurance_fee'] = line['amount_insurance_fee'] * operation
            self.fee_line_ids = [fields.Command.create(val) for val in fee_line_ids]
            self.contract_id._onchange_contract_fee_ids()
            self.warning_flag = True
        else:
            if not self.amount_due:
                message = "no tiene valor de prima neta"
            else:
                message = 'no se encuentra en estado "Borrador" o "Remitido aseguradora"'
            raise ValidationError(u'El movimiento {}, por esto no se puede recalcular las cuotas.'.format(message))

    def action_recalculate_fee(self):
        self.contract_id._onchange_contract_fee_ids()

    def action_open_movement(self):
        template = self.env.ref('broker_do.sale_order_form')
        if self.type_id.view_id:
            template = self.type_id.view_id
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'sale.order',
            'view_mode': 'form',
            'views': [(template.id, 'form')],
        }

    def action_select_object(self):
        template = self.env.ref('broker_do.wizard_contract_object_form')
        return {
            'name': 'Escoja un item para modificar',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'context': {'default_contract_id': self.contract_id.id, 'default_movement_id': self.id,
                        'default_movement_contract_object_ids': self.object_line_ids.mapped('contract_object_id').ids},
            'res_model': 'wizard.contract.object',
            'view_mode': 'form',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }

    def action_insurance_release(self):
        self.ensure_one()
        self.compare_fee_sum_amount()
        template_movement_branch = self.env['broker.movement.branch'].sudo().search(
            [('branch_id', '=', self.contract_id.branch_id.id), ('type_id', '=', self.type_id.id)])
        template = template_movement_branch.mail_template_id or False
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='sale.order',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            default_email_layout_xmlid='mail.mail_notification_light',
            mark_coupon_as_sent=True,
            force_email=True,
        )
        return {
            'name': 'Remitir Aseguradora',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_generate_commission(self, **kwargs):
        if self.order_line._check_line_unlink():
            raise UserError(
                u"El contrato se encuentra vigente y no se puede realizar el recálculo de las comisiones.")
        if not self.fee_line_ids:
            raise UserError(
                u"El movimiento no posee cuotas de contrato y no se puede realizar el cálculo de las comisiones.")
        distribution, period_num = 'first', 1
        decimal_places = self.env.company.currency_id.decimal_places
        if self.amount_due and self.payment_period == 'annully_comision':
            distribution, period_num = 'all', self.number_period
        mount_fee = self.amount_fee / period_num
        amount_commission, fee_id, order_vals = 0, False, []
        lst_commission = []
        if distribution == 'first':
            lst_commission = self.get_lst_commission(decimal_places, self.amount_fee)
        elif distribution == 'all':
            lst_commission = self.get_lst_commission(decimal_places, mount_fee)
        operation = 1 if self.type_id.operation == 'positive' else -1
        for sequence in range(0, period_num):
            for commission in lst_commission:
                fee_ids = self.fee_line_ids
                order_vals.append({
                    'product_id': self.contract_id.branch_id.product_id.id,
                    'product_uom_qty': 1,
                    'amount_fee': kwargs.get('amount_fee') or commission.get("amount_fee"),
                    'price_unit': commission.get("price_unit") * operation,
                    'percentage_commission': commission.get("percentage_commission"),
                    'percentage_fee': commission.get("percentage_fee"),
                    'sequence': sequence + 1,
                    'fee_id': fee_ids.filtered(lambda x: x.sequence == sequence + 1).id,
                    'status_commission': 'to_release' if not fee_ids.filtered(
                        lambda x: x.status_fee == 'paid' and x.sequence == sequence + 1) else 'to_receive'
                })
        value = sum(list(map(lambda x: x['price_unit'], order_vals)))
        commission_percentage = value / self.amount_fee
        self.write(dict(order_line=[fields.Command.clear()] + [fields.Command.create(val) for val in order_vals],
                        warning_flag=False,
                        commission_percentage=commission_percentage
                        ))

    def action_set_invoice_number(self):
        for fee_id in self.fee_line_ids:
            fee_id.invoice_number = self.invoice_number

    def compare_fee_sum_amount(self):
        if float_compare(self.amount_fee, abs(sum(self.fee_line_ids.mapped('amount_insurance_fee'))), 2) != 0:
            raise ValidationError(u'Las cuotas del movimiento no suman lo mismo que el total de la prima.')

    def action_release_move(self):
        self.compare_fee_sum_amount()
        self.status_movement = 'insurance_release'

    def action_back_release_move(self):
        self.status_movement = 'insurance_release'

    def action_approve_move(self):
        if self.type_id == self.env.ref('broker_do.policy_movement'):
            self.contract_id.state = 'valid'
        for object_id in self.object_line_ids:
            # Cuando no tengo items se crea una copia del objeto en el contrato
            if not object_id.contract_object_id:
                contract_object_id = object_id.copy({
                    'contract_id': self.contract_id.id,
                    'movement_id': False,
                })
                object_id.contract_object_id = contract_object_id.id
            # Cuando es exclusion se desactiva el objeto en el contrato del que se saco la copia
            elif self.type_id == self.env.ref('broker_do.exclusion_movement'):
                object_id.contract_object_id.active = False
            # Actualizacion del objeto del contrato por sus cambios en el movimiento
            else:
                for object_id in self.object_line_ids:
                    if not object_id.contract_object_id:
                        contract_object_id = object_id.copy({
                            'contract_id': self.contract_id.id,
                            'movement_id': False,
                        })
                        object_id.contract_object_id = contract_object_id.id
                    else:
                        contract_object_id = object_id.contract_object_id
                        contract_object_id.data_line_ids.unlink()
                        for data_line_id in object_id.data_line_ids:
                            data_line_id.copy(
                                {
                                    'value': data_line_id.final_value,
                                    'final_value': False,
                                    'value_change': False,
                                    'object_id': contract_object_id.id,
                                }
                            )
        self.status_movement = 'approved'

    def action_reject_move(self):
        if self.type_id == self.env.ref('broker_do.policy_movement'):
            self.contract_id.state = 'not_valid'
        self.status_movement = 'rejected'

    def get_lst_commission(self, decimal_places, amount):
        lst_commission = []
        group_coverage = False
        if self.contract_id.commission_insurer_id:
            commission_ids = self.contract_id.commission_insurer_id.commission_line_ids.filtered(
                lambda x: x.branch_id.id == self.contract_id.branch_id.id)
            if len(commission_ids) > 1:
                group_coverage = True
            for commission in commission_ids:
                if group_coverage:
                    percentage_commission = commission.percentage_value
                else:
                    percentage_commission = self.commission_percentage
                amount_fee = amount * commission.percentage_fee
                amount_commission = float_round(amount_fee * percentage_commission, decimal_places,
                                                rounding_method='HALF-DOWN')
                res = {
                    "amount_fee": amount_fee,
                    "percentage_commission": percentage_commission,
                    "price_unit": amount_commission,
                    "percentage_fee": commission.percentage_fee,
                }
                lst_commission.append(res)
        return lst_commission

    def import_object_data(self):
        self.ensure_one()
        template = self.env.ref('broker_do.broker_presettlement_wizard_form')
        crm_lead_object = self.env['crm.lead']
        movement_branch_id = crm_lead_object.get_movement_branch(branch_id=self.contract_id.branch_id.id)
        if not movement_branch_id:
            raise ValidationError(
                "Debe crear una configuración para el ramo {branch}".format(branch=self.contract_id.branch_id.name))
        return {
            'name': 'Escoja su archivo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.presettlement.wizard',
            'context': {
                'action_from': 'import_object',
                'movement_id': self.id,
                'movement_branch_id': movement_branch_id.id
            },
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }

    def export_object_data(self):
        broker_object = self.env['broker.movement.object']
        crm_lead_object = self.env['crm.lead']
        movement_branch = crm_lead_object.get_movement_branch(branch_id=self.contract_id.branch_id.id)
        return broker_object.export_object_data(movement_branch=movement_branch)


class SaleOrderType(models.Model):
    _name = 'sale.order.type'

    name = fields.Char(
        string="Nombre",
        required=True
    )
    code = fields.Char(
        string="Código",
    )
    operation = fields.Selection([
        ("positive", "Positiva"),
        ("negative", "Negativa"),
    ],
        string="Tipo de Operación",
        default="positive"
    )
    view_id = fields.Many2one(
        'ir.ui.view',
        string="Vista a para mostrar",
    )


class SaleOrderDocument(models.Model):
    _name = 'sale.order.document'

    order_id = fields.Many2one(
        "sale.order",
        string="Movimiento"
    )
    contract_id = fields.Many2one(
        "broker.contract",
        related="order_id.contract_id",
        string="Contrato",
        store=True
    )
    document_id = fields.Many2one(
        "broker.movement.document",
        string="Configuración Asociada",
        required=True
    )
    name = fields.Char(
        string="Nombre"
    )
    upload = fields.Boolean(
        string="Documento Cargado?"
    )
