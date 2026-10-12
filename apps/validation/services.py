"""Stage 2 AI Detection Validator pipeline services."""
import json
import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw

from django.conf import settings
from django.db import transaction

from apps.jobs.models import Job
from apps.jobs.services import update_job_progress_service, mark_job_failed_service
from apps.ai_engine.vlm_client import ai_client
from apps.ai_engine.prompts import STAGE2_VALIDATION_PROMPT_TEMPLATE
from apps.validation.bbox import normalize_bounding_box
from .models import DetectionRecord

logger = logging.getLogger(__name__)


def parse_detection_payload(raw_payload: Any) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Ingests diverse third-party detector schemas:
    1. Raw Python list: `[ { "id": 1, ... }, ... ]`
    2. Envelope objects: `{ "detections": [ ... ] }`, `{ "predictions": [ ... ] }`, `{ "results": [ ... ] }`
    3. Image-keyed maps: `{ "img_001.jpg": [ { "bbox": ... }, ... ] }`

    Returns:
        (flat_detection_list, schema_format_type, schema_envelope_template)
    """
    if isinstance(raw_payload, list):
        return raw_payload, "list", {}

    if isinstance(raw_payload, dict):
        envelope_keys = ["detections", "predictions", "results", "annotations", "objects", "items"]
        for key in envelope_keys:
            if key in raw_payload and isinstance(raw_payload[key], list):
                template = dict(raw_payload)
                template[key] = []
                return raw_payload[key], f"envelope_{key}", template

        # Check if keys are image filenames
        flat_list = []
        is_image_map = False
        for k, v in raw_payload.items():
            if isinstance(v, list) and (k.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")) or "/" in k):
                is_image_map = True
                for item in v:
                    if isinstance(item, dict):
                        item_copy = dict(item)
                        item_copy.setdefault("image_name", k)
                        flat_list.append(item_copy)

        if is_image_map:
            return flat_list, "image_map", {k: [] for k in raw_payload.keys()}

    return [], "unknown", {}


def generate_crop_and_overlay(
    image_path: str,
    bbox: Dict[str, float],
    class_name: str,
    job_id: str,
    det_index: int,
) -> Tuple[str, str, bytes]:
    """
    Extracts 15% padded crop and generates annotated overlay image with drawn bounding box.
    Returns (rel_crop_path, rel_annotated_path, crop_bytes).
    """
    with Image.open(image_path) as img:
        img_rgb = img.convert('RGB')
        img_w, img_h = img_rgb.size

        # Compute crop box with 15% contextual padding
        padding_ratio = float(os.getenv('STAGE2_BBOX_PADDING_RATIO', '0.15'))
        bw = bbox['xmax'] - bbox['xmin']
        bh = bbox['ymax'] - bbox['ymin']
        pad_x = bw * padding_ratio
        pad_y = bh * padding_ratio

        c_xmin = max(0, int(bbox['xmin'] - pad_x))
        c_ymin = max(0, int(bbox['ymin'] - pad_y))
        c_xmax = min(img_w, int(bbox['xmax'] + pad_x))
        c_ymax = min(img_h, int(bbox['ymax'] + pad_y))

        crop = img_rgb.crop((c_xmin, c_ymin, c_xmax, c_ymax))

        # Resize crop if larger than 768px for CPU VLM efficiency
        if crop.width > 768:
            aspect = crop.height / crop.width
            crop = crop.resize((768, int(768 * aspect)), Image.Resampling.LANCZOS)

        # Create annotated overlay image with bounding box
        overlay = img_rgb.copy()
        draw = ImageDraw.Draw(overlay)
        box_coords = [bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']]

        # Color: Emerald (#10b981) for box
        draw.rectangle(box_coords, outline="#10b981", width=4)
        label_text = f" {class_name} "
        draw.rectangle([bbox['xmin'], max(0, bbox['ymin'] - 20), bbox['xmin'] + len(label_text) * 9, bbox['ymin']], fill="#10b981")
        draw.text((bbox['xmin'] + 2, max(0, bbox['ymin'] - 18)), label_text, fill="#ffffff")

        # Save files
        crops_dir = os.path.join(settings.MEDIA_ROOT, 'crops', str(job_id))
        annotated_dir = os.path.join(settings.MEDIA_ROOT, 'annotated', str(job_id))
        os.makedirs(crops_dir, exist_ok=True)
        os.makedirs(annotated_dir, exist_ok=True)

        crop_filename = f"crop_{det_index:04d}.jpg"
        annotated_filename = f"overlay_{det_index:04d}.jpg"

        crop_disk = os.path.join(crops_dir, crop_filename)
        annotated_disk = os.path.join(annotated_dir, annotated_filename)

        crop.save(crop_disk, format='JPEG', quality=90)
        overlay.save(annotated_disk, format='JPEG', quality=85)

        with open(crop_disk, 'rb') as f:
            crop_bytes = f.read()

        rel_crop = f"crops/{job_id}/{crop_filename}"
        rel_annotated = f"annotated/{job_id}/{annotated_filename}"

        return rel_crop, rel_annotated, crop_bytes


def _evaluate_single_detection(
    item: Dict[str, Any],
    idx: int,
    image_search_dirs: List[str],
    job: Job,
) -> Tuple[DetectionRecord, Dict[str, Any]]:
    """Evaluates a single proposed detection against visual evidence and VLM."""
    det_id = str(item.get('id') or f"det_{idx + 1}")
    img_name = str(item.get('image_name') or item.get('image') or '')
    class_name = str(item.get('class_name') or item.get('label') or 'defect')
    orig_conf = float(item.get('confidence', item.get('score', 1.0)))
    raw_bbox = item.get('bbox', [0, 0, 100, 100])

    # Resolve image path
    matched_image_path = None
    for s_dir in image_search_dirs:
        candidate = os.path.join(s_dir, img_name)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            matched_image_path = candidate
            break
        base_name = os.path.basename(img_name)
        candidate_base = os.path.join(s_dir, base_name)
        if os.path.exists(candidate_base) and os.path.isfile(candidate_base):
            matched_image_path = candidate_base
            break

    if not matched_image_path:
        record = DetectionRecord(
            job=job,
            detection_id=det_id,
            image_name=img_name,
            class_name=class_name,
            original_confidence=orig_conf,
            bbox={},
            ai_status=DetectionRecord.STATUS_NEEDS_REVIEW,
            ai_confidence=0.0,
            reason=f"Corresponding image file '{img_name}' could not be located on server.",
        )
        export_dict = {
            **item,
            "ai_status": record.ai_status,
            "ai_confidence": record.ai_confidence,
            "reason": record.reason,
        }
        return record, export_dict

    try:
        with Image.open(matched_image_path) as img:
            img_w, img_h = img.size

        norm_bbox = normalize_bounding_box(raw_bbox, img_w, img_h)
        rel_crop, rel_annotated, crop_bytes = generate_crop_and_overlay(
            matched_image_path, norm_bbox, class_name, str(job.id), idx + 1
        )

        prompt = STAGE2_VALIDATION_PROMPT_TEMPLATE.format(class_name=class_name)
        vlm_resp = ai_client.query(crop_bytes, prompt)

        verdict_status = vlm_resp.get('status')
        if verdict_status not in [
            DetectionRecord.STATUS_CORRECT,
            DetectionRecord.STATUS_INCORRECT,
            DetectionRecord.STATUS_NEEDS_REVIEW,
        ]:
            verdict_status = DetectionRecord.STATUS_NEEDS_REVIEW

        v_conf = float(vlm_resp.get('confidence', 0.8))
        v_reason = str(vlm_resp.get('reason', 'Verification based on visual road surface characteristics.'))

        record = DetectionRecord(
            job=job,
            detection_id=det_id,
            image_name=img_name,
            class_name=class_name,
            original_confidence=orig_conf,
            bbox=norm_bbox,
            ai_status=verdict_status,
            ai_confidence=v_conf,
            reason=v_reason,
            crop_image=rel_crop,
            annotated_image=rel_annotated,
            raw_response=vlm_resp,
        )
        export_dict = {
            **item,
            "normalized_bbox": norm_bbox,
            "ai_status": verdict_status,
            "ai_confidence": v_conf,
            "reason": v_reason,
        }
        return record, export_dict

    except Exception as e:
        logger.warning(f"Error processing detection {det_id}: {e}")
        record = DetectionRecord(
            job=job,
            detection_id=det_id,
            image_name=img_name,
            class_name=class_name,
            original_confidence=orig_conf,
            bbox={},
            ai_status=DetectionRecord.STATUS_NEEDS_REVIEW,
            ai_confidence=0.0,
            reason=f"Processing error: {str(e)}",
        )
        export_dict = {
            **item,
            "ai_status": record.ai_status,
            "ai_confidence": record.ai_confidence,
            "reason": record.reason,
        }
        return record, export_dict


def export_schema_preserving_results(
    job_id: str,
    validated_export_list: List[Dict[str, Any]],
    schema_format: str,
    schema_template: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Exports validated detections in the caller's schema format,
    and packages JSON + crops + overlays into a zip bundle.
    """
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports', str(job_id))
    os.makedirs(exports_dir, exist_ok=True)
    json_path = os.path.join(exports_dir, 'validated_detections.json')
    zip_path = os.path.join(exports_dir, 'validated_bundle.zip')

    # Construct schema-preserved payload
    if schema_format.startswith("envelope_"):
        key = schema_format.split("envelope_")[1]
        out_payload = dict(schema_template)
        out_payload[key] = validated_export_list
    elif schema_format == "image_map":
        out_payload = {k: [] for k in schema_template.keys()}
        for item in validated_export_list:
            img = item.get("image_name", "")
            if img in out_payload:
                out_payload[img].append(item)
            else:
                out_payload.setdefault(img, []).append(item)
    else:
        out_payload = {
            "job_id": str(job_id),
            "total_detections": len(validated_export_list),
            "results": validated_export_list,
        }

    with open(json_path, 'w') as f:
        json.dump(out_payload, f, indent=2)

    # Package into ZIP archive
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(json_path, arcname='validated_detections.json')

            crops_dir = os.path.join(settings.MEDIA_ROOT, 'crops', str(job_id))
            annotated_dir = os.path.join(settings.MEDIA_ROOT, 'annotated', str(job_id))

            for directory, arc_folder in [(crops_dir, 'crops'), (annotated_dir, 'annotated')]:
                if os.path.exists(directory):
                    for fname in os.listdir(directory):
                        fpath = os.path.join(directory, fname)
                        if os.path.isfile(fpath):
                            zipf.write(fpath, arcname=f"{arc_folder}/{fname}")
    except Exception as ze:
        logger.warning(f"Could not construct zip bundle for job {job_id}: {ze}")

    return json_path, zip_path


@transaction.atomic
def run_validation_pipeline(
    job_id: str,
    detections_data: Any,
    image_search_dirs: List[str],
) -> str:
    """
    Executes Stage 2 Detection Validation:
    - Ingests universal payload formats.
    - Normalizes bounding boxes and generates context crops.
    - Validates detections concurrently using ThreadPoolExecutor.
    - Persists DetectionRecord rows and exports schema-preserving JSON + ZIP.
    """
    job = Job.objects.get(id=job_id)
    try:
        flat_detections, schema_format, schema_template = parse_detection_payload(detections_data)
        total = len(flat_detections)

        if total == 0:
            update_job_progress_service(job, 100, "Zero detections found in input", status=Job.STATUS_DONE)
            return ""

        update_job_progress_service(job, 10, f"Validating {total} detections...", status=Job.STATUS_RUNNING)

        max_workers = int(os.getenv('STAGE2_CONCURRENT_DETECTIONS', '2'))
        validated_records: List[DetectionRecord] = []
        validated_export_list: List[Dict[str, Any]] = []

        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_evaluate_single_detection, item, idx, image_search_dirs, job): idx
                for idx, item in enumerate(flat_detections)
            }

            results_by_idx: Dict[int, Tuple[DetectionRecord, Dict[str, Any]]] = {}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                completed_count += 1
                percent = 10 + int((completed_count / total) * 80)
                update_job_progress_service(job, percent, f"Evaluated {completed_count}/{total} detections with AI...")

                try:
                    rec, export_item = future.result()
                    results_by_idx[idx] = (rec, export_item)
                except Exception as e:
                    logger.error(f"Detection evaluation {idx} failed in worker: {e}")

        # Preserve original order
        for idx in range(total):
            if idx in results_by_idx:
                rec, export_item = results_by_idx[idx]
                validated_records.append(rec)
                validated_export_list.append(export_item)

        # Bulk save records
        DetectionRecord.objects.bulk_create(validated_records)

        # Export schema-preserving JSON and ZIP
        json_path, _ = export_schema_preserving_results(
            str(job.id), validated_export_list, schema_format, schema_template
        )

        update_job_progress_service(job, 100, f"Completed validation of {total} detections", status=Job.STATUS_DONE)
        return json_path

    except Exception as exc:
        logger.exception(f"Stage 2 validation failed for job {job_id}: {exc}")
        mark_job_failed_service(job, str(exc))
        raise
