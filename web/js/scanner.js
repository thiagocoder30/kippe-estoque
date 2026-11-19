/**
 * KIPPE WMS - Scanner Manager
 *
 * SCANNER-RECOVERY-003
 *
 * Arquitetura canônica:
 * - engine único: html5-qrcode;
 * - EAN-13 e CODE-128;
 * - seleção explícita de câmera por deviceId;
 * - persistência da câmera preferida do dispositivo;
 * - fallback seguro quando a câmera armazenada não existir;
 * - recriação integral do decoder a cada abertura;
 * - sem BarcodeDetector, ZXing, Quagga2 ou captura fotográfica.
 */
export class ScannerManager {
    static STORAGE_KEY =
        'kippe.scanner.preferredCameraId';

    constructor(onScanSuccessCallback) {
        this.onScanSuccess =
            onScanSuccessCallback;

        this.modal =
            document.getElementById(
                'scanner-modal'
            );

        this.closeBtn =
            document.getElementById(
                'close-scanner-btn'
            );

        this.reader =
            document.getElementById(
                'reader'
            );

        this.status =
            'IDLE';

        this.html5Qrcode =
            null;

        this.selectedCameraId =
            null;

        this.cameraSelector =
            null;

        if (this.closeBtn) {
            this.closeBtn.addEventListener(
                'click',
                () => this.stop()
            );
        }
    }

    getStoredCameraId() {
        try {
            return (
                window.localStorage.getItem(
                    ScannerManager.STORAGE_KEY
                ) || null
            );
        } catch (error) {
            console.warn(
                '[SCANNER STORAGE READ]',
                error
            );

            return null;
        }
    }

    storeCameraId(cameraId) {
        if (!cameraId) {
            return;
        }

        try {
            window.localStorage.setItem(
                ScannerManager.STORAGE_KEY,
                cameraId
            );
        } catch (error) {
            console.warn(
                '[SCANNER STORAGE WRITE]',
                error
            );
        }
    }

    async getAvailableCameras() {
        if (
            typeof Html5Qrcode ===
                'undefined' ||
            typeof Html5Qrcode.getCameras !==
                'function'
        ) {
            throw new Error(
                'Enumeração de câmeras indisponível.'
            );
        }

        const cameras =
            await Html5Qrcode.getCameras();

        if (
            !Array.isArray(cameras) ||
            cameras.length === 0
        ) {
            throw new Error(
                'Nenhuma câmera disponível.'
            );
        }

        return cameras;
    }

    resolvePreferredCamera(
        cameras
    ) {
        const storedCameraId =
            this.getStoredCameraId();

        if (storedCameraId) {
            const storedCamera =
                cameras.find(
                    (camera) =>
                        camera.id ===
                        storedCameraId
                );

            if (storedCamera) {
                return storedCamera;
            }
        }

        if (this.selectedCameraId) {
            const currentCamera =
                cameras.find(
                    (camera) =>
                        camera.id ===
                        this.selectedCameraId
                );

            if (currentCamera) {
                return currentCamera;
            }
        }

        const rearCandidates = cameras.filter((cam) => {
            const lbl = String(cam.label || '').toLowerCase();
            const isBack = /back|rear|traseira|environment|facing back/.test(lbl);
            const isAux = /front|frontal|wide|ultra|macro|depth|tele/.test(lbl);
            return isBack && !isAux;
        });
        if (rearCandidates.length > 0) {
            return rearCandidates[0];
        }

        const anyBack = cameras.find((cam) =>
            /back|rear|traseira|environment/.test(String(cam.label || '').toLowerCase())
        );
        if (anyBack) {
            return anyBack;
        }

        return cameras[0];
    }

    async ensureCameraSelector() {
        if (
            !this.modal ||
            !this.reader
        ) {
            return;
        }

        let wrapper =
            document.getElementById(
                'scanner-camera-selector-wrapper'
            );

        let selector =
            document.getElementById(
                'scanner-camera-selector'
            );

        if (!wrapper) {
            wrapper =
                document.createElement(
                    'div'
                );

            wrapper.id =
                'scanner-camera-selector-wrapper';

            wrapper.style.background =
                '#000000';

            wrapper.style.padding =
                '8px 12px';

            wrapper.style.color =
                '#ffffff';

            wrapper.style.flexShrink =
                '0';

            const label =
                document.createElement(
                    'div'
                );

            label.textContent =
                'CÂMERA DO SCANNER';

            label.style.fontSize =
                '10px';

            label.style.fontWeight =
                '700';

            label.style.letterSpacing =
                '0.08em';

            label.style.marginBottom =
                '4px';

            selector =
                document.createElement(
                    'select'
                );

            selector.id =
                'scanner-camera-selector';

            selector.style.width =
                '100%';

            selector.style.padding =
                '8px';

            selector.style.color =
                '#111827';

            selector.style.background =
                '#ffffff';

            selector.style.border =
                '1px solid #374151';

            selector.style.borderRadius =
                '6px';

            selector.style.fontSize =
                '12px';

            selector.addEventListener(
                'change',
                async (event) => {
                    const cameraId =
                        event.target.value;

                    if (!cameraId) {
                        return;
                    }

                    if (
                        cameraId ===
                        this.selectedCameraId
                    ) {
                        return;
                    }

                    this.selectedCameraId =
                        cameraId;

                    this.storeCameraId(
                        cameraId
                    );

                    if (
                        this.status ===
                        'SCANNING'
                    ) {
                        await this.stop(
                            false
                        );

                        await this.start();
                    }
                }
            );

            wrapper.appendChild(
                label
            );

            wrapper.appendChild(
                selector
            );

            this.reader.before(
                wrapper
            );
        }

        this.cameraSelector =
            selector;

        const cameras =
            await this.getAvailableCameras();

        const preferredCamera =
            this.resolvePreferredCamera(
                cameras
            );

        this.selectedCameraId =
            preferredCamera.id;

        /*
         * Depois que uma câmera válida é resolvida,
         * ela passa a ser a preferência persistente.
         */
        this.storeCameraId(
            preferredCamera.id
        );

        selector.innerHTML =
            '';

        cameras.forEach(
            (camera, index) => {
                const option =
                    document.createElement(
                        'option'
                    );

                option.value =
                    camera.id;

                option.textContent =
                    camera.label ||
                    `CÂMERA ${index + 1}`;

                option.selected =
                    camera.id ===
                    this.selectedCameraId;

                selector.appendChild(
                    option
                );
            }
        );

        selector.value =
            this.selectedCameraId;
    }

    async setupOpticalControls() {
        try {
            if (!this.html5Qrcode) return;
            await this.html5Qrcode.applyVideoConstraints({
                advanced: [{ focusMode: 'continuous' }]
            }).catch(() => {});

            const caps = typeof this.html5Qrcode.getRunningTrackCapabilities === 'function'
                ? this.html5Qrcode.getRunningTrackCapabilities()
                : {};

            let bar = document.getElementById('scanner-optical-controls');
            const wrapper = document.getElementById('scanner-camera-selector-wrapper');
            if (!bar && wrapper) {
                bar = document.createElement('div');
                bar.id = 'scanner-optical-controls';
                bar.style.cssText = 'display:flex;gap:8px;margin-top:8px;';
                wrapper.appendChild(bar);
            }
            if (!bar) return;
            bar.innerHTML = '';

            if (caps && caps.torch) {
                let torchOn = false;
                const torchBtn = document.createElement('button');
                torchBtn.type = 'button';
                torchBtn.textContent = '🔦 LANTERNA: OFF';
                torchBtn.style.cssText = 'flex:1;padding:7px 10px;border-radius:6px;border:1px solid #4B5563;background:#1F2937;color:#F9FAFB;font-size:11px;font-weight:800;letter-spacing:0.04em;';
                torchBtn.addEventListener('click', async () => {
                    torchOn = !torchOn;
                    try {
                        await this.html5Qrcode.applyVideoConstraints({
                            advanced: [{ torch: torchOn }]
                        });
                        torchBtn.textContent = torchOn ? '🔦 LANTERNA: ON' : '🔦 LANTERNA: OFF';
                        torchBtn.style.background = torchOn ? '#D97706' : '#1F2937';
                    } catch (_) {
                        torchOn = false;
                    }
                });
                bar.appendChild(torchBtn);
            }

            if (caps && caps.zoom && typeof caps.zoom.max === 'number' && caps.zoom.max >= 1.5) {
                let zoomed = false;
                const targetZoom = Math.min(2.0, caps.zoom.max);
                const zoomBtn = document.createElement('button');
                zoomBtn.type = 'button';
                zoomBtn.textContent = '🔍 ZOOM: 1.0x';
                zoomBtn.style.cssText = 'flex:1;padding:7px 10px;border-radius:6px;border:1px solid #4B5563;background:#1F2937;color:#F9FAFB;font-size:11px;font-weight:800;letter-spacing:0.04em;';
                zoomBtn.addEventListener('click', async () => {
                    zoomed = !zoomed;
                    const zVal = zoomed ? targetZoom : (caps.zoom.min || 1.0);
                    try {
                        await this.html5Qrcode.applyVideoConstraints({
                            advanced: [{ zoom: zVal }]
                        });
                        zoomBtn.textContent = zoomed ? `🔍 ZOOM: ${targetZoom.toFixed(1)}x` : '🔍 ZOOM: 1.0x';
                        zoomBtn.style.background = zoomed ? '#124191' : '#1F2937';
                    } catch (_) {
                        zoomed = false;
                    }
                });
                bar.appendChild(zoomBtn);
            }
        } catch (_) {}
    }

    async destroyScannerInstance() {
        const scanner =
            this.html5Qrcode;

        this.html5Qrcode =
            null;

        if (!scanner) {
            return;
        }

        try {
            await scanner.stop();
        } catch (error) {
            console.warn(
                '[SCANNER STOP]',
                error
            );
        }

        try {
            await scanner.clear();
        } catch (error) {
            console.warn(
                '[SCANNER CLEAR]',
                error
            );
        }
    }

    async start() {
        if (
            !this.modal ||
            !this.reader ||
            this.status ===
                'STARTING' ||
            this.status ===
                'SCANNING'
        ) {
            return;
        }

        if (
            this.status ===
            'STOPPING'
        ) {
            setTimeout(
                () => this.start(),
                300
            );

            return;
        }

        if (
            typeof Html5Qrcode ===
                'undefined' ||
            typeof Html5QrcodeSupportedFormats ===
                'undefined'
        ) {
            console.error(
                '[SCANNER ERROR] html5-qrcode indisponível.'
            );

            alert(
                'Leitor de código indisponível. ' +
                'Recarregue a aplicação.'
            );

            return;
        }

        this.status =
            'STARTING';

        this.modal.classList.remove(
            'hidden'
        );

        try {
            await this.ensureCameraSelector();

            if (
                !this.selectedCameraId
            ) {
                throw new Error(
                    'Nenhuma câmera selecionada.'
                );
            }

            /*
             * Garante instância óptica nova em cada abertura.
             */
            await this.destroyScannerInstance();

            this.html5Qrcode =
                new Html5Qrcode(
                    'reader'
                );

            const config = {
                fps: 10,

                qrbox: {
                    width: 250,
                    height: 150
                },

                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },

                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.ITF,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.CODE_128
                ]
            };

            await this.html5Qrcode.start(
                this.selectedCameraId,

                config,

                (decodedText) => {
                    if (
                        this.status !==
                        'SCANNING'
                    ) {
                        return;
                    }

                    const value =
                        String(
                            decodedText || ''
                        ).trim();

                    if (!value) {
                        return;
                    }

                    if (
                        navigator.vibrate
                    ) {
                        navigator.vibrate(
                            200
                        );
                    }

                    /*
                     * Conserva o callback antes da
                     * limpeza assíncrona do scanner.
                     */
                    const callback =
                        this.onScanSuccess;

                    this.stop();

                    callback(
                        value
                    );
                },

                () => {
                    /*
                     * Falhas de enquadramento são normais
                     * durante o loop óptico.
                     */
                }
            );

            if (
                this.status !==
                'STARTING'
            ) {
                return;
            }

            this.status =
                'SCANNING';

            this.setupOpticalControls();

        } catch (error) {
            console.error(
                '[SCANNER ERROR]',
                error
            );

            await this.destroyScannerInstance();

            this.status =
                'IDLE';

            this.modal.classList.add(
                'hidden'
            );

            alert(
                'Falha ao iniciar scanner: ' +
                (
                    error?.message ||
                    String(error)
                )
            );
        }
    }

    async stop(
        hideModal = true
    ) {
        if (
            this.status ===
                'IDLE' ||
            this.status ===
                'STOPPING'
        ) {
            return;
        }

        this.status =
            'STOPPING';

        if (
            hideModal &&
            this.modal
        ) {
            this.modal.classList.add(
                'hidden'
            );
        }

        await this.destroyScannerInstance();

        this.status =
            'IDLE';
    }
}
