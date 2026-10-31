from itertools import combinations

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

TAX_KEYS = ("iva16", "iva0", "iva_exento", "ieps8")
FILTERS = tuple("%s_%s" % (mode, key) for mode in ("any", "all") for key in TAX_KEYS)
# Casos básicos: cada línea lleva de 0 a 2 impuestos distintos.
ONE_LINE = [()] + [(k,) for k in TAX_KEYS] + list(combinations(TAX_KEYS, 2))
INVOICE_LINE_SETS = [(frozenset(taxes),) for taxes in ONE_LINE] + [
    tuple(frozenset(taxes) for taxes in lines)
    for lines in (
        # Todas las líneas con el mismo impuesto.
        [("iva16",), ("iva16",)],
        [("iva0",), ("iva0",)],
        [("iva_exento",), ("iva_exento",)],
        [("ieps8",), ("ieps8",)],
        # IEPS con o sin IVA: todas llevan IEPS, no todas IVA.
        [("ieps8", "iva16"), ("ieps8",)],
        [("ieps8", "iva0"), ("ieps8", "iva16")],
        # Todas con IVA 16%, una de ellas también con IEPS.
        [("iva16",), ("iva16", "ieps8")],
        # Impuestos mezclados: "al menos una" sí, "todas" no.
        [("iva16",), ("iva0",)],
        [("iva0",), ("iva_exento",)],
        [("iva_exento",), ("ieps8",)],
        [("iva16",), ()],
        [("iva16",), ("iva0",), ("iva_exento",)],
    )
]


def expected_match(filter_name, line_tax_sets):
    """Oráculo independiente del módulo: qué debe devolver cada filtro."""
    mode, key = filter_name.split("_", 1)
    found = [key in taxes for taxes in line_tax_sets]
    return any(found) if mode == "any" else all(found)


@tagged("post_install", "-at_install")
class TestInvoiceTaxFilters(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_mx.mx_coa"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]

        def mx_tax(name):
            return cls.env.ref("l10n_mx.%s_%s" % (company.id, name))

        # Impuestos nativos de l10n_mx. La localización de Odoo 14 no trae
        # "IVA Exento" ni "IEPS 8% VENTAS": se crean aquí como lo haría el cliente.
        iva0_sale, iva0_purchase = mx_tax("tax9"), mx_tax("tax13")
        ieps8_purchase = mx_tax("ieps_8_purchase")
        cls.sale_taxes = {
            "iva16": mx_tax("tax12"),
            "iva0": iva0_sale,
            "iva_exento": iva0_sale.copy({"name": "IVA EXENTO VENTAS"}),
            "ieps8": ieps8_purchase.copy({"name": "IEPS 8% VENTAS", "type_tax_use": "sale"}),
        }
        cls.purchase_taxes = {
            "iva16": mx_tax("tax14"),
            "iva0": iva0_purchase,
            "iva_exento": iva0_purchase.copy({"name": "IVA EXENTO COMPRAS"}),
            "ieps8": ieps8_purchase,
        }

        cls.invoices, cls.invoice_lines = cls._create_matrix("out_invoice", cls.sale_taxes)
        cls.bills, cls.bill_lines = cls._create_matrix("in_invoice", cls.purchase_taxes)
        cls._configure(cls.sale_taxes)

    @classmethod
    def _create_matrix(cls, move_type, taxes):
        vals_list = []
        for index, line_sets in enumerate(INVOICE_LINE_SETS):
            lines = [
                (0, 0, {
                    "name": "Línea %s" % ("+".join(sorted(tax_set)) or "sin impuestos"),
                    "quantity": 1,
                    "price_unit": 100,
                    "account_id": cls.company_data["default_account_revenue"].id,
                    "tax_ids": [(6, 0, [taxes[key].id for key in tax_set])],
                })
                for tax_set in line_sets
            ]
            if index % 3 == 0:
                # Secciones y notas no son líneas de producto: no deben contar.
                lines.insert(0, (0, 0, {"name": "Sección", "display_type": "line_section"}))
                lines.append((0, 0, {"name": "Nota", "display_type": "line_note"}))
            vals_list.append({
                "move_type": move_type,
                "partner_id": cls.partner_a.id,
                "invoice_date": "2021-01-01",
                "invoice_line_ids": lines,
            })
        moves = cls.env["account.move"].create(vals_list)
        return moves, dict(zip(moves.ids, INVOICE_LINE_SETS))

    @classmethod
    def _configure(cls, taxes):
        Filter = cls.env["zub.invoice.tax.filter"]
        Filter.search([("company_id", "=", cls.env.company.id)]).unlink()
        Filter.create([
            {"filter_type": name, "tax_id": taxes[name.split("_", 1)[1]].id} for name in FILTERS
        ])

    def _search(self, moves, filter_names, operator="="):
        domain = [("id", "in", moves.ids)]
        domain += [("zub_" + name, operator, True) for name in filter_names]
        return self.env["account.move"].search(domain)

    def _expected(self, moves, line_map, filter_names):
        return moves.filtered(
            lambda m: all(expected_match(name, line_map[m.id]) for name in filter_names)
        )

    def _check_matrix(self, moves, line_map):
        # Las líneas de cada factura llevan los impuestos que el oráculo supone.
        tax_to_key = {}
        for name in FILTERS:
            filter_rec = self.env["zub.invoice.tax.filter"].search([("filter_type", "=", name)])
            tax_to_key[filter_rec.tax_id] = name.split("_", 1)[1]
        for move in moves:
            got = sorted(
                frozenset(tax_to_key[t] for t in line.tax_ids)
                for line in move.invoice_line_ids.filtered(lambda l: not l.display_type)
            )
            self.assertEqual(got, sorted(line_map[move.id]))

        # Cada uno de los 8 filtros y cualquier par de ellos al mismo tiempo.
        for size in (1, 2):
            for combo in combinations(FILTERS, size):
                with self.subTest(filters=combo):
                    self.assertEqual(
                        self._search(moves, combo), self._expected(moves, line_map, combo)
                    )

        # El valor calculado del campo coincide con la búsqueda.
        for name in FILTERS:
            self.assertEqual(
                moves.filtered("zub_" + name), self._expected(moves, line_map, [name]), name
            )

    def test_matrix_customer_invoices(self):
        self._check_matrix(self.invoices, self.invoice_lines)

    def test_matrix_vendor_bills(self):
        self._configure(self.purchase_taxes)
        self._check_matrix(self.bills, self.bill_lines)

    def test_sale_taxes_do_not_match_bills(self):
        for name in FILTERS:
            self.assertFalse(self._search(self.bills, [name]), name)

    def test_negation(self):
        for name in FILTERS:
            self.assertEqual(
                self._search(self.invoices, [name], "!="),
                self.invoices - self._search(self.invoices, [name]),
            )

    def test_tax_change_is_reflected(self):
        self.env["zub.invoice.tax.filter"].search(
            [("filter_type", "=", "any_iva0")]
        ).tax_id = self.sale_taxes["ieps8"]
        self.assertEqual(
            self._search(self.invoices, ["any_iva0"]),
            self._search(self.invoices, ["any_ieps8"]),
        )

    def test_unconfigured_filter_raises(self):
        self.env["zub.invoice.tax.filter"].search([("filter_type", "=", "all_ieps8")]).unlink()
        with self.assertRaises(UserError):
            self._search(self.invoices, ["all_ieps8"])
        # Sin configuración el campo calculado vale Falso (no falla).
        self.assertFalse(self.invoices.filtered("zub_all_ieps8"))

    def test_tax_is_required_and_unique_per_company(self):
        Filter = self.env["zub.invoice.tax.filter"]
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception), self.cr.savepoint():
            Filter.create({"filter_type": "any_iva16"})
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception), self.cr.savepoint():
            Filter.create({"filter_type": "any_iva16", "tax_id": self.sale_taxes["iva0"].id})

    def test_billing_user_can_filter_but_not_configure(self):
        user = self.env["res.users"].create({
            "name": "Facturista",
            "login": "zub_billing",
            "groups_id": [(6, 0, [self.env.ref("account.group_account_invoice").id])],
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, self.env.company.ids)],
        })
        moves = self.env["account.move"].with_user(user).search(
            [("id", "in", self.invoices.ids), ("zub_any_iva0", "=", True)]
        )
        self.assertEqual(moves, self._search(self.invoices, ["any_iva0"]))
        with self.assertRaises(AccessError):
            self.env["zub.invoice.tax.filter"].with_user(user).create(
                {"filter_type": "any_iva16", "tax_id": self.sale_taxes["iva16"].id}
            )

    def test_other_company_configuration_is_independent(self):
        company_2 = self.company_data_2["company"]
        tax_2 = self.company_data_2["default_tax_sale"]
        filter_2 = self.env["zub.invoice.tax.filter"].create(
            {"filter_type": "any_iva16", "tax_id": tax_2.id}
        )
        self.assertEqual(filter_2.company_id, company_2)
        expected = self._expected(self.invoices, self.invoice_lines, ["any_iva16"])
        self.assertEqual(self._search(self.invoices, ["any_iva16"]), expected)
