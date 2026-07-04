/**
 * Módulo de Hardware Scanner (Integração com Câmera do Dispositivo).
 * Responsabilidade: Gerenciar permissões de vídeo, ler EAN/Código de Barras e emitir callbacks.
 */
export class ScannerManager {
    constructor(onScanSuccessCallback) {
        this.html5Qrcode = null;
        this.onScanSuccess = onScanSuccessCallback;
        this.modal = document.getElementById('scanner-modal');
        this.closeBtn = document.getElementById('close-scanner-btn');

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.stop());
        }
    }

    start() {
        if (!this.modal) return;
        
        // Exibe o modal em tela cheia (Overlay)
        this.modal.classList.remove('hidden');

        // Inicializa o leitor apontando para a div "reader"
        this.html5Qrcode = new Html5Qrcode("reader");
        
        // Configuração de alta performance para códigos de barras
        const config = { 
            fps: 10, 
            qrbox: { width: 250, height: 150 },
            aspectRatio: 1.0,
            formatsToSupport: [ Html5QrcodeSupportedFormats.EAN_13, Html5QrcodeSupportedFormats.CODE_128 ]
        };

        // facingMode: "environment" força o uso da câmera traseira principal
        this.html5Qrcode.start(
            { facingMode: "environment" },
            config,
            (decodedText, decodedResult) => {
                // SUCESSO: Para a leitura imediatamente
                this.stop();
                
                // Feedback Tátil (Vibração do celular se suportado)
                if (navigator.vibrate) navigator.vibrate(200);
                
                // Dispara o callback para o orquestrador (app.js)
                this.onScanSuccess(decodedText);
            },
            (errorMessage) => {
                // Ignora erros contínuos de enquadramento enquanto busca o código
            }
        ).catch((err) => {
            console.error("[SCANNER ERROR]", err);
            alert("Erro ao iniciar a câmera. Verifique as permissões do navegador.");
            this.stop();
        });
    }

    stop() {
        if (this.html5Qrcode) {
            this.html5Qrcode.stop().then(() => {
                this.html5Qrcode.clear();
                this.html5Qrcode = null;
            }).catch(err => console.error(err));
        }
        if (this.modal) this.modal.classList.add('hidden');
    }
}

