"""Subprocess-only Docling entry; stdout is a JSON conversion result."""

import json
import os
import sys
from pathlib import Path


def main():
    import threading
    import time
    import psutil

    peak = [0]
    process = psutil.Process()
    limit = max(256, int(os.environ.get("DOCLING_MAX_MEMORY_MB", "2048"))) * 1024 * 1024

    def monitor():
        while True:
            rss = process.memory_info().rss
            peak[0] = max(peak[0], rss)
            if rss > limit:
                os._exit(137)
            time.sleep(0.1)

    threading.Thread(target=monitor, daemon=True).start()
    from importlib.metadata import version

    if version("docling") != "2.58.0":
        raise RuntimeError("Expected pinned Docling 2.58.0")
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    options.accelerator_options.num_threads = 2
    if os.environ.get("DOCLING_ARTIFACTS_PATH"):
        options.artifacts_path = Path(os.environ["DOCLING_ARTIFACTS_PATH"])
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
    )
    result = converter.convert(Path(sys.argv[1]), raises_on_error=True)
    document = result.document
    blocks, headings = [], []
    for item, level in document.iterate_items():
        label = str(item.label.value)
        text = getattr(item, "text", "") or ""
        if label in {"section_header", "title"}:
            heading_level = max(1, int(getattr(item, "level", level) or 1))
            headings = headings[: heading_level - 1] + [text]
        if label == "table":
            text = item.export_to_markdown(doc=document)
        if not text.strip():
            continue
        provenance = [p.model_dump(mode="json") for p in (getattr(item, "prov", None) or [])]
        blocks.append(
            {
                "text": text,
                "page_number": provenance[0].get("page_no") if provenance else None,
                "location": {
                    "blockId": item.self_ref,
                    "type": label,
                    "titlePath": list(headings),
                    "order": len(blocks),
                    "provenance": provenance,
                },
            }
        )
    output = {
        "blocks": blocks,
        "markdown": document.export_to_markdown(),
        "document": document.export_to_dict(),
        "metrics": {"peakRssBytes": peak[0]},
    }
    Path(sys.argv[2]).write_text(json.dumps(output, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
