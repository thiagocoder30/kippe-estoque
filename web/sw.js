const CACHE_NAME = 'kippe-pwa-v1';
const APP_SHELL = [
    '/web/index.html',
    '/web/css/app.css',
    '/web/js/app.js',
    '/web/manifest.json'
];

// Instalação: Salva o App Shell no cache
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Fazendo cache do App Shell');
            return cache.addAll(APP_SHELL);
        })
    );
});

// Ativação: Limpa caches antigos se a versão mudar
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        console.log('[Service Worker] Limpando cache antigo:', name);
                        return caches.delete(name);
                    }
                })
            );
        })
    );
});

// Interceptação de Rede (Cache First)
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
