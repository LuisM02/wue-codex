# WUE local vision worker

This process is deliberately separate from the business API. It receives exactly five verified views, rejects duplicate or incoherent inputs, and returns photo-derived editable geometry.

The default pipeline is a lightweight baseline that runs immediately on Windows without downloading a model checkpoint. It traces the actual silhouettes, checks opposite-view consistency and expected orientation, identifies structural regions, and scales them to the user's measurements. It is most reliable when one furniture item is photographed against a plain contrasting background.

Version `0.2.0` also contains a lazy SAM 2.1 adapter. When deliberately configured, it uses the baseline outline only as a box prompt, replaces the foreground mask with SAM's selected mask, and records the neural provider/checkpoint provenance in the existing response contract. It never silently downloads a checkpoint and never claims dense 3D reconstruction is loaded.

## Optional SAM 2.1 provider

Meta's official SAM 2 repository recommends Python 3.10 or newer, PyTorch 2.5.1 or newer, and WSL with Ubuntu for Windows GPU installations. Its code and checkpoints are Apache-2.0. Install it in a dedicated AI environment from the official repository, then download one approved SAM 2.1 checkpoint into `reconstruction-worker/checkpoints/` (which Git ignores).

Configure the worker before starting it:

```powershell
$env:WUE_WORKER_SEGMENTATION_PROVIDER = "sam2"
$env:WUE_SAM2_CHECKPOINT = "C:\absolute\path\to\sam2.1_hiera_base_plus.pt"
$env:WUE_SAM2_MODEL_CONFIG = "configs/sam2.1/sam2.1_hiera_b+.yaml"
$env:WUE_SAM2_DEVICE = "auto"
```

`GET /v1/model-status` reports whether the package and local checkpoint are available, whether CUDA will be used, and whether the checkpoint has actually loaded. An unavailable configured provider returns `503` during inference instead of falling back invisibly.

Official references: [SAM 2 repository](https://github.com/facebookresearch/sam2) and [installation guide](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).

Run from this directory with the project's environment:

```powershell
..\.venv\Scripts\python.exe -m uvicorn wue_worker.main:app --host 127.0.0.1 --port 8010
```

The service exposes `GET /health`, `GET /v1/model-status`, `POST /v1/classify`, and `POST /v1/reconstruct`.
