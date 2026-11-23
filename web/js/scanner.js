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
    static STORAGE_KEY = 'kippe.scanner.preferredCameraId';

    constructor(onScanSuccessCallback) {
        this.onScanSuccess = onScanSuccessCallback;
        this.modal = document.getElementById('scanner-modal');
        this.closeBtn = document.getElementById('close-scanner-btn');
        this.reader = document.getElementById('reader');
        this.status = 'IDLE';
        this.html5Qrcode = null;
        this.selectedCameraId = null;
        this.cameraSelector = null;
        this.userManuallyPickedCamera = false;

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.stop());
        }

        if (this.reader) {
            this.reader.addEventListener('click', () => this.triggerFocusPulse());
        }
    }

    getStoredCameraId() {
        try {
            return window.localStorage.getItem(ScannerManager.STORAGE_KEY) || null;
        } catch (error) {
            console.warn('[SCANNER STORAGE READ]', error);
            return null;
        }
    }

    storeCameraId(cameraId) {
        if (!cameraId) {
            return;
        }

        try {
            window.localStorage.setItem(ScannerManager.STORAGE_KEY, cameraId);
        } catch (error) {
            console.warn('[SCANNER STORAGE WRITE]', error);
        }
    }

    async getAvailableCameras() {
        if (
            typeof Html5Qrcode === 'undefined' ||
            typeof Html5Qrcode.getCameras !== 'function'
        ) {
            throw new Error('Enumeração de câmeras indisponível.');
        }

        const cameras = await Html5Qrcode.getCameras();

        if (!Array.isArray(cameras) || cameras.length === 0) {
            throw new Error('Nenhuma câmera disponível.');
        }

        return cameras;
    }

    isPrimaryRearCamera(cam) {
        const lbl = String(cam?.label || '').toLowerCase();
        const isBack = /back|rear|traseira|environment|facing back/.test(lbl);
        const isAux = /front|frontal|wide|ultra|macro|depth|tele/.test(lbl);
        if (!isBack || isAux) return false;
        // Em dispositivos Android/Samsung, camera2 0 é a lente principal 1x com PDAF
        if (/camera2\s*0\b|\bcamera\s*0\b/.test(lbl)) return true;
        return !/camera2\s*[2-9]\b|\bcamera\s*[2-9]\b/.test(lbl);
    }

    resolvePreferredCamera(cameras) {
        const primaryRear = cameras.find((cam) => this.isPrimaryRearCamera(cam));
        const storedCameraId = this.getStoredCameraId();

        if (storedCameraId) {
            const storedCamera = cameras.find(
                (camera) => camera.id === storedCameraId
            );

            if (storedCamera) {
                const storedLbl = String(storedCamera.label || '').toLowerCase();
                const isStoredAux = /front|frontal|wide|ultra|macro|depth|tele|camera2\s*[2-9]\b/.test(storedLbl);
                // Auto-corrige se uma lente auxiliar sem foco ficou salva antes do filtro óptico
                if (!this.userManuallyPickedCamera && isStoredAux && primaryRear) {
                    return primaryRear;
                }
                return storedCamera;
            }
        }

        if (this.selectedCameraId) {
            const currentCamera = cameras.find(
                (camera) => camera.id === this.selectedCameraId
            );

            if (currentCamera) {
                return currentCamera;
            }
        }

        if (primaryRear) {
            return primaryRear;
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
        if (!this.modal || !this.reader) {
            return;
        }

        let wrapper = document.getElementById('scanner-camera-selector-wrapper');
        let selector = document.getElementById('scanner-camera-selector');

        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.id = 'scanner-camera-selector-wrapper';
            wrapper.style.background = '#000000';
            wrapper.style.padding = '8px 12px';
            wrapper.style.color = '#ffffff';
            wrapper.style.flexShrink = '0';

            const label = document.createElement('div');
            label.textContent = 'CÂMERA DO SCANNER (TOQUE NO VÍDEO P/ FOCAR)';
            label.style.fontSize = '10px';
            label.style.fontWeight = '700';
            label.style.letterSpacing = '0.06em';
            label.style.marginBottom = '4px';

            selector = document.createElement('select');
            selector.id = 'scanner-camera-selector';
            selector.style.width = '100%';
            selector.style.padding = '8px';
            selector.style.color = '#111827';
            selector.style.background = '#ffffff';
            selector.style.border = '1px solid #374151';
            selector.style.borderRadius = '6px';
            selector.style.fontSize = '12px';
            selector.style.fontWeight = '700';

            selector.addEventListener('change', async (event) => {
                const cameraId = event.target.value;
                if (!cameraId || cameraId === this.selectedCameraId) {
                    return;
                }

                this.userManuallyPickedCamera = true;
                this.selectedCameraId = cameraId;
                this.storeCameraId(cameraId);

                if (this.status === 'SCANNING') {
                    await this.stop(false);
                    await this.start();
                }
            });

            wrapper.appendChild(label);
            wrapper.appendChild(selector);
            this.reader.before(wrapper);
        }

        this.cameraSelector = selector;

        const cameras = await this.getAvailableCameras();
        const preferredCamera = this.resolvePreferredCamera(cameras);

        this.selectedCameraId = preferredCamera.id;
        this.storeCameraId(preferredCamera.id);

        selector.innerHTML = '';

        cameras.forEach((camera, index) => {
            const option = document.createElement('option');
            option.value = camera.id;
            const rawLbl = camera.label || `CÂMERA ${index + 1}`;
            option.textContent = this.isPrimaryRearCamera(camera)
                ? `★ PRINCIPAL · ${rawLbl}`
                : rawLbl;
            option.selected = camera.id === this.selectedCameraId;
            selector.appendChild(option);
        });

        selector.value = this.selectedCameraId;
    }

    async triggerFocusPulse() {
        try {
            if (!this.html5Qrcode || this.status !== 'SCANNING') return;
            await this.html5Qrcode.applyVideoConstraints({
                focusMode: 'continuous',
                advanced: [{ focusMode: 'single-shot' }]
            }).catch(() => {});
            setTimeout(() => {
                if (!this.html5Qrcode || this.status !== 'SCANNING') return;
                this.html5Qrcode.applyVideoConstraints({
                    focusMode: 'continuous',
                    advanced: [{ focusMode: 'continuous' }]
                }).catch(() => {});
            }, 250);
        } catch (_) {}
    }

    async setupOpticalControls() {
        try {
            if (!this.html5Qrcode) return;

            const applyFocusAndDefaultZoom = async (useDefaultZoom = true) => {
                if (!this.html5Qrcode || this.status !== 'SCANNING') return;
                const caps = typeof this.html5Qrcode.getRunningTrackCapabilities === 'function'
                    ? this.html5Qrcode.getRunningTrackCapabilities()
                    : {};
                const adv = [{ focusMode: 'continuous' }];
                if (useDefaultZoom && caps && caps.zoom && typeof caps.zoom.max === 'number' && caps.zoom.max >= 1.5) {
                    adv.push({ zoom: Math.min(1.5, caps.zoom.max) });
                }
                await this.html5Qrcode.applyVideoConstraints({
                    focusMode: 'continuous',
                    advanced: adv
                }).catch(() => {});
            };

            await applyFocusAndDefaultZoom(true);
            setTimeout(() => applyFocusAndDefaultZoom(true), 600);

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
                torchBtn.style.cssText = 'flex:1;padding:7px 8px;border-radius:6px;border:1px solid #4B5563;background:#1F2937;color:#F9FAFB;font-size:10px;font-weight:800;letter-spacing:0.04em;';
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
                const zoomSteps = [Math.min(1.5, caps.zoom.max), Math.min(2.2, caps.zoom.max), caps.zoom.min || 1.0];
                let stepIdx = 0;
                const zoomBtn = document.createElement('button');
                zoomBtn.type = 'button';
                zoomBtn.textContent = `🔍 ZOOM: ${zoomSteps[0].toFixed(1)}x`;
                zoomBtn.style.cssText = 'flex:1;padding:7px 8px;border-radius:6px;border:1px solid #4B5563;background:#124191;color:#F9FAFB;font-size:10px;font-weight:800;letter-spacing:0.04em;';
                zoomBtn.addEventListener('click', async () => {
                    stepIdx = (stepIdx + 1) % zoomSteps.length;
                    const zVal = zoomSteps[stepIdx];
                    try {
                        await this.html5Qrcode.applyVideoConstraints({
                            focusMode: 'continuous',
                            advanced: [{ focusMode: 'continuous', zoom: zVal }]
                        });
                        zoomBtn.textContent = `🔍 ZOOM: ${zVal.toFixed(1)}x`;
                        zoomBtn.style.background = zVal > 1.05 ? '#124191' : '#1F2937';
                    } catch (_) {}
                });
                bar.appendChild(zoomBtn);
            }

            const focusBtn = document.createElement('button');
            focusBtn.type = 'button';
            focusBtn.textContent = '🎯 FOCAR';
            focusBtn.style.cssText = 'padding:7px 10px;border-radius:6px;border:1px solid #4B5563;background:#1F2937;color:#F9FAFB;font-size:10px;font-weight:800;letter-spacing:0.04em;';
            focusBtn.addEventListener('click', () => this.triggerFocusPulse());
            bar.appendChild(focusBtn);
        } catch (_) {}
    }

    async destroyScannerInstance() {
        const scanner = this.html5Qrcode;
        this.html5Qrcode = null;

        if (!scanner) {
            return;
        }

        try {
            await scanner.stop();
        } catch (error) {
            console.warn('[SCANNER STOP]', error);
        }

        try {
            await scanner.clear();
        } catch (error) {
            console.warn('[SCANNER CLEAR]', error);
        }
    }

    async start() {
        if (
            !this.modal ||
            !this.reader ||
            this.status === 'STARTING' ||
            this.status === 'SCANNING'
        ) {
            return;
        }

        if (this.status === 'STOPPING') {
            setTimeout(() => this.start(), 300);
            return;
        }

        if (
            typeof Html5Qrcode === 'undefined' ||
            typeof Html5QrcodeSupportedFormats === 'undefined'
        ) {
            console.error('[SCANNER ERROR] html5-qrcode indisponível.');
            alert('Leitor de código indisponível. Recarregue a aplicação.');
            return;
        }

        this.status = 'STARTING';
        this.modal.classList.remove('hidden');

        try {
            await this.ensureCameraSelector();

            if (!this.selectedCameraId) {
                throw new Error('Nenhuma câmera selecionada.');
            }

            await this.destroyScannerInstance();

            this.html5Qrcode = new Html5Qrcode('reader', {
                verbose: false,
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.ITF,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39
                ]
            });

            const config = {
                fps: 10,
                qrbox: {
                    width: 250,
                    height: 150
                },
                disableFlip: true,
                videoConstraints: {
                    deviceId: { exact: this.selectedCameraId },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    focusMode: 'continuous'
                },
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.ITF,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39
                ]
            };

            await this.html5Qrcode.start(
                this.selectedCameraId,
                config,
                (decodedText) => {
                    if (this.status !== 'SCANNING') {
                        return;
                    }

                    const value = String(decodedText || '').trim();
                    if (!value) {
                        return;
                    }

                    if (navigator.vibrate) {
                        navigator.vibrate(200);
                    }

                    const callback = this.onScanSuccess;
                    this.stop();
                    callback(value);
                },
                () => {}
            );

            if (this.status !== 'STARTING') {
                return;
            }

            this.status = 'SCANNING';
            this.setupOpticalControls();

        } catch (error) {
            console.error('[SCANNER ERROR]', error);
            await this.destroyScannerInstance();
            this.status = 'IDLE';
            this.modal.classList.add('hidden');
            alert('Falha ao iniciar scanner: ' + (error?.message || String(error)));
        }
    }

    async stop(hideModal = true) {
        if (this.status === 'IDLE' || this.status === 'STOPPING') {
            return;
        }

        this.status = 'STOPPING';

        if (hideModal && this.modal) {
            this.modal.classList.add('hidden');
        }

        await this.destroyScannerInstance();
        this.status = 'IDLE';
    }
}
