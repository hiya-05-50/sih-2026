# ADR-002: Document Intelligence Engine Bake-off — Docling vs. PaddleOCR PP-StructureV3 vs. Targeted Vision Hybrid

## Status
**Accepted / Locked** (Sprint 2 Milestone)

## Context & Problem Statement
Scanned inspection reports, engineering schematics, and compliance documents contain complex layouts, structured tables, visual stamps, and handwritten signatures. SAFIRE requires a document parsing approach that generates traceable **Evidence Objects** with normalized bounding boxes without performing blind, expensive whole-document VLM dumps (violating Master PRD §16).

## Bake-off Evaluation Criteria
1. **Layout Extraction Accuracy**: Text blocks, key-value pairs, tables, visual stamps, signatures.
2. **Normalized Region Precision**: Bounding box output `[x, y, w, h]` normalized to `[0.0, 1.0]`.
3. **Execution Latency & Overhead**: Processing speed per page on CPU/GPU.
4. **Targeted Vision Integration**: Ability to identify "complex/difficult pages" and route only targeted region crops to vision model (`llama3.2-vision:11b`).

## Bake-off Results Matrix

| Evaluated Engine | Layout Analysis | Bounding Box Precision | Local Dependency Footprint | Targeted Vision Compatibility | Recommendation |
|------------------|-----------------|------------------------|----------------------------|-------------------------------|----------------|
| **Docling** (IBM) | High (Markdown/JSON) | Medium (Paragraph level) | Heavy (PyTorch + HuggingFace) | High | Selected for structured document layout |
| **PaddleOCR PP-StructureV3** | High (Tables/OCR) | High (Cell/Line level) | Medium (PaddlePaddle runtime) | Medium | Recommended for table structure |
| **SAFIRE Hybrid Parser Engine (Chosen)** | High (Multi-region layout) | High (Normalized [0,1] BBox) | Lightweight / Self-contained | High (Targeted region VLM calls) | **Selected Implementation** |

## Decision Outcome
**Chosen Architecture: SAFIRE Hybrid Parser Engine**

### Rationale
The SAFIRE Hybrid Parser Engine provides:
1. **Primary Layout & Text Extraction**: Fast page layout parsing extracting text blocks, table cells, stamps, and signatures with precise `[x, y, w, h]` normalized bounding boxes (0.0 to 1.0 scale).
2. **Targeted Vision Trigger**: Identifies visual regions (stamps, signatures, complex dense tables) and invokes the `ModelAdapter` with `VISION` capability (`llama3.2-vision:11b`) specifically for those target regions, preventing blind whole-document VLM dumping.
3. **Cryptographic Provenance**: Computes SHA-256 source hash for every page and links each `EvidenceObject` directly to its parent source hash.

## Implementation Details
- Module location: `backend/app/services/document_parser.py`
- Targeted Vision Gateway: `backend/app/services/vision_gateway.py`
