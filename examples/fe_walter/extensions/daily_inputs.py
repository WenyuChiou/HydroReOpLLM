"""Named daily inputs for original-compatible reservoir prompt builders.

These values are trace metadata. The native builder determines which fields reach
the LLM, preserving original text and excluding hidden availability information.

Role: Describe daily variables retained by reference-strategy traces.

Connections and data: reference_backend supplies the observation, reservoir profile and
committed native history. reference_variables returns beginning storage, inflow in
SI/native units and history metadata. This trace inventory does not imply every field is
inserted into the actual native prompt.
"""
from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.contracts import ReservoirObservation


def reference_variables(observation, profile_id, history=()):
    checked=ReservoirObservation(**observation)
    if not isinstance(profile_id,str) or not profile_id.strip():
        raise ValueError('reservoir profile ID must be explicit')
    return json_snapshot({
        'schema_version':'reservoir-daily-inputs.v1',
        'reservoir_profile':profile_id,
        'date':checked.timestamp[:10],
        'timestep':checked.timestep,
        'inflow_cms':checked.inflow_cms,
        'inflow_cfs':checked.inflow_cms/0.028316847,
        'storage_start_m3':checked.state['storage_m3'],
        'native_history':list(history),
        'history_semantics':'prior requested and implemented outflows; appended after physical commit',
    })
