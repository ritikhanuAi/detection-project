import os
import cv2
import json
import random
import zipfile
import numpy as np

def generate_photorealistic_asphalt(width=480, height=360, is_concrete=False):
    """Generates a realistic road pavement surface with aggregate texture and stone speckling."""
    if is_concrete:
        base_color = np.array([160, 162, 165], dtype=np.float32)
        noise_scale = 12.0
    else:
        base_color = np.array([62, 65, 68], dtype=np.float32)
        noise_scale = 18.0

    # Base pavement plane
    canvas = np.ones((height, width, 3), dtype=np.float32) * base_color

    # Multi-frequency noise for surface roughness
    noise_fine = np.random.normal(0, noise_scale, (height, width, 3)).astype(np.float32)
    noise_coarse = cv2.resize(
        np.random.normal(0, noise_scale * 1.5, (height // 4, width // 4, 3)).astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_CUBIC
    )
    canvas = np.clip(canvas + noise_fine + noise_coarse, 0, 255).astype(np.uint8)

    # Sprinkle aggregate stones (light & dark speckles)
    num_stones = np.random.randint(600, 1200)
    for _ in range(num_stones):
        sx = np.random.randint(0, width)
        sy = np.random.randint(0, height)
        radius = np.random.choice([1, 2])
        stone_val = np.random.choice([35, 45, 110, 140, 180])
        cv2.circle(canvas, (sx, sy), radius, (int(stone_val), int(stone_val), int(stone_val)), -1)

    return canvas


def create_sample_road_video(output_path: str, duration_sec: int = 4, fps: int = 24):
    """Generates a synthetic road survey video with lane markings and pavement texture."""
    width, height = 768, 432
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    for i in range(total_frames):
        # Generate base pavement
        frame = generate_photorealistic_asphalt(width, height)

        # Road boundaries / Curbs
        cv2.line(frame, (80, 0), (40, height), (130, 132, 135), 4)
        cv2.line(frame, (width - 80, 0), (width - 40, height), (130, 132, 135), 4)

        # Center dashed yellow divider (simulating divided/undivided motion)
        offset = (i * 12) % 60
        for y in range(-60 + offset, height, 60):
            cv2.line(frame, (width // 2, y), (width // 2, y + 30), (0, 210, 255), 5)

        # White lane edge lines
        cv2.line(frame, (200, 0), (160, height), (230, 230, 230), 3)
        cv2.line(frame, (width - 200, 0), (width - 160, height), (230, 230, 230), 3)

        out.write(frame)

    out.release()
    print(f"Created sample video: {output_path} ({total_frames} frames)")


def create_sample_detection_dataset(samples_dir: str):
    """Generates 24 realistic road defect and look-alike detection images + ground-truth dataset."""
    images_dir = os.path.join(samples_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    items = [
        # --- 12 Genuine Road Defects (Ground Truth: Valid Defect) ---
        {
            "id": "det_001",
            "image": "road_pothole_deep.jpg",
            "class_name": "pothole",
            "confidence": 0.94,
            "bbox": [160, 130, 300, 250],
            "type": "pothole_deep",
            "ground_truth_valid": True,
            "notes": "Deep cavity with sharp fractured perimeter and interior shadow depth"
        },
        {
            "id": "det_002",
            "image": "road_pothole_shallow.jpg",
            "class_name": "pothole",
            "confidence": 0.88,
            "bbox": [170, 140, 290, 230],
            "type": "pothole_shallow",
            "ground_truth_valid": True,
            "notes": "Shallow surface raveling depression with exposed coarse base"
        },
        {
            "id": "det_003",
            "image": "road_pothole_cluster.jpg",
            "class_name": "pothole",
            "confidence": 0.91,
            "bbox": [140, 110, 330, 260],
            "type": "pothole_cluster",
            "ground_truth_valid": True,
            "notes": "Multi-cavity pothole cluster on deteriorated wearing course"
        },
        {
            "id": "det_004",
            "image": "road_crack_longitudinal.jpg",
            "class_name": "longitudinal crack",
            "confidence": 0.92,
            "bbox": [220, 60, 270, 320],
            "type": "crack_longitudinal",
            "ground_truth_valid": True,
            "notes": "Parallel fatigue crack propagating along wheelpath"
        },
        {
            "id": "det_005",
            "image": "road_crack_transverse.jpg",
            "class_name": "transverse crack",
            "confidence": 0.89,
            "bbox": [80, 170, 400, 220],
            "type": "crack_transverse",
            "ground_truth_valid": True,
            "notes": "Perpendicular thermal contraction fracture across travel lane"
        },
        {
            "id": "det_006",
            "image": "road_crack_alligator_dense.jpg",
            "class_name": "alligator cracking",
            "confidence": 0.95,
            "bbox": [130, 100, 350, 270],
            "type": "alligator_dense",
            "ground_truth_valid": True,
            "notes": "Severe interconnected polygonal fatigue cracking mesh"
        },
        {
            "id": "det_007",
            "image": "road_crack_alligator_mild.jpg",
            "class_name": "alligator cracking",
            "confidence": 0.86,
            "bbox": [150, 120, 320, 250],
            "type": "alligator_mild",
            "ground_truth_valid": True,
            "notes": "Early-stage spiderweb cracking pattern with hairline fissures"
        },
        {
            "id": "det_008",
            "image": "road_crack_edge.jpg",
            "class_name": "edge crack",
            "confidence": 0.87,
            "bbox": [320, 80, 420, 290],
            "type": "crack_edge",
            "ground_truth_valid": True,
            "notes": "Structural failure along unsupported outer road shoulder"
        },
        {
            "id": "det_009",
            "image": "road_crack_block.jpg",
            "class_name": "block cracking",
            "confidence": 0.85,
            "bbox": [140, 90, 340, 260],
            "type": "crack_block",
            "ground_truth_valid": True,
            "notes": "Interconnected rectangular block cracking in aged binder"
        },
        {
            "id": "det_010",
            "image": "road_rutting_depression.jpg",
            "class_name": "rutting",
            "confidence": 0.83,
            "bbox": [180, 70, 300, 300],
            "type": "rutting",
            "ground_truth_valid": True,
            "notes": "Longitudinal surface depression along vehicular wheel track"
        },
        {
            "id": "det_011",
            "image": "road_raveling_aggregate.jpg",
            "class_name": "raveling",
            "confidence": 0.84,
            "bbox": [150, 110, 330, 250],
            "type": "raveling",
            "ground_truth_valid": True,
            "notes": "Progressive aggregate loss and surface pitting erosion"
        },
        {
            "id": "det_012",
            "image": "road_concrete_joint_spall.jpg",
            "class_name": "joint spall",
            "confidence": 0.88,
            "bbox": [120, 160, 360, 220],
            "type": "joint_spall",
            "ground_truth_valid": True,
            "notes": "Severe chipping and spalling along concrete slab joint"
        },

        # --- 12 Deliberate False Positives (Ground Truth: NOT a Defect) ---
        {
            "id": "det_013",
            "image": "road_shadow_tree_fp.jpg",
            "class_name": "crack",
            "confidence": 0.81,
            "bbox": [140, 90, 340, 270],
            "type": "shadow_tree",
            "ground_truth_valid": False,
            "notes": "Overhanging tree branch shadow (False Positive)"
        },
        {
            "id": "det_014",
            "image": "road_shadow_pole_fp.jpg",
            "class_name": "longitudinal crack",
            "confidence": 0.79,
            "bbox": [210, 50, 260, 310],
            "type": "shadow_pole",
            "ground_truth_valid": False,
            "notes": "Linear shadow cast by roadside utility pole (False Positive)"
        },
        {
            "id": "det_015",
            "image": "road_tar_sealant_fp.jpg",
            "class_name": "crack",
            "confidence": 0.87,
            "bbox": [150, 80, 320, 280],
            "type": "tar_sealant",
            "ground_truth_valid": False,
            "notes": "Bituminous rubber crack sealant repair (False Positive)"
        },
        {
            "id": "det_016",
            "image": "road_tar_patch_fp.jpg",
            "class_name": "pothole",
            "confidence": 0.82,
            "bbox": [160, 120, 320, 250],
            "type": "tar_patch",
            "ground_truth_valid": False,
            "notes": "Smooth rectangular slurry seal asphalt maintenance patch (False Positive)"
        },
        {
            "id": "det_017",
            "image": "road_manhole_cover_fp.jpg",
            "class_name": "pothole",
            "confidence": 0.85,
            "bbox": [160, 110, 310, 260],
            "type": "manhole_cover",
            "ground_truth_valid": False,
            "notes": "Cast iron circular sewer manhole casting (False Positive)"
        },
        {
            "id": "det_018",
            "image": "road_drainage_grate_fp.jpg",
            "class_name": "pothole",
            "confidence": 0.78,
            "bbox": [170, 130, 320, 240],
            "type": "drainage_grate",
            "ground_truth_valid": False,
            "notes": "Slotted steel stormwater inlet grate (False Positive)"
        },
        {
            "id": "det_019",
            "image": "road_oil_spill_fp.jpg",
            "class_name": "pothole",
            "confidence": 0.74,
            "bbox": [180, 130, 290, 230],
            "type": "oil_stain",
            "ground_truth_valid": False,
            "notes": "Flat vehicle engine oil fluid surface stain (False Positive)"
        },
        {
            "id": "det_020",
            "image": "road_water_puddle_fp.jpg",
            "class_name": "pothole",
            "confidence": 0.80,
            "bbox": [160, 120, 310, 240],
            "type": "water_puddle",
            "ground_truth_valid": False,
            "notes": "Reflective wet rainwater surface puddle (False Positive)"
        },
        {
            "id": "det_021",
            "image": "road_paint_marking_fp.jpg",
            "class_name": "crack",
            "confidence": 0.77,
            "bbox": [190, 70, 260, 300],
            "type": "paint_marking",
            "ground_truth_valid": False,
            "notes": "Weathered dashed thermoplastic road lane marking (False Positive)"
        },
        {
            "id": "det_022",
            "image": "road_tire_skid_fp.jpg",
            "class_name": "longitudinal crack",
            "confidence": 0.79,
            "bbox": [200, 60, 270, 310],
            "type": "tire_skid",
            "ground_truth_valid": False,
            "notes": "Black rubber vehicle deceleration skid burn mark (False Positive)"
        },
        {
            "id": "det_023",
            "image": "road_expansion_joint_fp.jpg",
            "class_name": "transverse crack",
            "confidence": 0.82,
            "bbox": [90, 170, 390, 210],
            "type": "expansion_joint",
            "ground_truth_valid": False,
            "notes": "Engineered steel neoprene expansion joint (False Positive)"
        },
        {
            "id": "det_024",
            "image": "road_leaves_debris_fp.jpg",
            "class_name": "alligator cracking",
            "confidence": 0.75,
            "bbox": [150, 120, 320, 250],
            "type": "leaves_debris",
            "ground_truth_valid": False,
            "notes": "Scattered organic fallen leaves and twigs on shoulder (False Positive)"
        }
    ]

    for item in items:
        is_conc = (item['type'] in ['joint_spall', 'expansion_joint'])
        img = generate_photorealistic_asphalt(480, 360, is_concrete=is_conc)
        b = item['bbox']
        t = item['type']

        if t == 'pothole_deep':
            # Jagged deep dark cavity with inner depth shadow
            pts = np.array([
                [b[0] + 15, b[1] + 25],
                [b[0] + 45, b[1] + 10],
                [b[2] - 30, b[1] + 15],
                [b[2] - 10, b[1] + 55],
                [b[2] - 15, b[3] - 25],
                [b[0] + 70, b[3] - 10],
                [b[0] + 20, b[3] - 30],
                [b[0] + 5, b[1] + 70]
            ], np.int32)
            cv2.fillPoly(img, [pts], (22, 24, 26))
            cv2.polylines(img, [pts], True, (15, 16, 18), 3)
            # Rim highlight on one side (simulating sunlight relief)
            cv2.polylines(img, [pts[2:5]], False, (115, 120, 125), 2)

        elif t == 'pothole_shallow':
            center = ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
            axes = ((b[2] - b[0]) // 2, (b[3] - b[1]) // 2)
            cv2.ellipse(img, center, axes, 10, 0, 360, (32, 35, 38), -1)
            cv2.ellipse(img, center, axes, 10, 0, 360, (25, 27, 30), 2)

        elif t == 'pothole_cluster':
            for dx, dy, r in [(0, 0, 35), (55, 30, 25), (-40, 20, 28)]:
                cx = (b[0] + b[2]) // 2 + dx
                cy = (b[1] + b[3]) // 2 + dy
                cv2.circle(img, (cx, cy), r, (22, 24, 26), -1)
                cv2.circle(img, (cx, cy), r, (15, 17, 19), 2)

        elif t == 'crack_longitudinal':
            # Jagged continuous vertical fracture
            pts = []
            cx = (b[0] + b[2]) // 2
            for y in range(b[1], b[3] + 1, 15):
                jitter = np.random.randint(-12, 12)
                pts.append([cx + jitter, y])
            pts = np.array(pts, np.int32)
            cv2.polylines(img, [pts], False, (18, 19, 21), 3)
            # Side branches
            cv2.line(img, (pts[3][0], pts[3][1]), (pts[3][0] + 25, pts[3][1] + 20), (18, 19, 21), 2)
            cv2.line(img, (pts[7][0], pts[7][1]), (pts[7][0] - 20, pts[7][1] + 25), (18, 19, 21), 2)

        elif t == 'crack_transverse':
            # Jagged horizontal fracture across lane
            pts = []
            cy = (b[1] + b[3]) // 2
            for x in range(b[0], b[2] + 1, 20):
                jitter = np.random.randint(-8, 8)
                pts.append([x, cy + jitter])
            pts = np.array(pts, np.int32)
            cv2.polylines(img, [pts], False, (18, 19, 21), 3)

        elif t == 'alligator_dense':
            # Interconnected polygonal mesh
            for y in range(b[1], b[3], 24):
                for x in range(b[0], b[2], 28):
                    jx = np.random.randint(-5, 5)
                    jy = np.random.randint(-5, 5)
                    cv2.rectangle(img, (x + jx, y + jy), (x + 26 + jx, y + 22 + jy), (20, 22, 24), 2)

        elif t == 'alligator_mild':
            for y in range(b[1], b[3], 35):
                for x in range(b[0], b[2], 40):
                    cv2.rectangle(img, (x, y), (x + 36, y + 30), (28, 30, 32), 1)

        elif t == 'crack_edge':
            # Road shoulder line + crumbling edge
            cv2.line(img, (b[0] + 10, 0), (b[0] + 10, 360), (220, 220, 220), 3)
            pts = [[b[0] + 20, y] for y in range(b[1], b[3], 20)]
            for p in pts:
                p[0] += np.random.randint(5, 35)
            cv2.polylines(img, [np.array(pts, np.int32)], False, (18, 20, 22), 3)

        elif t == 'crack_block':
            for y in range(b[1], b[3], 45):
                cv2.line(img, (b[0], y), (b[2], y), (20, 22, 24), 2)
            for x in range(b[0], b[2], 50):
                cv2.line(img, (x, b[1]), (x, b[3]), (20, 22, 24), 2)

        elif t == 'rutting':
            # Gradual longitudinal depression with darker compacted shadow
            overlay = img.copy()
            cv2.rectangle(overlay, (b[0], b[1]), (b[2], b[3]), (35, 37, 40), -1)
            img = cv2.addWeighted(img, 0.65, overlay, 0.35, 0)
            cv2.line(img, ((b[0]+b[2])//2, b[1]), ((b[0]+b[2])//2, b[3]), (30, 32, 34), 2)

        elif t == 'raveling':
            # Surface disintegration with coarse pitted holes
            for _ in range(80):
                rx = np.random.randint(b[0], b[2])
                ry = np.random.randint(b[1], b[3])
                cv2.circle(img, (rx, ry), np.random.randint(2, 6), (20, 22, 24), -1)

        elif t == 'joint_spall':
            # Concrete slab joint with jagged spalled edges
            cv2.line(img, (0, 190), (480, 190), (40, 42, 45), 3)
            pts = np.array([
                [b[0]+20, 190], [b[0]+80, 175], [b[2]-60, 170],
                [b[2]-10, 190], [b[2]-40, 205], [b[0]+50, 208]
            ], np.int32)
            cv2.fillPoly(img, [pts], (90, 92, 95))
            cv2.polylines(img, [pts], True, (45, 47, 50), 2)

        # --- False Positives ---
        elif t == 'shadow_tree':
            # Semi-transparent leaf canopy shadow where pavement aggregate remains visible through it!
            overlay = img.copy()
            pts = np.array([
                [b[0] + 10, b[1] + 30], [b[0] + 80, b[1]],
                [b[2] - 40, b[1] + 20], [b[2], b[1] + 90],
                [b[2] - 20, b[3] - 10], [b[0] + 90, b[3]],
                [b[0], b[3] - 40]
            ], np.int32)
            cv2.fillPoly(overlay, [pts], (15, 18, 20))
            # Smooth gaussian blur on shadow edges
            overlay = cv2.GaussianBlur(overlay, (21, 21), 0)
            img = cv2.addWeighted(img, 0.55, overlay, 0.45, 0)

        elif t == 'shadow_pole':
            # Semi-transparent linear pole shadow
            overlay = img.copy()
            cv2.line(overlay, (b[0] + 20, 0), (b[0] + 20, 360), (10, 12, 14), 22)
            overlay = cv2.GaussianBlur(overlay, (15, 15), 0)
            img = cv2.addWeighted(img, 0.60, overlay, 0.40, 0)

        elif t == 'tar_sealant':
            # Smooth glossy black rubber repair line following old crack path
            pts = []
            cx = (b[0] + b[2]) // 2
            for y in range(b[1], b[3] + 1, 25):
                pts.append([cx + np.random.randint(-10, 10), y])
            pts = np.array(pts, np.int32)
            # Thick glossy black rubber bead
            cv2.polylines(img, [pts], False, (12, 12, 14), 9)
            cv2.polylines(img, [pts], False, (22, 22, 25), 5)

        elif t == 'tar_patch':
            # Rectangular slurry seal maintenance patch
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (38, 40, 42), -1)
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (28, 30, 32), 2)

        elif t == 'manhole_cover':
            # Circular cast iron sanitary sewer cover
            cx = (b[0] + b[2]) // 2
            cy = (b[1] + b[3]) // 2
            r = min(b[2] - b[0], b[3] - b[1]) // 2
            cv2.circle(img, (cx, cy), r, (88, 92, 96), -1)
            cv2.circle(img, (cx, cy), r, (115, 120, 125), 4)
            cv2.circle(img, (cx, cy), r - 12, (75, 78, 82), 2)
            cv2.circle(img, (cx, cy), r - 24, (105, 110, 115), 2)
            # Center pick hole
            cv2.circle(img, (cx, cy), 6, (35, 38, 40), -1)

        elif t == 'drainage_grate':
            # Slotted catch basin drainage grate
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (80, 84, 88), -1)
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (120, 125, 130), 3)
            for x in range(b[0] + 12, b[2] - 8, 14):
                cv2.line(img, (x, b[1] + 8), (x, b[3] - 8), (20, 22, 25), 4)

        elif t == 'oil_spill':
            # Flat fluid stain soaked into surface pores
            overlay = img.copy()
            cx = (b[0] + b[2]) // 2
            cy = (b[1] + b[3]) // 2
            cv2.ellipse(overlay, (cx, cy), (45, 35), 25, 0, 360, (25, 27, 29), -1)
            overlay = cv2.GaussianBlur(overlay, (15, 15), 0)
            img = cv2.addWeighted(img, 0.45, overlay, 0.55, 0)

        elif t == 'water_puddle':
            # Puddle with sky reflection
            cx = (b[0] + b[2]) // 2
            cy = (b[1] + b[3]) // 2
            cv2.ellipse(img, (cx, cy), (65, 40), -15, 0, 360, (95, 105, 115), -1)
            cv2.ellipse(img, (cx, cy), (65, 40), -15, 0, 360, (140, 150, 160), 2)

        elif t == 'paint_marking':
            # Weathered white thermoplastic dashed stripe
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (225, 228, 230), -1)
            # Weathering aggregate showing through
            for _ in range(60):
                px = np.random.randint(b[0], b[2])
                py = np.random.randint(b[1], b[3])
                cv2.circle(img, (px, py), 1, (70, 72, 75), -1)

        elif t == 'tire_skid':
            # Dark black rubber skid mark
            overlay = img.copy()
            cx = (b[0] + b[2]) // 2
            cv2.line(overlay, (cx - 15, b[1]), (cx - 15, b[3]), (18, 18, 20), 16)
            cv2.line(overlay, (cx + 15, b[1]), (cx + 15, b[3]), (18, 18, 20), 16)
            overlay = cv2.GaussianBlur(overlay, (7, 7), 0)
            img = cv2.addWeighted(img, 0.45, overlay, 0.55, 0)

        elif t == 'expansion_joint':
            # Clean engineered bridge joint with steel headers
            cy = (b[1] + b[3]) // 2
            cv2.line(img, (0, cy), (480, cy), (25, 26, 28), 6)
            cv2.line(img, (0, cy - 6), (480, cy - 6), (110, 115, 120), 3)
            cv2.line(img, (0, cy + 6), (480, cy + 6), (110, 115, 120), 3)

        elif t == 'leaves_debris':
            # Scattered leaves / pine needles
            for _ in range(35):
                lx = np.random.randint(b[0], b[2])
                ly = np.random.randint(b[1], b[3])
                color = random.choice([(45, 90, 160), (35, 75, 130), (25, 55, 95)])
                cv2.ellipse(img, (lx, ly), (10, 4), np.random.randint(0, 180), 0, 360, (int(color[0]), int(color[1]), int(color[2])), -1)

        file_path = os.path.join(images_dir, item['image'])
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    # Save detections JSON
    json_path = os.path.join(samples_dir, 'sample_detections.json')
    with open(json_path, 'w') as f:
        json.dump(items, f, indent=2)
    print(f"Created {len(items)} sample detections in: {json_path}")

    # Zip images
    zip_path = os.path.join(samples_dir, 'sample_images.zip')
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for item in items:
            p = os.path.join(images_dir, item['image'])
            zf.write(p, arcname=item['image'])
    print(f"Created sample images zip: {zip_path}")


if __name__ == '__main__':
    samples_dir = os.path.join(os.path.dirname(__file__))
    video_path = os.path.join(samples_dir, 'sample_road_survey.mp4')
    create_sample_road_video(video_path)
    create_sample_detection_dataset(samples_dir)
