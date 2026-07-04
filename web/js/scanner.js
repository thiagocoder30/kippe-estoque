/**
 * Módulo de Hardware Scanner (Versão Definitiva Enterprise).
 * Resolvido o Memory Lock de Anti-Spam: a câmera agora permite bipar o mesmo EAN infinitas vezes.
 */
export class ScannerManager {
    constructor(onScanSuccessCallback) {
        this.onScanSuccess = onScanSuccessCallback;
        this.modal = document.getElementById('scanner-modal');
        this.closeBtn = document.getElementById('close-scanner-btn');
        this.status = "IDLE";
        this.html5Qrcode = null; 

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.stop());
        }
    }

    async start() {
        if (!this.modal || this.status === "STARTING" || this.status === "SCANNING") {
            return;
        }
        
        if (this.status === "STOPPING") {
            setTimeout(() => this.start(), 300);
            return;
        }

        this.status = "STARTING";
        this.modal.classList.remove('hidden');

        // A MÁGICA DA AMNÉSIA: Destruímos e recriamos a instância a cada abertura
        // Isso burla o sistema anti-spam da biblioteca, permitindo ler o mesmo SKU em sequência.
        if (this.html5Qrcode) {
            try { await this.html5Qrcode.clear(); } catch(e) {}
        }
        this.html5Qrcode = new Html5Qrcode("reader");

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
                    if (this.status === "SCANNING") {
                        if (navigator.vibrate) navigator.vibrate(200);
                        this.stop(); 
                        this.onScanSuccess(decodedText);
                    }
                },
                (errorMessage) => { /* Silenciado para não poluir o console com reenquadramentos */ }
            );
            this.status = "SCANNING";
        } catch (err) {
            console.error("[SCANNER ERROR]", err);
            this.status = "IDLE";
            this.stop();
            alert("Não foi possível acessar a câmera. Verifique as permissões.");
        }
    }

    stop() {
        if (this.status === "IDLE" || this.status === "STOPPING") return;
        
        this.status = "STOPPING"; 
        if (this.modal) this.modal.classList.add('hidden');
        
        if (this.html5Qrcode) {
            this.html5Qrcode.stop().then(() => {
                this.html5Qrcode.clear();
                this.html5Qrcode = null; // Limpeza absoluta da memória
                this.status = "IDLE";
            }).catch(e => {
                console.error("Erro ao desligar a lente:", e);
                this.html5Qrcode = null;
                this.status = "IDLE";
            });
        } else {
            this.status = "IDLE";
        }
    }
}

