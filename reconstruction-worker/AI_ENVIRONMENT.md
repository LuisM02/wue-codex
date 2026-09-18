# WUE SAM 2.1 environment

The local pretrained segmentation stage is isolated from the Windows application environment.

- WSL: `2.7.3.0`
- Distribution: Ubuntu `24.04.4 LTS`
- Linux account: `wueai` (non-administrator)
- Python: `3.12.3`, virtual environment `/home/wueai/wue-ai`
- PyTorch: `2.11.0+cu128`
- TorchVision: `0.26.0+cu128`
- GPU: NVIDIA GeForce RTX 4070 Laptop GPU, 8 GB
- SAM 2 source: official `facebookresearch/sam2` commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`
- Model: `sam2.1_hiera_base_plus.pt`
- Model SHA-256: `a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5`

The optional SAM 2 CUDA cleanup extension is disabled, as supported by Meta's installation guide. Neural inference itself runs on CUDA. The checkpoint and virtual environment remain inside WSL and are not committed to Git.

From the repository root, start the worker in PowerShell:

```powershell
.\scripts\start-sam2-worker.ps1
```

Keep that PowerShell window open while using WUE. The worker listens on `http://127.0.0.1:8010`, matching the backend defaults.

The verified integration run loaded the checkpoint on CUDA, processed five furniture views, returned eleven editable chair parts, and exposed the checkpoint hash through `/v1/model-status` and response provenance.
