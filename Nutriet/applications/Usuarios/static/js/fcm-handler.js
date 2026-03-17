// fcm-handler.js — Manejador de Firebase Cloud Messaging
// Funciona con script tags normales (sin módulos ES6)

let firebaseApp = null;
let messaging = null;
let firebaseConfig = null;
let vapidKey = null;

function initFirebase(config, vapid) {
    firebaseConfig = config;
    vapidKey = vapid;
    console.log('[FCM] Config inicializada');
}

async function requestNotificationPermissionAndToken() {
    try {
        if (!('Notification' in window)) {
            console.warn('[FCM] El navegador no soporta notificaciones');
            return null;
        }
        if (!('serviceWorker' in navigator)) {
            console.warn('[FCM] El navegador no soporta Service Workers');
            return null;
        }

        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('[FCM] Permiso denegado');
            return null;
        }
        console.log('[FCM] Permiso concedido');

        // Registrar/actualizar el Service Worker
        const registration = await navigator.serviceWorker.register(
            '/firebase-messaging-sw.js',
            { scope: '/' }
        );
        console.log('[FCM] Service Worker registrado:', registration.scope);

        // Esperar a que esté activo
        await navigator.serviceWorker.ready;

        // Inicializar Firebase (solo una vez)
        if (!firebaseApp) {
            firebaseApp = firebase.initializeApp(firebaseConfig);
        }
        messaging = firebase.messaging(firebaseApp);

        // Obtener token FCM
        const currentToken = await messaging.getToken({
            vapidKey: vapidKey,
            serviceWorkerRegistration: registration
        });

        if (currentToken) {
            console.log('[FCM] Token obtenido:', currentToken.substring(0, 20) + '...');
            return currentToken;
        } else {
            console.warn('[FCM] No se pudo obtener el token');
            return null;
        }

    } catch (error) {
        console.error('[FCM] Error al obtener token:', error);
        return null;
    }
}

async function saveTokenToServer(token) {
    try {
        const response = await fetch('/notificaciones/api/guardar-token-fcm/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                token: token,
                nombre_dispositivo: getBrowserInfo(),
                sistema_operativo: 'Web'
            })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('[FCM] Token guardado en servidor:', data.message);
            return true;
        } else {
            console.error('[FCM] Error al guardar token:', data);
            return false;
        }
    } catch (error) {
        console.error('[FCM] Error en fetch guardar token:', error);
        return false;
    }
}

function listenToForegroundMessages() {
    if (!messaging) {
        console.error('[FCM] messaging no inicializado');
        return;
    }

    messaging.onMessage(async (payload) => {
        console.log('[FCM] Mensaje en primer plano recibido:', payload);

        const title = (payload.notification && payload.notification.title)
            || (payload.data && payload.data.title)
            || 'NutriET';

        const body = (payload.notification && payload.notification.body)
            || (payload.data && payload.data.body)
            || '';

        const url = (payload.data && payload.data.url) || '/';

        if (Notification.permission === 'granted') {
            try {
                // Usar el Service Worker para mostrar la notificación en primer plano
                // new Notification() desde una página web puede ser bloqueado por Chrome
                const registration = await navigator.serviceWorker.ready;
                await registration.showNotification(title, {
                    body: body,
                    icon: '/static/images/logo.png',
                    tag: 'nutriet-fg-' + Date.now(),
                    requireInteraction: false,
                    data: { url: url, ...(payload.data || {}) },
                });
            } catch (e) {
                // Fallback a new Notification si el SW falla
                console.warn('[FCM] SW showNotification falló, usando new Notification:', e);
                new Notification(title, {
                    body: body,
                    icon: '/static/images/logo.png',
                });
            }
        }
    });
}

async function setupNotifications() {
    const token = await requestNotificationPermissionAndToken();
    if (token) {
        const saved = await saveTokenToServer(token);
        if (saved) {
            listenToForegroundMessages();
            return true;
        }
    }
    return false;
}

function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    if (ua.includes('Firefox')) browser = 'Firefox';
    else if (ua.includes('Edg')) browser = 'Edge';
    else if (ua.includes('Chrome')) browser = 'Chrome';
    else if (ua.includes('Safari')) browser = 'Safari';
    return `${browser} - ${navigator.platform}`;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        for (const cookie of document.cookie.split(';')) {
            const c = cookie.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Exponer funciones globalmente
window.initFirebase = initFirebase;
window.requestNotificationPermissionAndToken = requestNotificationPermissionAndToken;
window.saveTokenToServer = saveTokenToServer;
window.listenToForegroundMessages = listenToForegroundMessages;
window.setupNotifications = setupNotifications;

console.log('[FCM] Handler cargado correctamente');
