/**
 * onesignal-handler.js
 * Manejo de notificaciones push con OneSignal Web SDK v16.
 * Reemplaza el antiguo fcm-handler.js de Firebase.
 */

let _oneSignalReady = false;

/**
 * Inicializa OneSignal con el App ID configurado.
 * Se llama automáticamente desde el template main.html.
 */
async function initOneSignal(appId) {
    if (!appId) {
        console.warn('[OneSignal] No se proporcionó App ID');
        return false;
    }

    try {
        await OneSignal.init({
            appId: appId,
            // No mostrar prompt automático — lo controlamos manualmente
            promptOptions: { autoPrompt: false },
            // Activa notificaciones en Safari también
            safari_web_id: "",
            // Ruta del Service Worker (debe estar en la raíz del dominio)
            serviceWorkerPath: "/OneSignalSDKWorker.js",
            serviceWorkerParam: { scope: "/" },
        });
        _oneSignalReady = true;
        console.log('[OneSignal] SDK inicializado correctamente');
        return true;
    } catch (error) {
        console.error('[OneSignal] Error al inicializar:', error);
        return false;
    }
}

/**
 * Solicita permiso de notificaciones y obtiene el Player ID.
 * Retorna el Player ID (string) o null si falla/rechaza.
 */
async function requestNotificationPermissionAndToken() {
    if (!_oneSignalReady) {
        console.warn('[OneSignal] SDK no inicializado');
        return null;
    }

    try {
        // Solicitar permiso al usuario
        await OneSignal.Notifications.requestPermission();

        const permission = await OneSignal.Notifications.permission;
        if (!permission) {
            console.log('[OneSignal] Permiso denegado');
            return null;
        }

        // Obtener el Player ID
        const playerId = await OneSignal.User.PushSubscription.id;

        if (playerId) {
            console.log('[OneSignal] Player ID obtenido:', playerId.substring(0, 20) + '...');
            return playerId;
        } else {
            console.warn('[OneSignal] No se pudo obtener el Player ID');
            return null;
        }

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
 * Flujo completo: inicializar → pedir permiso → guardar en servidor.
 * Compatible con la interfaz del antiguo setupNotifications() de FCM.
 */
async function setupNotifications() {
    const playerId = await requestNotificationPermissionAndToken();
    if (playerId) {
        return await saveTokenToServer(playerId);
    }
    return false;
}

// ── Utilidades ────────────────────────────────────────────────────────────────

function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    if (ua.includes('Firefox'))    browser = 'Firefox';
    else if (ua.includes('Edg'))   browser = 'Edge';
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

// Exponer funciones globalmente (compatible con llamadas desde main.html)
window.initOneSignal                        = initOneSignal;
window.requestNotificationPermissionAndToken = requestNotificationPermissionAndToken;
window.saveTokenToServer                    = saveTokenToServer;
window.setupNotifications                   = setupNotifications;

console.log('[OneSignal] Handler cargado correctamente');
