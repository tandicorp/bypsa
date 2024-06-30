/** @odoo-module **/
import {registry} from '@web/core/registry';
import {useService} from "@web/core/utils/hooks";

import {Component, onWillStart, useState, useRef} from "@odoo/owl";

export class InsurerList extends Component {
    setup() {
        super.setup()
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.insurers = useState([]);

        onWillStart(async () => {
            this.loadRecords();
        })
        // todo: Revisar si hay una forma de escuchar eventos
        // setInterval(this.loadRecords.bind(this), 10000);
    }

    async loadRecords() {
        this.insurers = [];
        const insurers = await this.orm.call("broker.branch.insurer", "get_values_config", [""]);
        insurers.forEach(insurer => {
            this.insurers.push(insurer)
        })
        this.render();
    }


}

InsurerList.template = "broker_do.InsurerList"
registry.category('systray').add('broker_do.InsurerList', {Component: InsurerList}, {sequence: 30});