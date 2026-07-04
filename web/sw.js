// Versão v7: Ciclo Operacional Completo (Transferência e Ajustes)
const CACHE_NAME = 'kippe-pwa-v7';
const APP_SHELL = [
    '/web/index.html',
    '/web/css/app.css',
    '/web/js/app.js',
    '/web/js/api.js',
    '/web/js/ui.js',
    '/web/js/router.js',
    '/web/js/scanner.js',
    '/web/manifest.json',
    'https://unpkg.com/html5-qrcode'
];

self.addEventListener('install', (event) => {
    self.skipWaiting(); 
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Fazendo cache do App Shell V7 (Full Operations)');
            return cache.addAll(APP_SHELL);
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        console.log('[Service Worker] Destruindo cache antigo:', name);
                        return caches.delete(name);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});

