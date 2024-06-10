# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
import base64
import xlrd


class BrokerPresettlementWizard(models.TransientModel):
    _name = 'broker.presettlement.wizard'

    file = fields.Binary(
        string="Cargar archivo",
        attachment=True
    )
    filename = fields.Char(
        string="Cargar archivo"
    )
    message = fields.Text(
        string="Mensaje"
    )

    def load_file(self):
        if not self.file:
            raise ValidationError("Debe subir un archivo")
        data_file = base64.decodebytes(self.file)
        excel = xlrd.open_workbook(file_contents=data_file)
        return excel.sheet_by_index(0)

    def import_sheet(self):
        sh = self.load_file()
        presettlement_id = self.env['broker.presettlement'].browse(self.env.context.get('active_id'))
        presettlement_id.action_generate_presettlement()
        matched_presettlement_line_ids, not_matched_commission_ids = self.env['broker.presettlement.line'], []
        for r in range(1, sh.nrows):
            row = sh.row_values(r)
            contract_num, type_contract, fee_num_seq, amount_insurer = row[0], row[1], row[2], row[3]
            data = {
                'contract_num_excel': contract_num,
                'type_contract_excel': type_contract,
                'fee_num_seq_excel': fee_num_seq
            }
            contract_id = self.env['broker.contract'].search([('contract_num', '=', contract_num)])
            commission_id = self.env['sale.order.line'].search([
                ('order_id.contract_id.insurer_id', '=', presettlement_id.insurer_id.id),
                ('fee_id.provisional_payment_date', '<=', presettlement_id.date_end),
                ('status_commission', '!=', 'received'),
                '|', ('order_id.contract_id', '=', contract_id.id),
                ('order_id.contract_id.contract_num', '=', contract_num),
                ('order_id.type_id.code', 'ilike', type_contract),
                ('sequence', '=', fee_num_seq)
            ])
            presettlement_line_ids = presettlement_id.presettlement_line_ids.filtered(
                lambda x: x.commission_id == commission_id)
            if not presettlement_line_ids:
                data.update({
                    'number_fee': len(not_matched_commission_ids) + 1,
                    'commission_id': False,
                    'contract_id': contract_id.id,
                    'amount_insurer': amount_insurer,
                    'amount_original_commission': 0,
                    'display_type': 'commission',
                    'amount_commission': amount_insurer,
                    'create_commission': True,
                })
                not_matched_commission_ids.append(data)
            else:
                matched_presettlement_line_ids += presettlement_line_ids
                data.update({'amount_insurer': amount_insurer})
                presettlement_line_ids.write(data)
        sequence = 1
        presettlement_line_data = [
            Command.create({
                'sequence': sequence,
                'display_type': 'line_section',
                'name': 'Comisiones no esperadas',
            })
        ]
        for val in not_matched_commission_ids:
            sequence += 1
            val.update({'sequence': sequence})
        presettlement_line_data.extend([
            Command.create(val) for val in not_matched_commission_ids
        ])
        sequence += 1
        presettlement_line_data.append(
            Command.create({
                'sequence': sequence,
                'display_type': 'line_section',
                'name': 'Comisiones obtenidas y empatadas',
            })
        )
        presettlement_line_data.extend([
            Command.update(id, {'sequence': sequence + index + 1}) for index, id in
            enumerate(matched_presettlement_line_ids.ids)
        ])
        sequence += len(matched_presettlement_line_ids)
        sequence += 1
        presettlement_line_data.append(
            Command.create({
                'sequence': sequence,
                'display_type': 'line_section',
                'name': 'Comisiones obtenidas y no empatadas',
            })
        )
        presettlement_line_data.extend([
            Command.update(line_id.id, {'sequence': sequence + index + 1}) for index, line_id in
            enumerate(presettlement_id.presettlement_line_ids - matched_presettlement_line_ids)
        ])
        presettlement_id.presettlement_line_ids = presettlement_line_data
        for line_id in presettlement_id.presettlement_line_ids:
            line_id.commission_to_adjust = True if line_id.amount_difference != 0 else False

    def import_payment_sheet(self):
        sh = self.load_file()
        payment_id = self.env['account.payment'].browse(self.env.context.get('payment_id'))
        payment_id.fee_payment_ids.unlink()
        for r in range(1, sh.nrows):
            row = sh.row_values(r)
            commission_id = self.env['sale.order.line'].search([
                ('movement_id.contract_id.insurer_id', '=', self.env.context.get('insurer_id')),
                ('status_commission', '=', 'to_release'),
                ('status_fee', '=', 'no_payment'),
                ('movement_id.contract_id.contract_num', '=', row[0]),
                ('movement_id.type_id.code', '=', row[1]),
                ('sequence', '=', row[2])
            ])
            if commission_id:
                commission_id.payment_ids = [fields.Command.create({'payment_id': payment_id.id,
                                                                    'commission_id': commission_id.id,
                                                                    'amount_paid': commission_id.balance_due})]
        payment_id.amount = sum(payment_id.fee_payment_ids.mapped('amount_paid'))

    def import_object_info(self):
        context = self.env.context.copy()
        movement_object = self.env['broker.movement.object']
        sale_order_obj = self.env['sale.order']
        movement_info_object = self.env['broker.movement.object.value']
        if context.get('object_id'):
            object_id = movement_object.browse(context.get('object_id'))
        if context.get('movement_id'):
            movement_id = sale_order_obj.browse(context.get('movement_id'))
        sh = self.load_file()
        lst_info = []
        headers = sh.row_values(0)
        for r in range(2, sh.nrows):
            rows = sh.row_values(r)
            res = {
                "type": "normal",
                "name": rows[0],
            }
            if context.get('object_id'):
                res.update({
                    "parent_object_id": object_id.id,
                    "movement_branch_id": object_id.movement_branch_id.id
                })
            if context.get('movement_id'):
                res.update({
                    "movement_id": movement_id.id,
                    "movement_branch_id": movement_id.movement_branch_id.id
                })
            if context.get('lead_id'):
                res.update({
                    "lead_id": context.get('lead_id'),
                    "movement_branch_id": context.get('movement_branch_id')
                })
            object_move = movement_object.create(res)
            for row in range(1, len(headers)):
                res = {
                    "movement_object_id": object_move.id,
                    "movement_branch_object_id": int(headers[row]),
                    "value_char": rows[row],
                }
                lst_info.append(res)
        movement_info_object.create(lst_info)
