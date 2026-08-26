/**
 * Módulo de Hardware Scanner.
 *
 * Responsabilidade:
 * - controlar uma única instância de câmera;
 * - oferecer leitura confiável de códigos de barras no mobile;
 * - evitar estado residual entre aberturas do scanner.
 */
export class ScannerManager {
    constructor(onScanSuccessCallback) {
        this.onScanSuccess = onScanSuccessCallback;
        this.modal = document.getElementById('scanner-modal');
        this.closeBtn = document.getElementById('close-scanner-btn');
        this.status = "IDLE";
        this.html5Qrcode = null;

        if (this.closeBtn) {
            this.closeBtn.addEventListener(
                'click',
                () => this.stop()
            );
        }
    }

    async start() {
        if (
            !this.modal ||
            this.status === "STARTING" ||
            this.status === "SCANNING"
        ) {
            return;
        }

        if (this.status === "STOPPING") {
            setTimeout(
                () => this.start(),
                300
            );
            return;
        }

        this.status = "STARTING";
        this.modal.classList.remove('hidden');

        if (this.html5Qrcode) {
            try {
                await this.html5Qrcode.clear();
            } catch (error) {
                console.warn(
                    "[SCANNER CLEANUP]",
                    error
                );
            }
        }

        this.html5Qrcode = new Html5Qrcode("reader");

        const config = {
            fps: 15,

            qrbox: (viewfinderWidth, viewfinderHeight) => {
                const width = Math.floor(
                    viewfinderWidth * 0.9
                );

                const height = Math.floor(
                    Math.min(
                        160,
                        viewfinderHeight * 0.45
                    )
                );

                return {
                    width: width,
                    height: height,
                };
            },

            aspectRatio: 1.777778,
        };

        try {
            await this.html5Qrcode.start(
                {
                    facingMode: {
                        exact: "environment"
                    }
                },
                config,
                (decodedText) => {
                    if (this.status !== "SCANNING") {
                        return;
                    }

                    if (navigator.vibrate) {
                        navigator.vibrate(200);
                    }

                    this.stop();
                    this.onScanSuccess(decodedText);
                },
                () => {
                    /*
                     * Erros de enquadramento/decodificação são esperados
                     * enquanto a câmera procura um código válido.
                     */
                }
            );

            this.status = "SCANNING";
        } catch (error) {
            console.error(
                "[SCANNER ERROR]",
                error
            );

            if (this.modal) {
                this.modal.classList.add('hidden');
            }

            if (this.html5Qrcode) {
                try {
                    await this.html5Qrcode.clear();
                } catch (clearError) {
                    console.warn(
                        "[SCANNER CLEANUP]",
                        clearError
                    );
                }
            }

            this.html5Qrcode = null;
            this.status = "IDLE";

            alert(
                "Não foi possível acessar a câmera. " +
                "Verifique as permissões."
            );
        }
    }

    stop() {
        if (
            this.status === "IDLE" ||
            this.status === "STOPPING"
        ) {
            return;
        }

        this.status = "STOPPING";

        if (this.modal) {
            this.modal.classList.add('hidden');
        }

        if (!this.html5Qrcode) {
            this.status = "IDLE";
            return;
        }

        this.html5Qrcode
            .stop()
            .then(async () => {
                try {
                    await this.html5Qrcode.clear();
                } catch (error) {
                    console.warn(
                        "[SCANNER CLEANUP]",
                        error
                    );
                }

                this.html5Qrcode = null;
                this.status = "IDLE";
            })
            .catch((error) => {
                console.error(
                    "Erro ao desligar a lente:",
                    error
                );

                this.html5Qrcode = null;
                this.status = "IDLE";
            });
    }
}
