from pravaha_data.demo.scenario import (
    DemoStage,
    build_demo_fused_state,
    iter_demo_fused_states,
)
from pravaha_data.models.provenance import DataStatus


def test_demo_scenario_is_deterministic():
    first = [state.model_dump(mode="json") for state in iter_demo_fused_states()]
    second = [state.model_dump(mode="json") for state in iter_demo_fused_states()]

    assert first == second


def test_demo_scenario_deteriorates_observed_conditions_without_predictions():
    states = list(iter_demo_fused_states())

    rainfall = [state.rainfall.intensity.value for state in states]
    soil = [state.soil.saturation for state in states]

    assert rainfall == sorted(rainfall)
    assert soil == sorted(soil)
    assert states[0].rainfall.intensity.value < states[-1].rainfall.intensity.value
    assert states[0].soil.saturation < states[-1].soil.saturation


def test_demo_scenario_preserves_simulated_provenance():
    state = build_demo_fused_state(DemoStage.SEVERE)

    assert state.rainfall.intensity.status == DataStatus.SIMULATED
    assert state.soil.status == DataStatus.SIMULATED
    assert state.rainfall.rain_1h.status == DataStatus.DERIVED
