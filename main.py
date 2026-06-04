from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

CM_TO_PT = 72 / 2.54
REMOVE_SUFFIXES = [
    ": Chaozhou Zero to One Cultural Media Co., Ltd",
    "Chaozhou Zero to One Cultural Media Co., Ltd",
]
SIZE_MAP = {
    "10x8": (10.0, 8.0),
    "10x10": (10.0, 10.0),
    "10x15": (10.0, 15.0),
}
SKU_PATTERNS = [
    re.compile(r"\bFD-[A-Z0-9][A-Z0-9\-]*\b"),
    re.compile(r"\b[A-Z]{1,8}-US-[A-Z0-9][A-Z0-9\-]*\b"),
    re.compile(r"\b[A-Z0-9]{2,}[A-Z0-9\-]*-US\b"),
]
SKU_LINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{2,80}$")
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]+')

app = FastAPI(title="PDF Label Tool")
app.mount("/static", StaticFiles(directory="static"), name="static")


def safe_name(name: str) -> str:
    name = INVALID_FILENAME_CHARS.sub("-", name.strip())
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "UNKNOWN-SKU"


def cm_to_pt(v: float) -> float:
    return v * CM_TO_PT


def normalize_token(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def is_sku_candidate(text: str) -> bool:
    t = normalize_token(text)
    if not t:
        return False
    bad_keywords = ["数量", "SingleSKU", "MadeInChina", "Created:", "FBA", "请不要遮住", "目的地", "发货地"]
    if any(k.lower() in t.lower() for k in bad_keywords):
        return False
    if re.search(r"[\u4e00-\u9fff]", t):
        return False
    if not SKU_LINE_RE.match(t):
        return False
    # SellerSKU usually contains at least one hyphen or both letters and digits.
    has_letter = bool(re.search(r"[A-Za-z]", t))
    has_digit = bool(re.search(r"\d", t))
    if "-" not in t and not (has_letter and has_digit):
        return False
    # Exclude Amazon FBA shipment/carton ids.
    if re.match(r"^FBA[A-Z0-9]+$", t, re.I):
        return False
    return True


def extract_lines(page: fitz.Page) -> List[str]:
    text = page.get_text("text") or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        return lines
    # Fallback: sort spans by visual row.
    d = page.get_text("dict")
    rows: List[Tuple[float, float, str]] = []
    for b in d.get("blocks", []):
        for l in b.get("lines", []):
            y = min((s.get("bbox", [0, 0, 0, 0])[1] for s in l.get("spans", [])), default=0)
            x = min((s.get("bbox", [0, 0, 0, 0])[0] for s in l.get("spans", [])), default=0)
            t = "".join(s.get("text", "") for s in l.get("spans", [])).strip()
            if t:
                rows.append((y, x, t))
    return [t for _, _, t in sorted(rows)]


def extract_sku_and_qty(page: fitz.Page) -> Tuple[str, int]:
    lines = extract_lines(page)
    sku = ""
    qty = 1

    # Strong rule: SellerSKU is the first valid code line after "Single SKU".
    # This supports both formats such as FD-US-SD4-AH-BN4875 and FDM888A-FX-US.
    for i, line in enumerate(lines):
        if "Single SKU" in line:
            for candidate in lines[i + 1 : i + 10]:
                cand = normalize_token(candidate)
                if "数量" in candidate or cand.lower().startswith("madeinchina"):
                    break
                if is_sku_candidate(cand):
                    sku = cand
                    break
            if sku:
                break

    # Regex fallback from the complete text, in case line reconstruction changes.
    if not sku:
        full_text = "\n".join(lines)
        m = re.search(r"Single\s*SKU\s*\n\s*([^\n\r]+)\s*\n\s*数量", full_text, re.I)
        if m and is_sku_candidate(m.group(1)):
            sku = normalize_token(m.group(1))

    # Older fallback: SKU-looking tokens anywhere, but avoid choosing FBA shipment IDs.
    if not sku:
        full = normalize_token("\n".join(lines))
        candidates = []
        for pat in SKU_PATTERNS:
            candidates.extend(pat.findall(full))
        candidates = [c for c in candidates if is_sku_candidate(c)]
        if candidates:
            sku = sorted(set(candidates), key=lambda x: (-len(x), x))[0]

    for i, line in enumerate(lines):
        if "数量" in line:
            m = re.search(r"数量\s*(\d+)", line)
            if m:
                qty = int(m.group(1))
            elif i + 1 < len(lines) and lines[i + 1].isdigit():
                qty = int(lines[i + 1])
            break

    return (sku or "UNKNOWN-SKU", qty)


def clean_company_suffix(page: fitz.Page) -> None:
    """Remove destination-line text after FBA:/FBA： without changing nearby layout.

    This handles English/Chinese/romanized company names, e.g.
    "FBA: Chaozhou...", "FBA: dongguan...", "FBA: Changsha...".
    It keeps the visible FBA/FBA: prefix and only wipes the same-line suffix in
    the destination column, so the warehouse code line below is not touched.
    """
    page_w = page.rect.width
    # Right column usually starts around the middle of the label. Do not wipe into it.
    destination_right = min(page_w * 0.50, 153.0 if page_w <= 320 else page_w * 0.50)

    # First try generic line-based cleanup: remove all same-line words after FBA:.
    for prefix in ("FBA:", "FBA："):
        rects = page.search_for(prefix)
        for r in rects:
            # Ignore the big top title "FBA"; this rect must be in the address area.
            if r.y0 < 20 or r.x0 > destination_right:
                continue
            words = page.get_text("words") or []
            wipe_rect = None
            for w in words:
                x0, y0, x1, y1, word = w[:5]
                same_line = abs(y0 - r.y0) < 3.0 or (y0 <= r.y1 and y1 >= r.y0)
                if not same_line:
                    continue
                if x0 >= destination_right:
                    continue
                # Remove either words after the prefix, or the suffix part of a combined word like FBA:dongguan.
                if x1 > r.x1 + 0.15 and (x0 >= r.x0 - 0.5):
                    part = fitz.Rect(max(r.x1 + 0.2, x0), y0 - 0.4, min(x1 + 0.6, destination_right), y1 + 0.4)
                    wipe_rect = part if wipe_rect is None else (wipe_rect | part)
            if wipe_rect is None:
                # Fallback: wipe a short same-line band after FBA: but stay inside destination column.
                wipe_rect = fitz.Rect(r.x1 + 0.2, r.y0 - 0.3, destination_right, r.y1 + 0.3)
            shape = page.new_shape()
            shape.draw_rect(wipe_rect)
            shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
            shape.commit(overlay=True)
            return

    # Fallback for older exact company names, if the prefix is not searchable.
    for suffix in REMOVE_SUFFIXES:
        rects = page.search_for(suffix)
        if rects:
            for r in rects:
                rr = fitz.Rect(r.x0 + 0.05, r.y0 + 0.1, min(r.x1 + 0.3, destination_right), min(r.y1, r.y0 + 9.0))
                shape = page.new_shape()
                shape.draw_rect(rr)
                shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
                shape.commit(overlay=True)
            return


def make_output_page(src_doc: fitz.Document, page_index: int, size_key: str, add_made: bool, made_font_size: float) -> fitz.Document:
    width_cm, height_cm = SIZE_MAP[size_key]
    target_w = cm_to_pt(width_cm)
    target_h = cm_to_pt(height_cm)

    # Work on a one-page copy so overlays do not affect original text extraction.
    tmp = fitz.open()
    tmp.insert_pdf(src_doc, from_page=page_index, to_page=page_index)
    page = tmp[0]
    clean_company_suffix(page)

    src_w, src_h = page.rect.width, page.rect.height
    scale = target_w / src_w
    clip_h = min(src_h, target_h / scale)
    clip = fitz.Rect(0, 0, src_w, clip_h)

    out = fitz.open()
    out_page = out.new_page(width=target_w, height=target_h)
    out_page.show_pdf_page(fitz.Rect(0, 0, target_w, target_h), tmp, 0, clip=clip, keep_proportion=False)

    if add_made:
        # PyMuPDF's insert_textbox may silently skip text when the box is tight
        # after show_pdf_page. Use baseline insertion with explicit centering instead.
        made_text = "Made In China"
        made_font_size = float(made_font_size or 8.0)
        made_y = target_h - cm_to_pt(0.5)  # baseline: 0.5 cm from bottom
        text_w = fitz.get_text_length(made_text, fontname="helv", fontsize=made_font_size)
        made_x = max(0, (target_w - text_w) / 2)
        out_page.insert_text(
            (made_x, made_y),
            made_text,
            fontsize=made_font_size,
            fontname="helv",
            color=(0, 0, 0),
            overlay=True,
        )

    tmp.close()
    return out


def collect_pdfs(input_path: Path, work_dir: Path) -> List[Path]:
    if input_path.suffix.lower() == ".pdf":
        return [input_path]
    if input_path.suffix.lower() == ".zip":
        extract_dir = work_dir / "input_zip"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(extract_dir)
        return sorted(extract_dir.rglob("*.pdf"))
    raise ValueError("Only PDF or ZIP is supported")


def process_file(
    input_path: Path,
    output_zip: Path,
    size_key: str,
    add_made: bool,
    made_font_size: float,
    group_by_sku: bool,
) -> Dict:
    """Process PDFs.

    group_by_sku=True:
      - every page is identified by SellerSKU
      - pages with the exact same SellerSKU are merged into one PDF
      - filename: SellerSKU-数量只.pdf

    group_by_sku=False:
      - keep the original PDF file structure
      - each source PDF becomes one processed output PDF
      - no cross-file or cross-SKU merging is performed
    """
    if size_key not in SIZE_MAP:
        raise ValueError("Invalid size")

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        pdf_paths = collect_pdfs(input_path, work_dir)
        if not pdf_paths:
            raise ValueError("No PDF found")

        out_dir = work_dir / "output"
        out_dir.mkdir()
        total_pages = 0
        unknown_pages: List[str] = []

        if group_by_sku:
            groups: "OrderedDict[str, fitz.Document]" = OrderedDict()
            qty_map: Dict[str, int] = OrderedDict()
            page_map: Dict[str, int] = OrderedDict()

            for pdf_path in pdf_paths:
                src = fitz.open(str(pdf_path))
                try:
                    for i, page in enumerate(src):
                        sku, qty = extract_sku_and_qty(page)
                        if sku == "UNKNOWN-SKU":
                            unknown_pages.append(f"{pdf_path.name} page {i + 1}")
                        total_pages += 1
                        if sku not in groups:
                            groups[sku] = fitz.open()
                            qty_map[sku] = 0
                            page_map[sku] = 0
                        one_page_doc = make_output_page(src, i, size_key, add_made, made_font_size)
                        groups[sku].insert_pdf(one_page_doc)
                        one_page_doc.close()
                        qty_map[sku] += qty
                        page_map[sku] += 1
                finally:
                    src.close()

            manifest_lines = [
                "PDF label processing finished",
                "Output mode: group by SellerSKU",
                f"Input PDFs: {len(pdf_paths)}",
                f"Total pages: {total_pages}",
                f"SellerSKU groups: {len(groups)}",
                f"Size: {size_key}",
                f"Made In China: {'yes' if add_made else 'no'}",
                "",
                "Groups:",
            ]

            for sku, doc in groups.items():
                file_name = f"{safe_name(sku)}-{qty_map[sku]}只.pdf"
                out_pdf = out_dir / file_name
                doc.save(str(out_pdf), deflate=True, garbage=4)
                doc.close()
                manifest_lines.append(f"{file_name}\tpages={page_map[sku]}\tqty={qty_map[sku]}")

            skus_payload = [{"sku": sku, "qty": qty_map[sku], "pages": page_map[sku]} for sku in groups]

        else:
            # Preserve the input-file split. This is useful when the user only wants
            # cleanup/crop/Made In China without merging different shipments.
            manifest_lines = [
                "PDF label processing finished",
                "Output mode: original files",
                f"Input PDFs: {len(pdf_paths)}",
                f"Size: {size_key}",
                f"Made In China: {'yes' if add_made else 'no'}",
                "",
                "Files:",
            ]
            skus_payload = []
            used_names: Dict[str, int] = {}

            for pdf_path in pdf_paths:
                src = fitz.open(str(pdf_path))
                out_doc = fitz.open()
                qty_sum = 0
                pages = 0
                first_sku = ""
                unique_skus = OrderedDict()
                try:
                    for i, page in enumerate(src):
                        sku, qty = extract_sku_and_qty(page)
                        if not first_sku and sku != "UNKNOWN-SKU":
                            first_sku = sku
                        if sku != "UNKNOWN-SKU":
                            unique_skus[sku] = True
                        qty_sum += qty
                        pages += 1
                        total_pages += 1
                        one_page_doc = make_output_page(src, i, size_key, add_made, made_font_size)
                        out_doc.insert_pdf(one_page_doc)
                        one_page_doc.close()
                finally:
                    src.close()

                if len(unique_skus) == 1:
                    base = f"{safe_name(next(iter(unique_skus)))}-{qty_sum}只"
                else:
                    base = safe_name(pdf_path.stem) or "processed"
                count = used_names.get(base, 0) + 1
                used_names[base] = count
                if count > 1:
                    base = f"{base}-{count}"
                out_name = f"{base}.pdf"
                out_doc.save(str(out_dir / out_name), deflate=True, garbage=4)
                out_doc.close()
                manifest_lines.append(f"{out_name}\tpages={pages}\tqty={qty_sum}\tfirst_seller_sku={first_sku or 'UNKNOWN-SKU'}")

            skus_payload = []

        if unknown_pages:
            manifest_lines += ["", "Unknown SKU pages:", *unknown_pages]

        (out_dir / "处理说明.txt").write_text("\n".join(manifest_lines), encoding="utf-8")

        if output_zip.exists():
            output_zip.unlink()
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.rglob("*")):
                zf.write(p, p.relative_to(out_dir))

        return {
            "input_pdfs": len(pdf_paths),
            "total_pages": total_pages,
            "mode": "group_by_sku" if group_by_sku else "original_files",
            "groups": len(skus_payload),
            "skus": skus_payload,
            "unknown_pages": unknown_pages,
        }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return Path("static/index.html").read_text(encoding="utf-8")


@app.post("/api/inspect")
async def inspect(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        in_path = tmp / safe_name(file.filename or "input.pdf")
        in_path.write_bytes(await file.read())
        try:
            pdfs = collect_pdfs(in_path, tmp)
            group_counts: Dict[str, int] = OrderedDict()
            total_pages = 0
            for pdf_path in pdfs:
                doc = fitz.open(str(pdf_path))
                for page in doc:
                    sku, qty = extract_sku_and_qty(page)
                    group_counts[sku] = group_counts.get(sku, 0) + qty
                    total_pages += 1
                doc.close()
            return {"total_pages": total_pages, "groups": [{"sku": k, "qty": v} for k, v in group_counts.items()]}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/process")
async def process(
    file: UploadFile = File(...),
    size: str = Form("10x8"),
    add_made: bool = Form(False),
    made_font_size: float = Form(8.0),
    group_by_sku: bool = Form(True),
):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        in_path = tmp / safe_name(file.filename or "input.pdf")
        in_path.write_bytes(await file.read())
        out_zip = tmp / "PDF标签处理结果.zip"
        try:
            info = process_file(in_path, out_zip, size, add_made, made_font_size, group_by_sku)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        final_path = Path(tempfile.gettempdir()) / f"pdf-label-result-{os.getpid()}-{abs(hash(str(out_zip)))}.zip"
        shutil.copy2(out_zip, final_path)
        return FileResponse(final_path, filename="PDF标签处理结果.zip", media_type="application/zip")
