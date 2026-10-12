import pytest
from apps.validation.bbox import normalize_bounding_box, BBoxFormat
from apps.validation.services import parse_detection_payload


def test_normalize_xyxy_absolute():
    bbox = [100, 150, 400, 450]
    result = normalize_bounding_box(bbox, 1920, 1080)
    assert result['xmin'] == 100.0
    assert result['ymin'] == 150.0
    assert result['xmax'] == 400.0
    assert result['ymax'] == 450.0
    assert result['width'] == 300.0
    assert result['height'] == 300.0


def test_normalize_xywh_absolute():
    bbox = [100, 200, 50, 80]
    result = normalize_bounding_box(bbox, 1000, 1000)
    assert result['xmin'] == 100.0
    assert result['ymin'] == 200.0
    assert result['xmax'] == 150.0
    assert result['ymax'] == 280.0


def test_normalize_normalized_coordinates():
    bbox = [0.1, 0.2, 0.4, 0.5]
    result = normalize_bounding_box(bbox, 1000, 1000)
    assert result['xmin'] == 100.0
    assert result['ymin'] == 200.0
    assert result['xmax'] == 400.0
    assert result['ymax'] == 500.0


def test_boundary_clamping_beyond_edges():
    bbox = [-50, -20, 2500, 1500]
    result = normalize_bounding_box(bbox, 1920, 1080)
    assert result['xmin'] == 0.0
    assert result['ymin'] == 0.0
    assert result['xmax'] == 1920.0
    assert result['ymax'] == 1080.0


def test_cxcywh_format():
    bbox = [200, 300, 100, 80]
    result = normalize_bounding_box(bbox, 1000, 1000, expected_format=BBoxFormat.CXCYWH)
    assert result['xmin'] == 150.0
    assert result['ymin'] == 260.0
    assert result['xmax'] == 250.0
    assert result['ymax'] == 340.0


def test_inverted_coordinate_repair():
    # x2 < x1, y2 < y1
    bbox = [400, 500, 100, 200]
    result = normalize_bounding_box(bbox, 1000, 1000, expected_format=BBoxFormat.XYXY)
    assert result['xmin'] == 100.0
    assert result['xmax'] == 400.0
    assert result['ymin'] == 200.0
    assert result['ymax'] == 500.0


def test_dict_box_parsing():
    raw = {'x': 50, 'y': 60, 'width': 100, 'height': 80}
    result = normalize_bounding_box(raw, 500, 500)
    assert result['xmin'] == 50.0
    assert result['xmax'] == 150.0
    assert result['ymin'] == 60.0
    assert result['ymax'] == 140.0


def test_parse_detection_payload_formats():
    # 1. Raw list
    lst = [{'id': 1}, {'id': 2}]
    res, fmt, _ = parse_detection_payload(lst)
    assert len(res) == 2
    assert fmt == 'list'

    # 2. Envelope
    env = {'detections': [{'id': 1}], 'meta': 'version 1'}
    res, fmt, template = parse_detection_payload(env)
    assert len(res) == 1
    assert fmt == 'envelope_detections'
    assert 'meta' in template

    # 3. Image map
    img_map = {'frame_01.jpg': [{'bbox': [10, 10, 50, 50]}], 'frame_02.jpg': []}
    res, fmt, _ = parse_detection_payload(img_map)
    assert len(res) == 1
    assert fmt == 'image_map'
    assert res[0]['image_name'] == 'frame_01.jpg'
