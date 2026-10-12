import pytest
from apps.core.exceptions import PipelineError
from apps.profiling.services import (
    select_model_configuration,
    aggregate_road_profile_consensus,
    _vote_categorical,
)


def test_model_selection_matrix_highway_asphalt():
    cfg = select_model_configuration('Highway', 'Asphalt', 'Divided', 4)
    assert 'HighSpeed' in cfg or 'Asphalt' in cfg


def test_model_selection_matrix_urban_concrete():
    cfg = select_model_configuration('Urban', 'Concrete', 'Undivided', 2)
    assert 'RigidPavement' in cfg or 'Concrete' in cfg


def test_model_selection_matrix_rural_narrow():
    cfg = select_model_configuration('Rural', 'Asphalt', 'Undivided', 1)
    assert 'Narrow' in cfg or 'Rural' in cfg


def test_vote_categorical():
    values = ['Urban', 'Urban', 'Highway']
    weights = [1.0, 1.0, 1.0]
    winner, agreement, counts = _vote_categorical(values, weights, default='Unknown')
    assert winner == 'Urban'
    assert agreement > 0.6
    assert counts['Urban'] == 2


def test_aggregate_consensus_success():
    analyses = [
        {'road_type': 'Urban', 'pavement_type': 'Asphalt', 'carriageway_type': 'Undivided', 'lanes': 2, 'estimated_width_m': 7.0, 'valid': True},
        {'road_type': 'Urban', 'pavement_type': 'Asphalt', 'carriageway_type': 'Undivided', 'lanes': 2, 'estimated_width_m': 7.2, 'valid': True},
        {'road_type': 'Highway', 'pavement_type': 'Asphalt', 'carriageway_type': 'Undivided', 'lanes': 2, 'estimated_width_m': 6.8, 'valid': True},
    ]
    res = aggregate_road_profile_consensus(analyses, total_frames=3)
    assert res['road_type'] == 'Urban'
    assert res['pavement_type'] == 'Asphalt'
    assert res['lanes'] == 2
    assert 6.5 <= res['estimated_width_m'] <= 7.5
    assert res['overall_confidence'] > 0.7
    assert 'votes' in res


def test_aggregate_consensus_raises_on_zero_valid():
    analyses = [
        {'road_type': None, 'pavement_type': None, 'carriageway_type': None, 'lanes': None, 'estimated_width_m': None, 'valid': False},
        {'road_type': None, 'pavement_type': None, 'carriageway_type': None, 'lanes': None, 'estimated_width_m': None, 'valid': False},
    ]
    with pytest.raises(PipelineError):
        aggregate_road_profile_consensus(analyses, total_frames=2)
