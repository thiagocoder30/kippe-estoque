import { APIClient } from './api.js';

class KippeApplication {
    constructor() {
        // Inicializa APENAS a API. Ignoramos a UI antiga (ui.js) para evitar crash.
        this.api = new APIClient();
        
        // Ativação do Bypass de Login imediatamente
        localStorage.setItem('kippe_operator', 'ADMIN (BYPASS)');
        localStorage.setItem('kippe_role', 'ADMIN');
    }

    async bootstrap() {
        console.log('[KIPPE SPRINT 1] Sistema Operacional Iniciado e Blindado.');
        
        // Registra o novo Service Worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/web/sw.js').catch(e => console.error(e));
        }

        // Liga o campo de Busca Rápida (Prova de Vida JS)
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                const val = searchInput.value.trim();
                if (val) {
                    alert(`O motor JS está 100% liso!\n\nNa Sprint 2, esse botão vai puxar do banco de dados o SKU: ${val}`);
                } else {
                    alert("Digite um código ou nome para buscar.");
                }
            });
        }
    }
}

// Inicializa a aplicação quando o HTML estiver totalmente carregado
document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
