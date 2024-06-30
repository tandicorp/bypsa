/** @odoo-module */

import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {Component, useState, useRef} from "@odoo/owl";
import {DatePicker} from "@web/core/datepicker/datepicker";
import {registry} from "@web/core/registry";
import {areDateEquals, formatDateTime} from "@web/core/l10n/dates";
import {localization} from "@web/core/l10n/localization";
import {formatFloat, formatInteger, formatChar} from "@web/views/fields/formatters";
import {parseFloat, parseInteger} from "@web/views/fields/parsers";
import {useInputField} from "@web/views/fields/input_field_hook";
import {useNumpadDecimal} from "@web/views/fields/numpad_decimal_hook";

export class WidgetType extends Component {

    setup() {

        this.lastSetValue = null;
        this.revId = 0;
        this.typeField = this.props.record.data.type || 'char'
        this.state = useState({
            typeField: this.props.record.data.type || 'char'
        });

        if (this.typeField === 'integer') {
            useInputField({
                getValue: () => this.formattedValueInteger,
                refName: "numpadNumeric",
                parse: (v) => parseInteger(v),
            });
            useNumpadDecimal();
        }
        if (this.typeField === 'float') {
            this.inputRef = useInputField({
                getValue: () => this.formattedValueFloat,
                refName: "numpadDecimal",
                parse: (v) => this.parseFloat(v),
            });
            useNumpadDecimal();
        }
        if (this.typeField === 'char') {
            this.input = useRef("input");
            useInputField({getValue: () => this.props.value || "", parse: (v) => this.parseChar(v)});
        }
        if (this.typeField === 'selection') {
            this.value_field = this.props.record.data.value_field
        }
    }

    get date() {
        var value = new Date(this.props.value);
        return value;
    }

    parseFloat(value) {
        return this.props.inputType === "number" ? Number(value) : parseFloat(value);
    }

    onDateTimeChanged(date) {
        console.log("El valor del date ondatetime ", date)
        if (!areDateEquals(this.date || "", date)) {
            console.log("en el if");
            this.revId++;
            this.props.update(date);
        }
    }

    get formattedValue() {
        if (this.props.value === "") {
            return "";
        } else {
            return formatDateTime(this.props.value, {format: localization.dateFormat})
        }
    }

    onDatePickerInput(ev) {
        this.props.setDirty(ev.target.value !== this.lastSetValue);
    }

    onUpdateInput(date) {
        this.props.setDirty(false);
        this.lastSetValue = date;
    }

    get formattedValueFloat() {
        var value = this.props.value == "" ? null : Number(this.props.value);
        if (this.props.inputType === "number" && !this.props.readonly && value) {
            return value;
        }
        return formatFloat(value, {digits: 2});
    }

    get formattedValueInteger() {
        var value = this.props.value == "" ? null : parseInt(this.props.value);
        if (!this.props.readonly && this.props.inputType === "number") {
            return value;
        }
        return formatInteger(value);
    }

    get formattedValueChar() {
        return formatChar(this.props.value, {isPassword: false});
    }

    parseChar(value) {
        if (this.props.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    // Para el tipo de seleccion

    stringify(value) {
        return JSON.stringify(value);
    }

    get options() {
        if (this.value_field !== "" && this.value_field !== false) {
            return this.value_field.split(',')
        }
    }

    get string() {
        switch (this.typeField) {
            case "selection":
                return this.props.value !== false && this.props.value !== ""
                    ? this.options.find((o) => o[0] === this.props.value)
                    : "";
            default:
                return "";
        }
    }

    get value() {
         const rawValue = this.props.value;
        return this.typeField === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    /**
     * @param {Event} ev
     */
    onChangeSelect(ev) {
       const value = JSON.parse(ev.target.value);
        switch (this.typeField) {
            case "selection":
                this.props.update(value);
                break;
        }
    }

}

WidgetType.template = "web.WidgetType";
WidgetType.props = {
    ...standardFieldProps,
    pickerOptions: {type: Object, optional: true},
    placeholder: {type: String, optional: true},
    inputType: {type: String, optional: true},
    step: {type: Number, optional: true},
};
WidgetType.defaultProps = {
    pickerOptions: {},
    inputType: "text",
};
WidgetType.components = {
    DatePicker,
};
WidgetType.supportedTypes = ["char"];

WidgetType.extractProps = ({attrs}) => {
    return {
        inputType: attrs.options.type,
        pickerOptions: attrs.options.datepicker,
        placeholder: attrs.placeholder,
    };
};
WidgetType.legacySpecialData = "_fetchSpecialRelation";

registry.category("fields").add("widget_type", WidgetType);