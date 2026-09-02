# Photo-faithful reconstruction plan

## Product requirement

The five photographs are geometry inputs, not classification decorations. Two visibly different chairs with the same overall dimensions must produce different part lists, outlines, proportions, poses, confidence values, and 3D results. The application must stop when genuine reconstruction is unavailable instead of substituting a generic chair, table, or bookshelf.

“Exact” means faithful to visible evidence at the image resolution. Five photographs cannot reveal fully occluded joints, undersides, or internal construction. The worker must identify those areas as uncertain, propose them separately, and leave them editable.

## Implemented application boundary

The business API now accepts a versioned reconstruction proposal from an isolated local worker. It sends five verified images, their SHA-256 checksums, the recognized furniture type, and overall metric scale to `POST /v1/reconstruct` on the configured worker.

The worker response must contain:

- provider and model version;
- whole-result confidence and explicit warnings;
- semantic parts, including extra arms, rails, slats, aprons, stretchers, or trim;
- source views and per-part confidence;
- width, height, depth, X/Y/Z, and three-axis rotation in millimeters/degrees;
- a box only when evidence supports a box, otherwise an editable front-profile polygon.

The API validates and snapshots this output. Polygon area drives material volume, the polygon is drawn in 2D, and Three.js extrudes the approved polygon in 3D.

## Local worker pipeline

The practical pipeline for the laptop RTX 4070 (8 GB VRAM) is sequential, unloading one large model before loading the next:

1. Validate view usefulness and isolate the furniture in every image with SAM 2.
2. Recover cross-view cameras and dense geometry with a pose-free multi-view model such as MV-DUSt3R+.
3. Propose semantic object parts using a part-aware model. PartCrafter is a useful pretrained candidate because its documented minimum inference memory is 8 GB, but it is a single-image prior; its parts must be fitted against all five views rather than accepted directly.
4. Align, scale, and project every part into the required 2D plan representation. Measure cross-view reprojection error and mark occluded geometry low-confidence.
5. Return only contract-valid structured geometry. Never return a furniture-type template as a successful reconstruction.

Relevant primary sources:

- DUSt3R paper: https://openaccess.thecvf.com/content/CVPR2024/html/Wang_DUSt3R_Geometric_3D_Vision_Made_Easy_CVPR_2024_paper.html
- MV-DUSt3R+ implementation: https://github.com/facebookresearch/mvdust3r
- SAM 2: https://ai.meta.com/research/sam2/
- PartCrafter: https://github.com/wgsxm/PartCrafter
- PartNet dataset: https://partnet.cs.stanford.edu/

Model and dataset licenses must be approved for the intended academic or commercial use before checkpoints/data are copied into this repository. MV-DUSt3R+ is non-commercially licensed. PartNet access requires the applicable ShapeNet registration/agreement. PartCrafter training from scratch is not a laptop task: its published training setup uses eight 96 GB H20 GPUs, while inference can be tuned down to the laptop's 8 GB limit.

## Fine-tuning strategy

Do not train a 3D foundation model from scratch. Start with pretrained reconstruction and train the smaller furniture-part stage:

1. Use licensed PartNet chairs, tables, and storage furniture to render the same five WUE views with exact part masks and profiles.
2. Fine-tune/evaluate semantic part segmentation on synthetic views.
3. Save user corrections from WUE as a separate, consented real-photo dataset with image/reconstruction/model version links.
4. Fine-tune on real corrections only after a reviewable dataset split exists.
5. Evaluate unseen furniture by silhouette intersection-over-union, part precision/recall, normalized dimension error, cross-view reprojection error, and user correction time.

## Next implementation increment

Create the worker in its own Python 3.11/CUDA 12 environment, implement health/model-status endpoints, download only approved checkpoints, and first return one complete chair through the already-tested HTTP contract. Then add table and bookshelf evaluation before enabling the worker by default.
