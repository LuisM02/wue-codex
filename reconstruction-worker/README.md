# WUE local vision worker

This process is deliberately separate from the business API. It receives exactly five verified views, rejects duplicate or incoherent inputs, and returns photo-derived editable geometry.

The current `0.1.0` pipeline is a lightweight baseline that runs immediately on Windows without downloading a model checkpoint. It traces the actual silhouettes, checks opposite-view consistency and expected orientation, identifies structural regions, and scales them to the user's measurements. It is most reliable when one furniture item is photographed against a plain contrasting background.

It is not the final neural reconstruction pipeline. Its response explicitly warns that SAM 2 and dense multi-view depth are not loaded. The worker boundary is ready for those implementations without changing saved project/plan data.

Run from this directory with the project's environment:

```powershell
..\.venv\Scripts\python.exe -m uvicorn wue_worker.main:app --host 127.0.0.1 --port 8010
```

The service exposes `GET /health`, `GET /v1/model-status`, `POST /v1/classify`, and `POST /v1/reconstruct`.
