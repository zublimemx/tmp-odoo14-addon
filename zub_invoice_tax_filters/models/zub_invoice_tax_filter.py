from odoo import fields, models

FILTER_TYPES = [
    ("any_iva16", "Al menos una línea con IVA 16%"),
    ("any_iva0", "Al menos una línea con IVA 0%"),
    ("any_iva_exento", "Al menos una línea con IVA Exento"),
    ("any_ieps8", "Al menos una línea con IEPS 8%"),
    ("all_iva16", "Todas las líneas con IVA 16%"),
    ("all_iva0", "Todas las líneas con IVA 0%"),
    ("all_iva_exento", "Todas las líneas con IVA Exento"),
    ("all_ieps8", "Todas las líneas con IEPS 8%"),
]


class ZubInvoiceTaxFilter(models.Model):
    """Impuesto que usa cada filtro de la lista de facturas, por empresa."""

    _name = "zub.invoice.tax.filter"
    _description = "Configuración de filtro de impuestos en facturas"
    _order = "company_id, filter_type"
    _rec_name = "filter_type"

    filter_type = fields.Selection(FILTER_TYPES, string="Filtro", required=True)
    tax_id = fields.Many2one(
        "account.tax", string="Impuesto", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        related="tax_id.company_id", store=True, string="Empresa"
    )

    _sql_constraints = [
        (
            "filter_company_uniq",
            "unique(filter_type, company_id)",
            "Cada filtro solo puede tener un impuesto por empresa.",
        ),
    ]
