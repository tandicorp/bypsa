from odoo import models, fields, api
from datetime import datetime
import pytz


class CommissionSpecialReport(models.AbstractModel):
    _name = 'report.broker_do.commission.special.report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Reporte de Comisiones Especiales'

    def get_data(self):
        return self.env['commission.special.wizard'].data['data']

    def generate_xlsx_report(self, workbook, data, active_ids):
        def initial_row(row=8, col=0):
            return row, col

        def print_headers(sheet):
            tz = pytz.timezone(self.env.user.tz)
            sheet.merge_range(0, 0, 2, 10, "Comisiones Especiales",
                              title_format)
            sheet.merge_range(3, 0, 3, 1, "Compañía:",
                              title_format)
            sheet.merge_range(3, 2, 3, 4, self.env.user.company_id.name,
                              title_format)
            sheet.merge_range(4, 0, 4, 1, "Periodo:",
                              title_format)
            sheet.merge_range(4, 2, 4, 4,
                              str(data.get("date_from")) + " - " + str(data.get("date_to")),
                              title_format)
            sheet.merge_range(5, 0, 5, 1, "Creado el:",
                              title_format)
            sheet.merge_range(5, 2, 5, 4, datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
                              title_format)
            sheet.merge_range(6, 0, 6, 1, "Valor Total en el periodo:",
                              title_format)
            sheet.merge_range(6, 2, 6, 4, data.get("total", 0.00),
                              title_format)
            sheet.merge_range(7, 0, 7, 4, "NOMBRES Y APELLIDOS", merge_format)
            sheet.merge_range(7, 5, 7, 6, "VALOR DE COMISIÓN", merge_format)

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
        sheet = workbook.add_worksheet('Empleados')
        sheet.set_row(0, 25)
        row, col = initial_row()
        print_headers(sheet)
        if data.get("departments"):
            for department in data.get("departments"):
                sheet.merge_range(row, 0, row, 4, department.get("name"), merge_format)
                sheet.merge_range(row, 5, row, 6, department.get("total_dep", 0.0), merge_format)
                row += 1
                for line in department.get("employees"):
                    sheet.merge_range(row, 0, row, 4, line.get("name"), merge_format)
                    sheet.merge_range(row, 5, row, 6,  line.get("unit", 0.0), merge_format)
        return row
