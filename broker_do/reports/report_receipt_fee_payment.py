# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
import odoo.tools.image as image
import io


def image_decode(companylogo):
    """Retorna el logo de la compañia redimencionado en formato bmp"""
    sm_image = image.base64_to_image(companylogo)
    image_bytes = io.BytesIO()
    sm_image.save(image_bytes, format='bmp')
    return image_bytes


bold_column_normal = {'align': 'center',
                      'bold': True,
                      'font_size': 11,
                      'border': True
                      }
normal_format = {'align': 'center',
                 'font_size': 9,
                 'border': True
                 }
bold_title_format = {'align': 'center',
                     'bold': True,
                     'font_size': 14,
                     'border': True
                     }


class ModelName(models.AbstractModel):
    _name = 'report.broker_do.report_receipt_fee_payment'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Egresos/Ingresos Export'

    def generate_xlsx_report(self, workbook, data, active_ids):
        def initial_row(row=8, col=0):
            return row, col

        def print_header(sheet, row, fee_payment_id):
            """Imprime las cabeceras y da formato de ancho a las columnas"""
            sheet.merge_range(0, 0, 1, 8, "RECIBO DE COBROS", title_format)
            sheet.write(2, 0, "Recibo No", header_title_format)
            sheet.write(3, 0, "Fecha de Emisión", header_title_format)
            sheet.write(4, 0, "Asegurado:", header_title_format)
            sheet.write(5, 0, "Contratante:", header_title_format)
            sheet.merge_range(2, 1, 2, 2, fee_payment_id.name, header_normal_format)
            image_bytes = image_decode(self.env.user.company_id.logo)
            sheet.insert_image("H3", image_bytes.getvalue())
            sheet.merge_range(3, 1, 3, 2, str(fee_payment_id.date_payment or ""), header_normal_format)
            sheet.merge_range(4, 1, 4, 2, fee_payment_id.partner_id.name, header_normal_format)
            sheet.merge_range(5, 1, 5, 2, "", header_normal_format)
            return row

        def print_columns(sheet, row):
            sheet.write(row, 0, "Cuota #", columns_title_format)
            sheet.write(row, 1, "Ramo", columns_title_format)
            sheet.write(row, 2, "Póliza #", columns_title_format)
            sheet.write(row, 3, "Anexo #", columns_title_format)
            sheet.write(row, 4, "Factura #", columns_title_format)
            sheet.write(row, 5, "Valor", columns_title_format)
            sheet.write(row, 6, "Forma de pago", columns_title_format)
            sheet.write(row, 7, "Banco", columns_title_format)
            sheet.write(row, 8, "N° Documento", columns_title_format)
            return row + 1

        def set_width_columns(col_spec):
            for col, width in col_spec:
                sheet.set_column(col, col, width)

        ############# FORMATOS #############
        # Titulo principal
        title_format = workbook.add_format(bold_title_format)
        title_format.set_align('vcenter')
        # Titulo columns
        columns_title_format = workbook.add_format(bold_column_normal)
        # Cuerpo del reporte
        normal_cell_format = workbook.add_format(normal_format)
        normal_cell_format.set_align('vcenter')
        # Etiquetas cabecera
        header_bold = bold_column_normal.copy()
        header_bold['align'] = 'left'
        header_title_format = workbook.add_format(header_bold)
        # Datos cabecera
        header_normal = normal_format.copy()
        header_normal['align'] = 'left'
        header_normal_format = workbook.add_format(header_normal)
        header_normal_format.set_align('vcenter')
        ############# Inicio del reporte #############
        sheet = workbook.add_worksheet('Recibo de Cobros')
        fee_payment_id = active_ids[0]
        sheet.set_row(0, 25)
        row, col = initial_row()
        row = print_header(sheet, row, fee_payment_id)
        column_spec = [(0, 18), (1, 18), (2, 12), (3, 12), (4, 20), (5, 12), (6, 20), (7, 20), (8, 15)]
        set_width_columns(column_spec)
        row = print_columns(sheet, row)
        for fee in fee_payment_id.sale_fee_payment_ids:
            sheet.write(row, 0, fee.fee_id.sequence, normal_cell_format)
            sheet.write(row, 1, fee.fee_id.contract_id.branch_id.name, normal_cell_format)
            sheet.write(row, 2, fee.fee_id.contract_id.contract_num, normal_cell_format)
            sheet.write(row, 3, "01", normal_cell_format)
            sheet.write(row, 4, fee.fee_id.invoice_number, normal_cell_format)
            sheet.write(row, 5, fee.amount_paid, normal_cell_format)
            sheet.write(row, 6, "Transferencia", normal_cell_format)
            sheet.write(row, 7, "", normal_cell_format)
            sheet.write(row, 8, "", normal_cell_format)
            row += 1
            for cross_credit in fee.fee_id.negative_quota_cross_ids:
                sheet.write(row, 0, fee.fee_id.sequence, normal_cell_format)
                sheet.write(row, 1, fee.fee_id.contract_id.branch_id.name, normal_cell_format)
                sheet.write(row, 2, fee.fee_id.contract_id.contract_num, normal_cell_format)
                sheet.write(row, 3, "01", normal_cell_format)
                sheet.write(row, 4, fee.fee_id.invoice_number, normal_cell_format)
                sheet.write(row, 5, cross_credit.value_cross, normal_cell_format)
                sheet.write(row, 6, "Nota de Credito", normal_cell_format)
                sheet.write(row, 7, "", normal_cell_format)
                sheet.write(row, 8, "", normal_cell_format)
                row += 1
        return row
