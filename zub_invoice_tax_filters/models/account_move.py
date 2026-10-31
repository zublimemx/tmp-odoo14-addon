from odoo import fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

from .zub_invoice_tax_filter import FILTER_TYPES


class AccountMove(models.Model):
    _inherit = "account.move"

    # Campos no almacenados: solo sirven para los filtros de la vista de
    # búsqueda; no crean columnas ni modifican datos de las facturas.
    zub_any_iva16 = fields.Boolean(
        string="Al menos una línea con IVA 16%",
        compute="_compute_zub_tax_filters", search="_search_zub_any_iva16"
    )
    zub_any_iva0 = fields.Boolean(
        string="Al menos una línea con IVA 0%",
        compute="_compute_zub_tax_filters", search="_search_zub_any_iva0"
    )
    zub_any_iva_exento = fields.Boolean(
        string="Al menos una línea con IVA Exento",
        compute="_compute_zub_tax_filters", search="_search_zub_any_iva_exento"
    )
    zub_any_ieps8 = fields.Boolean(
        string="Al menos una línea con IEPS 8%",
        compute="_compute_zub_tax_filters", search="_search_zub_any_ieps8"
    )
    zub_all_iva16 = fields.Boolean(
        string="Todas las líneas con IVA 16%",
        compute="_compute_zub_tax_filters", search="_search_zub_all_iva16"
    )
    zub_all_iva0 = fields.Boolean(
        string="Todas las líneas con IVA 0%",
        compute="_compute_zub_tax_filters", search="_search_zub_all_iva0"
    )
    zub_all_iva_exento = fields.Boolean(
        string="Todas las líneas con IVA Exento",
        compute="_compute_zub_tax_filters", search="_search_zub_all_iva_exento"
    )
    zub_all_ieps8 = fields.Boolean(
        string="Todas las líneas con IEPS 8%",
        compute="_compute_zub_tax_filters", search="_search_zub_all_ieps8"
    )

    def _zub_filter_taxes(self, filter_type):
        """Impuestos configurados para el filtro en las empresas activas."""
        return (
            self.env["zub.invoice.tax.filter"]
            .sudo()
            .search(
                [
                    ("filter_type", "=", filter_type),
                    ("company_id", "in", self.env.companies.ids),
                ]
            )
            .tax_id
        )

    def _compute_zub_tax_filters(self):
        taxes = {key: self._zub_filter_taxes(key) for key, _label in FILTER_TYPES}
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            for key, _label in FILTER_TYPES:
                with_tax = lines.filtered(lambda l: l.tax_ids & taxes[key])
                if key.startswith("any_"):
                    value = bool(with_tax)
                else:
                    value = bool(lines) and with_tax == lines
                move["zub_%s" % key] = value

    def _zub_search_tax_filter(self, filter_type, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError("Operación no soportada en el filtro de impuestos.")
        taxes = self._zub_filter_taxes(filter_type)
        if not taxes:
            label = dict(FILTER_TYPES)[filter_type]
            raise UserError(
                "El filtro «%s» no tiene un impuesto configurado. Configúralo en "
                "Contabilidad › Configuración › Contabilidad › Filtros de impuestos." % label
            )
        lines = self.env["account.move.line"]
        product_lines = [
            ("exclude_from_invoice_tab", "=", False),
            ("display_type", "=", False),
        ]
        # Factura con al menos una línea de producto que incluye el impuesto
        # (la línea puede tener otros impuestos además del configurado).
        domain = [
            ("line_ids", "in", lines._search(product_lines + [("tax_ids", "in", taxes.ids)]))
        ]
        if filter_type.startswith("all_"):
            # ...y ninguna línea de producto sin el impuesto.
            domain.append(
                ("line_ids", "not in", lines._search(product_lines + [("tax_ids", "not in", taxes.ids)]))
            )
        if (operator == "=") != value:
            domain = ["!"] + expression.normalize_domain(domain)
        return domain

    def _search_zub_any_iva16(self, operator, value):
        return self._zub_search_tax_filter("any_iva16", operator, value)

    def _search_zub_any_iva0(self, operator, value):
        return self._zub_search_tax_filter("any_iva0", operator, value)

    def _search_zub_any_iva_exento(self, operator, value):
        return self._zub_search_tax_filter("any_iva_exento", operator, value)

    def _search_zub_any_ieps8(self, operator, value):
        return self._zub_search_tax_filter("any_ieps8", operator, value)

    def _search_zub_all_iva16(self, operator, value):
        return self._zub_search_tax_filter("all_iva16", operator, value)

    def _search_zub_all_iva0(self, operator, value):
        return self._zub_search_tax_filter("all_iva0", operator, value)

    def _search_zub_all_iva_exento(self, operator, value):
        return self._zub_search_tax_filter("all_iva_exento", operator, value)

    def _search_zub_all_ieps8(self, operator, value):
        return self._zub_search_tax_filter("all_ieps8", operator, value)
