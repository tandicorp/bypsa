from odoo import models, fields
from itertools import groupby


class CommissionSpecialWizard(models.TransientModel):
    _name = "commission.special.wizard"
    _description = "Permite obtener un reporte Excel de las comisiones special por empleado"

    date_from = fields.Date(
        string="Desde",
        required=True
    )
    date_to = fields.Date(
        string="Hasta",
        required=True
    )

    def create_report(self):
        commission_obj = self.env['sale.order.line'].sudo()
        employee_obj = self.env['hr.employee'].sudo()
        for this in self:
            percent_company = self.env.user.company_id.percent_commission_special
            data = {
                "date_from": this.date_from,
                "date_to": this.date_to
            }
            commissions = commission_obj.search([
                ('fee_id.provisional_payment_date', '<=', this.date_to),
                ('fee_id.provisional_payment_date', '>=', this.date_from),
                ('status_commission', '=', 'received'),
            ])
            employees = employee_obj.search([
                ('active', '=', True),
                ('receive_commission', '=', True),
                ('user_id.business_group', '=', False)
            ])
            if commissions and employees:
                groups = {}
                employees_sorted = sorted(employees, key=lambda x: x.job_id.id)
                for key, group in groupby(employees_sorted, key=lambda x: x.job_id.name):
                    groups[key] = list(group)
                department = []
                for key, employees in groups.items():
                    employee_list = list(map(lambda x: x.user_id.id, employees))
                    total = sum(commissions.filtered(
                        lambda com: com.movement_id.contract_id.user_id.id in employee_list).mapped(
                        "amount_insurance_due")) * percent_company
                    res = {
                        "name": key,
                        "total_dep": total
                    }
                    unit = total / len(employees) if total > 0 and len(employees) > 0 else 0
                    employee_list = []
                    for employee in employees:
                        res_emp = {
                            "name": employee.name,
                            "unit": unit,
                        }
                        employee_list.append(res_emp)
                    res.update({
                        "employees": employee_list
                    })
                    department.append(res)
                data.update({
                    "departments": department,
                })
            return self.env.ref('broker_do.commission_special_report').report_action(self, data=data)
