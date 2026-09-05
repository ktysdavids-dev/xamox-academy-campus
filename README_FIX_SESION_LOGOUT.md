# Fix · La sesión se cerraba sola en cada despliegue

## Causa real (no era "recordar sesión", era un bug)
`bootstrap_admin` corre en CADA arranque del contenedor (está en tu start
command, antes de gunicorn). Hacía `user.set_password(password)` sin
comprobar antes si hacía falta. `set_password()` genera un hash con una
sal aleatoria DISTINTA cada vez, aunque la contraseña en texto plano sea
la misma. Django usa ese hash para validar las sesiones abiertas
(`get_session_auth_hash`) — en cuanto el hash cambia, todas las sesiones
abiertas (la tuya) se invalidan automáticamente. Por eso te desloguea
justo después de cada actualización, no al azar.

## El fix
Ahora solo se llama a `set_password()` si la contraseña de verdad cambió
(`user.check_password(password)` primero). Si no cambió, no se toca nada
y tu sesión sobrevive al deploy.

## Verificado con Django real (no solo lectura de código)
- 3 "deploys" seguidos con la misma contraseña -> el hash NO cambia,
  el session_auth_hash tampoco -> la sesión sobrevive          OK
- Si cambias la contraseña de verdad -> se actualiza bien,
  la vieja deja de funcionar y la nueva sí                     OK

## Instalación
    git checkout -b fix/sesion-no-se-cierra-en-deploy
    git add -A
    git commit -m "Fix: bootstrap_admin ya no invalida la sesion en cada deploy"
    git push -u origin fix/sesion-no-se-cierra-en-deploy
    # PR -> main -> mergear

## Importante
Este fix soluciona el deslogueo en cada DEPLOY. Si además quieres sesiones
más largas para el día a día (aunque no haya deploys de por medio), dimelo
y añado SESSION_COOKIE_AGE más largo + un "recuérdame" real, pero eso es
una mejora aparte de este bug.
