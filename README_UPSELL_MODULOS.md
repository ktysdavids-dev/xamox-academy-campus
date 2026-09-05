# Entrega · Comprar módulos que faltan desde el propio Campus

## Qué hace
Un alumno que compró un módulo suelto ahora ve en su Campus una sección
"Añade el resto del programa" con los módulos que le faltan, cada uno con
su precio y un botón "Comprar →" que le lleva directo al Payment Link de
Stripe de ESE módulo. Al pagar, el webhook (ya existente) le da acceso
automático — no hace falta nada manual.

Un alumno con el curso completo (Enrollment) no ve esta sección (ya lo
tiene todo).

## Archivos
NUEVO:
- core/migrations/0007_module_price_display_module_stripe_payment_link.py

MODIFICADOS:
- core/models.py     (+ Module.stripe_payment_link, Module.price_display)
- core/services.py   (+ get_purchasable_modules)
- core/views.py      (dashboard pasa purchasable_modules al contexto)
- templates/core/dashboard.html  (+ sección "Añade el resto del programa")
- core/management/commands/set_stripe_prices.py (+ --mN-link, --mN-price)

## Verificado con tests reales
- Comprador de 1 módulo -> ve los otros 3 con su link y precio correctos   OK
- No le ofrece comprar el que ya tiene                                     OK
- Comprador del curso completo -> no ve la sección (ya lo tiene todo)      OK

## Instalación
    git checkout -b feature/upsell-modulos-dashboard
    git add -A
    git commit -m "Mostrar y vender los modulos que faltan desde el dashboard del alumno"
    git push -u origin feature/upsell-modulos-dashboard
    # PR -> main -> mergear. Railway aplica la migracion 0007 sola.

## Configurar los links/precios en producción (un solo comando)
Dentro de railway ssh:
    python manage.py set_stripe_prices \
      --m1-link https://buy.stripe.com/cNi3cugxf2BG0vl1au6Na05 --m1-price "305 €" \
      --m2-link https://buy.stripe.com/4gMcN46WFfosce306q6Na04 --m2-price "405 €" \
      --m3-link https://buy.stripe.com/aFacN4cgZgswguj9H06Na03 --m3-price "405 €" \
      --m4-link https://buy.stripe.com/28EdR8dl35NS91R7yS6Na02 --m4-price "505 €"
(Los --m1..--m4 con los Price ID ya los pusiste antes; puedes omitirlos, este
comando solo actualiza lo que le pases.)
