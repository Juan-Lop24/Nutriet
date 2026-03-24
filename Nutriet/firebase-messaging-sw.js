importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyCP7LywDqDvbYawIPRZabt5gFbn5DIoxho",
    messagingSenderId: "758388755200",
    projectId: "sanguine-robot-478914-g6",
    appId: "1:758388755200:web:ec3a7b927378dc551b81e5"
});

const messaging = firebase.messaging();

// ─── Helper para mostrar notificación ────────────────────────────────────────
function mostrarNotificacion(payload) {
    const data = payload.data || {};
    const notif = payload.notification || {};

    const title = notif.title || data.title || 'Nutriet';
    const body  = notif.body  || data.body  || '';
    const url   = data.url || notif.click_action || '/';

    const options = {
        body:               body,
        icon:               '/static/images/logo.png',
        tag:                'nutriet-' + (data.tipo || 'msg') + '-' + Date.now(),
        requireInteraction: false,
        vibrate:            [200, 100, 200],
        data:               { url: url, ...data },
    };

    return self.registration.showNotification(title, options);
}

// ─── Mensaje en SEGUNDO PLANO (app cerrada o en otra pestaña) ─────────────────
messaging.onBackgroundMessage(function(payload) {
    console.log('[SW] Background message:', payload);
    return mostrarNotificacion(payload);
});

// ─── Fallback: evento push directo (captura mensajes que FCM no intercepta) ──
// Esto garantiza que NUNCA se pierda una notificación aunque Firebase falle
self.addEventListener('push', function(event) {
    console.log('[SW] Push event recibido');

    let payload = {};
    try {
        if (event.data) {
            payload = event.data.json();
        }
    } catch (e) {
        console.warn('[SW] No se pudo parsear push data:', e);
    }

    // Solo mostrar si Firebase no lo está manejando ya (evitar duplicados)
    // Firebase maneja los mensajes con notification payload automáticamente,
    // pero los data-only los delega a onBackgroundMessage.
    // El evento 'push' es el último recurso.
    if (!payload.notification && !payload.data) {
        // Notificación genérica de fallback
        event.waitUntil(
            self.registration.showNotification('NutriET', {
                body: 'Tienes una nueva notificación',
                icon: '/static/images/logo.png',
                tag: 'nutriet-fallback-' + Date.now(),
            })
        );
    }
});

// ─── Click en la notificación ─────────────────────────────────────────────────
self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    const url = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            // Si ya hay una pestaña abierta con la app, navegar ahí
            for (let client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            // Si no hay pestaña abierta, abrir una nueva
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
