// Registro do Service Worker para habilitar o PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/web/sw.js')
            .then((registration) => {
                console.log('[KIPPE APP] Service Worker registrado com sucesso. Escopo:', registration.scope);
            })
            .catch((error) => {
                console.error('[KIPPE APP] Falha ao registrar o Service Worker:', error);
            });
    });
}
