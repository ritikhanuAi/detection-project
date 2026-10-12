"""Stage 1 Road Profiling pipeline services."""
import os
import time
import logging
from collections import Counter
from statistics import median
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from django.conf import settings
from django.db import transaction

from apps.core.exceptions import PipelineError, VLMUnavailable
from apps.core.imaging import (
    downscale_to_width,
    laplacian_variance,
    imwrite_unicode,
    bgr_to_jpeg_bytes,
)
from apps.jobs.models import Job
from apps.jobs.services import update_job_progress_service, mark_job_failed_service
from apps.ai_engine.vlm_client import ai_client
from apps.ai_engine.parsers import coerce_enum, coerce_float, coerce_int
from apps.ai_engine.prompts import STAGE1_ROAD_PROFILING_PROMPT
from .models import RoadProfile, Keyframe

logger = logging.getLogger(__name__)


def extract_sharp_frames(
    video_path: str,
    job_id: str,
    sample_count: int = 8,
    blur_threshold: float = 100.0,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Advanced multi-candidate frame extraction:
    1. Over-samples candidate frames (sample_count * 4).
    2. Calculates Laplacian variance sharpness.
    3. Rejects blurry frames using blur_threshold with adaptive relaxing (down to 30.0).
    4. Selects the top sharpest frames and restores chronological order.
    5. Downscales to max 768px and saves to disk.

    Returns:
        (extracted_frame_records, frames_sampled_count, frames_rejected_blur_count)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file at {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if total_frames <= 0:
        cap.release()
        raise ValueError("Video has zero readable frames.")

    # Over-sample candidates across duration
    oversample_factor = 4
    total_candidates = min(total_frames, max(sample_count * oversample_factor, 16))
    candidate_indices = np.linspace(0, total_frames - 1, total_candidates, dtype=int)

    candidates = []
    rejected_blur = 0

    for f_idx in candidate_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f_idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        sharpness = laplacian_variance(frame)
        timestamp_s = round(float(f_idx) / fps, 2)
        candidates.append({
            "frame_number": int(f_idx),
            "timestamp_s": timestamp_s,
            "sharpness": sharpness,
            "frame": frame,
        })

    cap.release()

    if not candidates:
        raise ValueError("Failed to extract any readable candidate frames from video.")

    frames_sampled = len(candidates)

    # 1. Filter candidates by blur_threshold
    sharp_candidates = [c for c in candidates if c["sharpness"] >= blur_threshold]
    rejected_blur = frames_sampled - len(sharp_candidates)

    # 2. Adaptive relaxing: If blur threshold filtered out too many frames, relax down to 30.0
    active_thresh = blur_threshold
    if len(sharp_candidates) < sample_count:
        adaptive_threshold = 30.0
        sharp_candidates = [c for c in candidates if c["sharpness"] >= adaptive_threshold]
        active_thresh = adaptive_threshold
        logger.info(
            f"Relaxed blur threshold to {adaptive_threshold} for Job {job_id}. "
            f"Candidates qualified: {len(sharp_candidates)}"
        )

    # 3. If still fewer than requested, sort all candidates by sharpness
    if len(sharp_candidates) < sample_count:
        sharp_candidates = sorted(candidates, key=lambda c: c["sharpness"], reverse=True)

    # 4. Select top sample_count sharpest candidates
    top_candidates = sorted(sharp_candidates, key=lambda c: c["sharpness"], reverse=True)[:sample_count]

    # 5. Restore chronological order for natural video progression and UI carousel
    selected_in_order = sorted(top_candidates, key=lambda c: c["frame_number"])

    output_dir = os.path.join(settings.MEDIA_ROOT, 'frames', str(job_id))
    os.makedirs(output_dir, exist_ok=True)

    extracted_records = []
    for idx, cand in enumerate(selected_in_order):
        frame = cand["frame"]
        h, w = frame.shape[:2]
        if w > 768:
            frame = downscale_to_width(frame, max_width=768)

        filename = f"frame_{idx + 1:02d}.jpg"
        disk_path = os.path.join(output_dir, filename)
        imwrite_unicode(disk_path, frame, quality=88)

        with open(disk_path, 'rb') as f:
            img_bytes = f.read()

        rel_path = f"frames/{job_id}/{filename}"
        extracted_records.append({
            "index": idx + 1,
            "frame_number": cand["frame_number"],
            "timestamp_s": cand["timestamp_s"],
            "sharpness": round(cand["sharpness"], 2),
            "disk_path": disk_path,
            "rel_path": rel_path,
            "image_bytes": img_bytes,
        })

    return extracted_records, frames_sampled, rejected_blur


def select_model_configuration(
    road_type: str,
    pavement_type: str,
    carriageway_type: str,
    lanes: int,
) -> str:
    """Rules matrix mapping the road profile attributes to optimal defect detector configurations."""
    rt_lower = road_type.lower()
    pt_lower = pavement_type.lower()
    cw_lower = carriageway_type.lower()

    if 'highway' in rt_lower or 'arterial' in rt_lower:
        if 'concrete' in pt_lower or 'composite' in pt_lower:
            return 'RT-DETR-HighSpeed-RigidPavement-Config'
        return 'YOLOv8x-HighSpeed-FlexibleAsphalt-Config'
    elif 'urban' in rt_lower or 'local' in rt_lower or 'collector' in rt_lower:
        if 'concrete' in pt_lower:
            return 'HRNet-Urban-RigidPavement-Config'
        return 'YOLOv8m-Urban-MultiClassPavement-Config'
    else:  # Rural or Unknown
        if lanes <= 1 or 'undivided' in cw_lower or 'single' in cw_lower:
            return 'YOLOv8s-Rural-NarrowPavement-Config'
        return 'YOLOv8m-Rural-GeneralPavement-Config'


def _vote_categorical(values: List[str], weights: List[float], default: str) -> Tuple[str, float, Dict[str, int]]:
    """Confidence-weighted voting for categorical attributes."""
    if not values:
        return default, 0.0, {}

    tally: Counter = Counter()
    for val, w in zip(values, weights):
        if val:
            tally[val] += max(w, 0.05)

    if not tally:
        return default, 0.0, {}

    winner, win_weight = tally.most_common(1)[0]
    total_weight = sum(tally.values())
    agreement = round(win_weight / max(total_weight, 0.001), 3)
    counts = dict(Counter(v for v in values if v))
    return winner, agreement, counts


def analyze_single_frame(img_bytes: bytes) -> Dict[str, Any]:
    """Analyzes a single frame image using VLM with tolerant schema coercion."""
    raw_result = ai_client.query(img_bytes, STAGE1_ROAD_PROFILING_PROMPT)

    road_types_allowed = ['Highway', 'Arterial', 'Collector', 'Local Street', 'Rural Road', 'Service Road', 'Urban', 'Rural']
    pavements_allowed = ['Asphalt', 'Concrete', 'Composite', 'Gravel', 'Unpaved']
    carriageways_allowed = ['Divided', 'Undivided', 'Single Carriageway', 'Dual Carriageway', 'One-way']

    rt = coerce_enum(raw_result.get('road_type'), road_types_allowed, default=None)
    pt = coerce_enum(raw_result.get('pavement_type'), pavements_allowed, default=None)
    cw = coerce_enum(raw_result.get('carriageway_type'), carriageways_allowed, default=None)
    ln = coerce_int(raw_result.get('lanes'), default=None, minimum=1, maximum=16)
    wd = coerce_float(raw_result.get('estimated_width_m'), default=None, minimum=2.0, maximum=60.0)

    return {
        'road_type': rt,
        'pavement_type': pt,
        'carriageway_type': cw,
        'lanes': ln,
        'estimated_width_m': wd,
        'explanation': str(raw_result.get('explanation', '')),
        'valid': bool(rt or pt or cw or ln or wd),
    }


def aggregate_road_profile_consensus(
    frame_analyses: List[Dict[str, Any]],
    total_frames: int,
) -> Dict[str, Any]:
    """
    Computes confidence-weighted consensus and applies road geometry sanity checks.
    Raises PipelineError if zero frames returned valid attributes.
    """
    valid_frames = [f for f in frame_analyses if f.get('valid')]
    if not valid_frames:
        raise PipelineError(
            "The model returned no usable road attributes for any analyzed frame. "
            "Please verify VLM model availability or provider configuration."
        )

    road_types = []
    pavements = []
    carriageways = []
    lanes_list = []
    widths = []
    weights = []

    for f in frame_analyses:
        # Sharpness or completeness weight
        w = 1.0 if f.get('valid') else 0.1
        weights.append(w)
        if f.get('road_type'):
            road_types.append(f['road_type'])
        if f.get('pavement_type'):
            pavements.append(f['pavement_type'])
        if f.get('carriageway_type'):
            carriageways.append(f['carriageway_type'])
        if f.get('lanes'):
            lanes_list.append(f['lanes'])
        if f.get('estimated_width_m'):
            widths.append(f['estimated_width_m'])

    # Weighted categorical votes
    final_road_type, conf_rt, votes_rt = _vote_categorical(road_types, [1.0] * len(road_types), default='Urban')
    final_pavement, conf_pt, votes_pt = _vote_categorical(pavements, [1.0] * len(pavements), default='Asphalt')
    final_carriageway, conf_cw, votes_cw = _vote_categorical(carriageways, [1.0] * len(carriageways), default='Undivided')
    final_lanes = Counter(lanes_list).most_common(1)[0][0] if lanes_list else 2
    conf_ln = round(lanes_list.count(final_lanes) / max(len(lanes_list), 1), 2) if lanes_list else 0.5

    # Road geometry metric sanity check
    # Single lane physical bounds: 2.5m - 4.5m; standard default 3.4m
    standard_lane_width = 3.6 if final_road_type == 'Highway' else 3.2
    expected_width = final_lanes * standard_lane_width
    raw_median_width = median(widths) if widths else expected_width

    # Plausibility check: clamp single lane width between 2.5m and 4.5m
    inferred_lane_width = raw_median_width / max(final_lanes, 1)
    if inferred_lane_width < 2.5 or inferred_lane_width > 4.5:
        # Blend towards expected lane-count geometry
        final_width = round((raw_median_width * 0.3) + (expected_width * 0.7), 1)
        conf_wd = 0.65
    else:
        final_width = round(raw_median_width, 1)
        conf_wd = 0.88

    conf_scores = {
        'road_type': conf_rt,
        'pavement_type': conf_pt,
        'carriageway_type': conf_cw,
        'lanes': conf_ln,
        'estimated_width_m': conf_wd,
    }

    votes = {
        'road_type': votes_rt,
        'pavement_type': votes_pt,
        'carriageway_type': votes_cw,
        'lanes': dict(Counter(lanes_list)),
    }

    overall_conf = round(float(np.mean(list(conf_scores.values()))), 2)
    selected_config = select_model_configuration(final_road_type, final_pavement, final_carriageway, final_lanes)

    return {
        'road_type': final_road_type,
        'pavement_type': final_pavement,
        'carriageway_type': final_carriageway,
        'lanes': final_lanes,
        'estimated_width_m': final_width,
        'confidence_scores': conf_scores,
        'confidences': conf_scores,
        'votes': votes,
        'overall_confidence': overall_conf,
        'model_config_selected': selected_config,
    }


@transaction.atomic
def run_road_profiling_pipeline(job_id: str) -> RoadProfile:
    """
    Complete Stage 1 pipeline:
    1. Extracts sharp keyframes with multi-candidate sampling and adaptive blur rejection.
    2. Runs VLM per frame.
    3. Aggregates via confidence-weighted voting and metric geometry sanity checking.
    4. Persists RoadProfile and Keyframe database records.
    """
    job = Job.objects.get(id=job_id)
    start_time = time.time()

    try:
        update_job_progress_service(job, 10, "Sampling video frames with blur variance filter", status=Job.STATUS_RUNNING)
        sample_count = int(os.getenv('STAGE1_SAMPLE_FRAMES', '8'))
        blur_thresh = float(os.getenv('STAGE1_LAPLACIAN_BLUR_THRESHOLD', '100.0'))

        frames, frames_sampled, rejected_blur = extract_sharp_frames(
            job.input_file.path,
            str(job.id),
            sample_count=sample_count,
            blur_threshold=blur_thresh,
        )
        total_frames = len(frames)
        update_job_progress_service(job, 30, f"Extracted {total_frames} sharp frames. Analyzing with AI...")

        frame_analyses = []
        frame_details = []
        rel_frame_paths = []

        for i, f_rec in enumerate(frames):
            percent = 30 + int((i / total_frames) * 50)
            update_job_progress_service(job, percent, f"Analyzing frame {i + 1}/{total_frames} with VLM...")

            try:
                analysis = analyze_single_frame(f_rec["image_bytes"])
            except VLMUnavailable as ve:
                logger.error(f"VLM unavailable for frame {i + 1}: {ve}")
                analysis = {
                    'road_type': None,
                    'pavement_type': None,
                    'carriageway_type': None,
                    'lanes': None,
                    'estimated_width_m': None,
                    'explanation': f"VLM unavailable: {ve}",
                    'valid': False,
                }

            analysis_detail = {
                'frame': f_rec["rel_path"],
                'frame_number': f_rec["frame_number"],
                'timestamp_s': f_rec["timestamp_s"],
                'sharpness': f_rec["sharpness"],
                **analysis,
            }

            frame_analyses.append(analysis)
            frame_details.append(analysis_detail)
            rel_frame_paths.append(f_rec["rel_path"])

        update_job_progress_service(job, 85, "Aggregating consensus and validating road geometry...")

        consensus = aggregate_road_profile_consensus(frame_analyses, total_frames)
        processing_seconds = round(time.time() - start_time, 2)

        profile, _ = RoadProfile.objects.update_or_create(
            job=job,
            defaults={
                'road_type': consensus['road_type'],
                'pavement_type': consensus['pavement_type'],
                'carriageway_type': consensus['carriageway_type'],
                'lanes': consensus['lanes'],
                'estimated_width_m': consensus['estimated_width_m'],
                'confidence_scores': consensus['confidence_scores'],
                'confidences': consensus['confidences'],
                'votes': consensus['votes'],
                'overall_confidence': consensus['overall_confidence'],
                'model_config_selected': consensus['model_config_selected'],
                'extracted_frames': rel_frame_paths,
                'frame_details': frame_details,
                'frames_sampled': frames_sampled,
                'frames_analysed': total_frames,
                'frames_rejected_blur': rejected_blur,
                'processing_seconds': processing_seconds,
                'ai_provider': getattr(ai_client, 'provider_name', os.getenv('AI_PROVIDER', 'ollama')),
            }
        )

        # Populate Keyframe records
        Keyframe.objects.filter(profile=profile).delete()
        keyframe_objs = []
        for i, f_rec in enumerate(frames):
            detail = frame_details[i]
            keyframe_objs.append(
                Keyframe(
                    profile=profile,
                    index=f_rec["index"],
                    frame_number=f_rec["frame_number"],
                    timestamp_s=f_rec["timestamp_s"],
                    sharpness=f_rec["sharpness"],
                    image=f_rec["rel_path"],
                    analysis=detail,
                    analysed=True,
                )
            )
        Keyframe.objects.bulk_create(keyframe_objs)

        update_job_progress_service(job, 100, "Road profiling complete", status=Job.STATUS_DONE)
        return profile

    except Exception as e:
        logger.exception(f"Stage 1 profiling pipeline failed for job {job_id}: {e}")
        mark_job_failed_service(job, str(e))
        raise
