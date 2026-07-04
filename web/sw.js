// Mudança para v3: Força a atualização do cache para carregar os módulos de Rastreabilidade
const CACHE_NAME = 'kippe-pwa-v3';
const APP_SHELL = [
    '/web/index.html',
    '/web/css/app.css',
    '/web/js/app.js',
    '/web/manifest.json'
];

self.addEventListener('install', (event) => {
    // Força a instalação imediata do novo Service Worker
    self.skipWaiting(); 
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Fazendo cache do App Shell V3');
            return cache.addAll(APP_SHELL);
        })
    );
});

self.addEventListener('activate', (event) => {
    // Assume o controle imediatamente nas abas abertas
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

