from odoo import fields, models, api


class ModelName(models.AbstractModel):
    _name = 'report.broker_do.report_receipt_fee_payment'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Egresos/Ingresos Export'

    def generate_xlsx_report(self, workbook, data, active_ids):
        def initial_row(row=8, col=0):
            return row, col

        def print_headers(sheet, row, col, fee_payment_id):
            """Imprime las cabeceras y da formato de ancho a las columnas"""
            sheet.merge_range(0, 0, 1, 8, "RECIBO DE COBROS", title_format)
            sheet.write(2, 0, "Recibo No", title_format)
            sheet.merge_range(2, 1, 2, 2, fee_payment_id.payment_ref, title_format)
            sheet.write(3, 0, "Fecha de Emisión", title_format)
            sheet.merge_range(3, 1, 3, 2, str(fee_payment_id.date_payment or ""), title_format)
            sheet.write(4, 0, "Asegurado", title_format)
            sheet.merge_range(4, 1, 4, 2, fee_payment_id.partner_id.name, title_format)
            sheet.write(6, 0, "Cuota #", title_format)
            sheet.write(6, 1, "Ramo", title_format)
            sheet.write(6, 2, "Póliza #", title_format)
            sheet.write(6, 3, "Anexo #", title_format)
            sheet.write(6, 4, "Factura #", title_format)
            sheet.write(6, 5, "Valor", title_format)
            sheet.write(6, 6, "Forma de pago", title_format)
            sheet.write(6, 7, "Banco", title_format)
            sheet.write(6, 8, "N° Documento", title_format)
            return row

        merge_format = workbook.add_format({'align': 'left',
                                            'bold': True,
                                            'font_size': 8,
                                            'bg_color': '#FFFFCC',
                                            'border': True
                                            })
        title_format = workbook.add_format({'align': 'center',
                                            'bold': True,
                                            'font_size': 8,
                                            'bg_color': '#CCFFFF',
                                            'border': True
                                            })
        sheet = workbook.add_worksheet('Recibo de Cobros')
        fee_payment_id = active_ids[0]
        sheet.set_row(0, 25)
        row, col = initial_row()
        row = print_headers(sheet, row, col, fee_payment_id)
        for fee in fee_payment_id.sale_fee_payment_ids:
            sheet.write(row, 0, fee.fee_id.sequence, merge_format)
            sheet.write(row, 1, fee.fee_id.contract_id.branch_id.name, merge_format)
            sheet.write(row, 2, fee.fee_id.contract_id.contract_num, merge_format)
            sheet.write(row, 3, "01", merge_format)
            sheet.write(row, 4, fee.fee_id.invoice_number, merge_format)
            sheet.write(row, 5, fee.amount_paid, merge_format)
            sheet.write(row, 6, "Transferencia", merge_format)
            sheet.write(row, 7, "", merge_format)
            sheet.write(row, 8, "", merge_format)
            row += 1
            for cross_credit in fee.fee_id.negative_quota_cross_ids:
                sheet.write(row, 0, fee.fee_id.sequence, merge_format)
                sheet.write(row, 1, fee.fee_id.contract_id.branch_id.name, merge_format)
                sheet.write(row, 2, fee.fee_id.contract_id.contract_num, merge_format)
                sheet.write(row, 3, "01", merge_format)
                sheet.write(row, 4, fee.fee_id.invoice_number, merge_format)
                sheet.write(row, 5, cross_credit.value_cross, merge_format)
                sheet.write(row, 6, "Nota de Credito", merge_format)
                sheet.write(row, 7, "", merge_format)
                sheet.write(row, 8, "", merge_format)
                row += 1
        return row
