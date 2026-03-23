/**
 * onesignal-handler.js
 * Manejo de notificaciones push con OneSignal Web SDK v16.
 *
 * Correcciones aplicadas:
 * - initOneSignal devuelve una Promise que resuelve cuando el SDK
 *   está realmente listo, evitando race conditions con el defer del script.
 * - setupNotifications espera a que el SDK esté listo antes de continuar.
 * - Reintento automático: si el usuario ya tiene permiso concedido pero
 *   el token no está en el servidor, lo sincroniza en cada carga de página.
 * - subscriptionchange listener: si OneSignal asigna un nuevo Player ID
 *   lo guarda en el servidor de inmediato.
 */

// Promesa global que resuelve cuando OneSignal está listo
let _oneSignalReadyPromise = null;
let _oneSignalReady = false;

/**
 * Inicializa OneSignal. Puede llamarse varias veces sin problema
 * (devuelve la misma promesa si ya fue invocado).
 */
function initOneSignal(appId) {
    if (_oneSignalReadyPromise) return _oneSignalReadyPromise;

    if (!appId) {
        console.warn('[OneSignal] No se proporcionó App ID');
        _oneSignalReadyPromise = Promise.resolve(false);
        return _oneSignalReadyPromise;
    }

    _oneSignalReadyPromise = new Promise((resolve) => {
        // El script de OneSignal puede llegar después (defer).
        // Esperamos hasta que window.OneSignal esté disponible.
        const MAX_WAIT_MS = 10000;
        const POLL_MS = 100;
        let waited = 0;

        const waitForSDK = setInterval(async () => {
            waited += POLL_MS;

            if (typeof window.OneSignal === 'undefined') {
                if (waited >= MAX_WAIT_MS) {
                    clearInterval(waitForSDK);
                    console.error('[OneSignal] SDK no cargó en ' + MAX_WAIT_MS + 'ms');
                    resolve(false);
                }
                return;
            }

            clearInterval(waitForSDK);

            try {
                await window.OneSignal.init({
                    appId: appId,
                    promptOptions: { autoPrompt: false },
                    safari_web_id: "",
                    serviceWorkerPath: "/OneSignalSDKWorker.js",
                    serviceWorkerParam: { scope: "/" },
                });

                _oneSignalReady = true;
                console.log('[OneSignal] SDK inicializado correctamente');

                // Escuchar cambios de suscripción (nuevo Player ID asignado)
                window.OneSignal.User.PushSubscription.addEventListener(
                    'change',
                    async (event) => {
                        const newId = event.current?.id;
                        if (newId) {
                            console.log('[OneSignal] Player ID actualizado, guardando en servidor...');
                            await saveTokenToServer(newId);
                        }
                    }
                );

                resolve(true);
            } catch (error) {
                console.error('[OneSignal] Error al inicializar:', error);
                resolve(false);
            }
        }, POLL_MS);
    });

    return _oneSignalReadyPromise;
}

/**
 * Solicita permiso de notificaciones y obtiene el Player ID.
 * Retorna el Player ID (string) o null si falla/rechaza.
 */
async function requestNotificationPermissionAndToken() {
    const ready = await _oneSignalReadyPromise;
    if (!ready) {
        console.warn('[OneSignal] SDK no inicializado');
        return null;
    }

    try {
        await window.OneSignal.Notifications.requestPermission();

        const permission = await window.OneSignal.Notifications.permission;
        if (!permission) {
            console.log('[OneSignal] Permiso denegado');
            return null;
        }

        // Esperar hasta 3s a que OneSignal asigne el Player ID
        for (let i = 0; i < 30; i++) {
            const playerId = await window.OneSignal.User.PushSubscription.id;
            if (playerId) {
                console.log('[OneSignal] Player ID obtenido:', playerId.substring(0, 20) + '...');
                return playerId;
            }
            await new Promise(r => setTimeout(r, 100));
        }

        console.warn('[OneSignal] No se pudo obtener el Player ID tras esperar');
        return null;

    } catch (error) {
        console.error('[OneSignal] Error al solicitar permiso:', error);
        return null;
    }
}

/**
 * Guarda el Player ID en el servidor Django.
 */
async function saveTokenToServer(playerId) {
    try {
        const response = await fetch('/notificaciones/api/guardar-token-fcm/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                token: playerId,
                nombre_dispositivo: getBrowserInfo(),
                sistema_operativo: 'Web',
            }),
        });

        const data = await response.json();
        if (response.ok) {
            console.log('[OneSignal] Player ID guardado en servidor:', data.message);
            return true;
        } else {
            console.error('[OneSignal] Error al guardar Player ID:', data);
            return false;
        }
    } catch (error) {
        console.error('[OneSignal] Error en fetch guardar Player ID:', error);
        return false;
    }
}

/**
 * Flujo completo: pedir permiso → obtener Player ID → guardar en servidor.
 */
async function setupNotifications() {
    const playerId = await requestNotificationPermissionAndToken();
    if (playerId) {
        return await saveTokenToServer(playerId);
    }
    return false;
}

/**
 * Registro automático silencioso.
 * Si el usuario ya tiene permiso concedido, obtiene el Player ID
 * y lo envía al servidor sin mostrar ningún prompt.
 * Se llama en cada carga de página para mantener el token sincronizado.
 */
async function autoSyncToken() {
    const ready = await _oneSignalReadyPromise;
    if (!ready) return;

    const permission = await window.OneSignal.Notifications.permission;
    if (!permission) return;

    // Esperar hasta 3s a que OneSignal tenga el ID listo
    for (let i = 0; i < 30; i++) {
        const playerId = await window.OneSignal.User.PushSubscription.id;
        if (playerId) {
            await saveTokenToServer(playerId);
            return;
        }
        await new Promise(r => setTimeout(r, 100));
    }
    console.warn('[OneSignal] autoSyncToken: no se pudo obtener Player ID');
}

// ── Utilidades ────────────────────────────────────────────────────────────────

function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    if (ua.includes('Firefox'))     browser = 'Firefox';
    else if (ua.includes('Edg'))    browser = 'Edge';
    else if (ua.includes('Chrome')) browser = 'Chrome';
    else if (ua.includes('Safari')) browser = 'Safari';
    return `${browser} - ${navigator.platform}`;
}

function getCookie(name) {
    for (const cookie of document.cookie.split(';')) {
        const c = cookie.trim();
        if (c.startsWith(name + '=')) {
            return decodeURIComponent(c.substring(name.length + 1));
        }
    }
    return null;
}

// Exponer funciones globalmente
window.initOneSignal                         = initOneSignal;
window.requestNotificationPermissionAndToken = requestNotificationPermissionAndToken;
window.saveTokenToServer                     = saveTokenToServer;
window.setupNotifications                    = setupNotifications;
window.autoSyncToken                         = autoSyncToken;

console.log('[OneSignal] Handler cargado correctamente');