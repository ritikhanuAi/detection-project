"""
Gold-Standard Dataset Labeler Script.
Uses Google Gemini Flash to generate ground-truth labels and rationale for uncurated road defect detections.
"""

import os
import sys
import json
import base64
import argparse
from typing import Dict, Any

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.ai_engine.vlm_client import ai_client
from apps.ai_engine.prompts import STAGE2_VALIDATION_PROMPT_TEMPLATE
from apps.validation.services import normalize_bounding_box, generate_crop_and_overlay
from PIL import Image


def generate_gold_standard_labels(input_json: str, images_dir: str, output_json: str):
    print("=" * 75)
    print(" RoadAthena AI: Gold-Standard Dataset Labeler (Gemini Engine)")
    print("=" * 75)

    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Input detections JSON not found: {input_json}")

    with open(input_json, 'r') as f:
        detections = json.load(f)

    print(f"Loaded {len(detections)} candidate detections from: {input_json}")
    labeled_results = []

    for idx, item in enumerate(detections):
        det_id = item.get('id', f"gold_{idx+1}")
        image_name = item.get('image', item.get('image_name', ''))
        class_name = item.get('class_name', item.get('label', 'defect'))
        bbox = item.get('bbox', [0, 0, 100, 100])

        img_path = os.path.join(images_dir, image_name)
        if not os.path.exists(img_path):
            print(f"[!] Warning: Image {image_name} not found, skipping...")
            continue

        print(f"[{idx+1}/{len(detections)}] Labeling {det_id} ({class_name} on {image_name})...")

        with Image.open(img_path) as img:
            w, h = img.size

        norm_bbox = normalize_bounding_box(bbox, w, h)
        _, _, crop_bytes = generate_crop_and_overlay(
            img_path, norm_bbox, class_name, job_id="gold_standard", det_index=idx + 1
        )

        prompt = (
            STAGE2_VALIDATION_PROMPT_TEMPLATE.format(class_name=class_name)
            + "\nBe highly objective and rigorous. Differentiate real structural asphalt/concrete damage from non-damage features like shadows, wet surfaces, patches, and road hardware."
        )

        response = ai_client.query(crop_bytes, prompt)
        status = response.get('status', 'Needs Review')
        conf = response.get('confidence', 0.9)
        reason = response.get('reason', '')

        is_valid = (status == 'Correct')

        labeled_item = {
            **item,
            "normalized_bbox": norm_bbox,
            "ground_truth_valid": is_valid,
            "gold_standard_status": status,
            "gold_standard_confidence": conf,
            "gold_standard_reason": reason,
            "verified_by": "Gemini-Flash-Expert"
        }
        labeled_results.append(labeled_item)

    with open(output_json, 'w') as f:
        json.dump(labeled_results, f, indent=2)

    print("\n" + "=" * 75)
    print(f"[+] Successfully generated gold-standard dataset: {output_json}")
    print(f"[+] Total items labeled: {len(labeled_results)}")
    print("=" * 75)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate gold-standard labels using Gemini Flash")
    parser.add_argument('--input', type=str, default='samples/sample_detections.json')
    parser.add_argument('--images', type=str, default='samples/images')
    parser.add_argument('--output', type=str, default='samples/gold_standard_detections.json')
    args = parser.parse_args()

    generate_gold_standard_labels(args.input, args.images, args.output)
