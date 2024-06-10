/** @odoo-module **/
import {registry} from '@web/core/registry';
import {useService} from "@web/core/utils/hooks";
import {Component, onWillStart, useState, useExternalListener} from "@odoo/owl";

export class AgreementCompare extends Component {
    setup() {

        super.setup()
        useExternalListener(window, 'beforeunload', this._onBeforeUnload);
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.messageInfo = useState([]);
        this.actionService = useService("action");
        this.agreements = useState([]);
        this.template = useState([]);
        this.insurers = useState([]);
        this.objects = useState([]);
        this.formulario = useState({
            company_id: ""
        });
        onWillStart(async () => {
            await this.loadValues();
            await this.loadRecordInfo();
        })
    }

    async loadValues() {
        console.log(this.lead_id)
        console.log(window.localStorage)
        this.identification = this.props.action.identification || parseInt(window.localStorage.getItem("identification"));
        this.lead_id = this.props.action.lead_id || parseInt(window.localStorage.getItem("lead_id"));
        this.template_id = this.props.action.template_id || parseInt(window.localStorage.getItem("template_id"));
    }

    async loadRecordInfo() {
        this.agreements = [];
        const agreements = await this.orm.call("broker.movement.object", "get_agreement_data", [this.identification], {});
        agreements.forEach(agreement => {
            this.agreements.push(agreement)
        })
        this.render();
    }

    _onBeforeUnload() {
        console.log("En el local store");
        window.localStorage.setItem("identification", this.identification);
        window.localStorage.setItem("lead_id", this.lead_id);
        window.localStorage.setItem("template_id", this.template_id);
    }


    async onClickDelete(agreement_id) {
        await this.orm.call("broker.movement.object", "delete_agreement_lead", [this.identification], {agreement_id});
        await this.loadRecordInfo();
        this.messageInfo = "Se elimino un acuerdo"
        this.showToast();
    }

    async onClickAccept(agreement) {
        const result = await this.orm.call("broker.movement.object", "accept_agreement_object", [this.identification], {agreement});
        this.messageInfo = "En unos segundo se mostrara el Contrato"
        this.showToast();
        return this.OnClickLead()
    }

    OnClickLead() {
        console.log(this.lead_id)
        if (this.lead_id) {
            return this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: 'crm.lead',
                res_id: this.lead_id,
                views: [[false, "form"]],
                target: "current",
                context: {
                    active_id: this.lead_id,
                },
            });
        } else {
            return this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: 'broker.movement.object',
                res_id: this.identification,
                views: [[false, "form"]],
                target: "current",
                context: {
                    active_id: this.identification,
                },
            });
        }
    }

    OnClickSendComparison() {
        const wizard = this.orm.call("crm.lead", "send_email_client", [this.lead_id], {object_id: this.identification, quotation: false});
        this.messageInfo = "Cargando Correo Electrónico..."
        this.showToast();
        return this.actionService.doAction(wizard)
    }

    OnClickSendQuotation() {
        const wizard = this.orm.call("crm.lead", "send_email_client", [this.lead_id], {object_id: this.identification, quotation: true});
        this.messageInfo = "Cargando Correo Electrónico..."
        this.showToast();
        return this.actionService.doAction(wizard)
    }

    async onClickCreate() {
        await this.orm.call("broker.movement.object", "create_agreement_lead", [this.identification], {data: this.formulario});
        await this.loadRecordInfo();
        const modal = document.getElementById('exampleModal');
        modal.style.display = 'none';
        this.messageInfo = "Acuerdo Comercial Creado con Éxito"
        this.showToast();
    }

    async OnChangeEdit(id, field, ev) {
        const value = ev.target.value;
        await this.orm.call("agreements.insurer.line", "set_value_line", [id], {value, field});
        await this.loadRecordInfo();
        this.messageInfo = "Registro Actualizado con éxito!!"
        this.showToast();
    }

    showToast() {
        const toast = $('#infoToast');
        toast.toast('show');
        this.render();
        setTimeout(function () {
            toast.toast('hide'); // Ocultamos el toast después de un cierto tiempo
        }, 10000);
    }

    async loadInfoObject() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Objeto Asegurado",
            res_model: 'broker.movement.object',
            res_id: this.identification,
            views: [[false, "form"]],
            target: "new",
            context: {
                active_id: this.identification,
            }
        });
    }

    async CreateAgreement() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Nuevo Acuerdo",
            res_model: 'agreements.insurer',
            views: [[false, "form"]],
            target: "new",
            context: {
                object_id: this.identification,
                lead_id: this.lead_id,
                default_coverage_id: this.template_id,
            },
        }, {
            onClose: async () => {
                await this.loadRecordInfo();
                this.messageInfo = "Acuerdo Comercial Creado con Éxito"
                this.showToast();
            },
        });
    }

    async UpdateTemplate() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Editar Plantilla",
            res_model: 'coverage.template',
            res_id: this.template_id,
            views: [[false, "form"]],
            target: "new",
            context: {
                active_id: this.template_id,
            },
        }, {
            onClose: async () => {
                await this.loadRecordInfo();
                this.messageInfo = "Plantilla Actualizada con exito"
                this.showToast();
            },
        });
    }
}

AgreementCompare.template = "broker_do.AgreementCompare"
registry.category('actions').add('broker_do.agreement_compare_action_js', AgreementCompare);