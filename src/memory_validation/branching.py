"""Intervention declarations. Raw-format edits remain the adapter's responsibility."""

from dataclasses import dataclass

from memory_validation.schemas import MemorySnapshot


@dataclass(frozen=True)
class NoIntervention:
    pass


@dataclass(frozen=True)
class MaskMemoryItem:
    memory_id: str


@dataclass(frozen=True)
class NoMemory:
    pass


def mask_mapping_memory(snapshot: MemorySnapshot, intervention) -> MemorySnapshot:
    """Only for adapters whose raw memory is an ID->item mapping (including fake).

    This is deliberately not a generic masker for upstream rule/workflow formats.
    """
    raw = snapshot.raw
    if not isinstance(raw, dict):
        raise TypeError("This adapter requires mapping memory")
    metadata = snapshot.metadata
    if isinstance(intervention, MaskMemoryItem):
        if intervention.memory_id not in raw:
            raise ValueError("Target memory item does not exist")
        del raw[intervention.memory_id]
        metadata = [item for item in metadata if item["memory_id"] != intervention.memory_id]
    elif isinstance(intervention, NoMemory):
        raw, metadata = {}, []
    elif not isinstance(intervention, NoIntervention):
        raise TypeError("Unsupported intervention")
    return MemorySnapshot.capture(raw, metadata)
