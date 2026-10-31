# Filtros de impuestos en facturas (`zub_invoice_tax_filters`)

Módulo para **Odoo 14 Enterprise** (funciona también en Community; solo depende de `account`).
Agrega 8 filtros a la vista de búsqueda de facturas (`account.move`), cada uno con su impuesto
configurable:

| Filtro | Una factura aparece si… |
|---|---|
| Al menos una línea con IVA 16% / IVA 0% / IVA Exento / IEPS 8% | alguna de sus líneas de producto lleva el impuesto configurado |
| Todas las líneas con IVA 16% / IVA 0% / IVA Exento / IEPS 8% | todas sus líneas de producto llevan el impuesto configurado |

- Una línea cuenta si **entre sus impuestos** está el configurado, aunque tenga otro
  (p. ej. una línea con IEPS 8% + IVA 16% cuenta para ambos).
- Solo cuentan las líneas de producto: secciones y notas se ignoran. Una factura sin líneas de
  producto no aparece en "Todas las líneas…".
- Se pueden activar **uno o varios filtros a la vez**; se combinan con **Y** (cada filtro reduce el
  resultado).

## Configuración

*Contabilidad › Configuración › Contabilidad › Filtros de impuestos* (grupo **Asesor**,
`account.group_account_manager`). Se crea un registro por filtro y se elige su **Impuesto**
(obligatorio, many2one a los impuestos nativos de Odoo). Un impuesto por filtro y por empresa.

Si se usa un filtro que no tiene impuesto configurado, Odoo muestra un aviso indicando dónde
configurarlo.

> La localización `l10n_mx` de Odoo 14 trae *IVA 16% VENTAS*, *IVA 0% VENTAS* e *IEPS 8% COMPRAS*,
> pero no trae *IVA Exento* ni *IEPS 8% VENTAS*: esos impuestos deben existir en la empresa para
> poder elegirlos. Como cada filtro usa un solo impuesto, uno de ventas filtra facturas de cliente y
> uno de compras filtra facturas de proveedor.

## No invasivo

- Los 8 campos agregados a `account.move` **no se almacenan** (sin columnas nuevas); solo se usan
  para buscar. No cambia ningún cálculo ni flujo de Odoo.
- La configuración vive en su propio modelo `zub.invoice.tax.filter`. Al desinstalar se borra solo
  esa configuración; facturas, líneas e impuestos no se tocan.
- Si se borra un impuesto configurado, su registro de filtro se borra con él (no bloquea a Odoo).

## Pruebas

```bash
odoo-bin -d <bd> -i l10n_mx,zub_invoice_tax_filters --test-tags /zub_invoice_tax_filters --stop-after-init
```

Usan el plan contable mexicano (`l10n_mx.mx_coa`) y sus impuestos nativos. Con líneas de 0 a 2
impuestos verifican cada filtro y cada par de filtros combinados contra un oráculo independiente,
en facturas de cliente y de proveedor, además de negación, aviso sin configuración, permisos y
multiempresa.

## Capturas

`static/description/`: configuración (01–02), menú de filtros (03), un filtro (04), dos filtros
combinados (05) y "Todas las líneas con IVA 16%" (06).
