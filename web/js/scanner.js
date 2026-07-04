/**
 * Módulo de Hardware Scanner (Resolvido o bug de instâncias duplicadas).
 */
export class ScannerManager {
    constructor(onScanSuccessCallback) {
        this.html5Qrcode = null;
        this.onScanSuccess = onScanSuccessCallback;
        this.modal = document.getElementById('scanner-modal');
        this.closeBtn = document.getElementById('close-scanner-btn');
        this.isScanning = false;

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.stop());
        }
    }

    async start() {
        if (!this.modal || this.isScanning) return;
        this.modal.classList.remove('hidden');
        this.isScanning = true;

        // Se a instância não existe, cria. Se existe, reutiliza a limpeza.
        if (!this.html5Qrcode) {
            this.html5Qrcode = new Html5Qrcode("reader");
        }

        const config = { 
            fps: 10, 
            qrbox: { width: 250, height: 150 },
            formatsToSupport: [ Html5QrcodeSupportedFormats.EAN_13, Html5QrcodeSupportedFormats.CODE_128 ]
        };
        
        try {
            await this.html5Qrcode.start(
                { facingMode: "environment" },
                config,
                (decodedText) => {
                    if (this.isScanning) {
                        this.stop(); // Para o hardware imediatamente
                        if (navigator.vibrate) navigator.vibrate(200);
                        this.onScanSuccess(decodedText);
                    }
                },
                (errorMessage) => { /* Ignorar avisos naturais de reenquadramento contínuo */ }
            );
        } catch (err) {
            console.error("[SCANNER ERROR]", err);
            alert("Erro ao aceder à câmara. Verifique as permissões do navegador.");
            this.stop();
        }
    }

    stop() {
        this.isScanning = false;
        if (this.modal) this.modal.classList.add('hidden');
        
        if (this.html5Qrcode) {
            this.html5Qrcode.stop().then(() => {
                this.html5Qrcode.clear();
                this.html5Qrcode = null; // Limpa o ponteiro para a memória (Fix do Bug)
            }).catch(err => {
                console.error("Erro ao fechar scanner:", err);
                this.html5Qrcode.clear();
                this.html5Qrcode = null;
            });
        }
    }
}

