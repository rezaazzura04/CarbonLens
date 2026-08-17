"""
CarbonLens V8 — ComputedState model.

The single shared output object that all pages consume.
No page may compute its own scores independently.
ComputedState is IMMUTABLE once written — recomputation creates a new version.
"""
from __future__ import annotations
from typing import Optional
from typing import TypedDict

from models.carbon import CarbonInventory
from models.esg import ESGScore, ConfidenceScore
from models.data_quality import DataQualityScore


class ComputedState(TypedDict):
    """
    The canonical, versioned output of one full computation cycle.

    Architecture rules:
    - Every page reads from ComputedState. No page calls services directly.
    - ComputedState is immutable: once written to the repository, its values
      never change. Recomputation creates a NEW ComputedState with version+1.
    - previous_version_id enables audit diff view and undo capability.
    - input_hash enables cache validation: if hash mismatches current dataset,
      the state is stale and must be recomputed.
    """
    state_id:             str                    # UUID4
    org_id:               str
    period:               str
    version:              int                    # Monotonically increasing per org
    previous_version_id:  Optional[str]          # UUID4 or None for first version
    input_hash:           str                    # SHA-256(org_id + period + df_hash)
    status:               str                    # "Provisional" | "Substantive" | "No data"
    carbon:               CarbonInventory
    esg:                  ESGScore
    data_quality:         DataQualityScore
    confidence:           ConfidenceScore
    computed_at:          str                    # ISO 8601
    computation_time_ms:  int                    # Performance tracking


def make_empty_computed_state(org_id: str, period: str) -> ComputedState:
    """
    Return a 'No data' ComputedState for a freshly configured organisation.
    Used as the initial state before any dataset is uploaded.
    """
    import datetime, uuid
    from models.carbon import make_zero_inventory
    from models.esg import make_provisional_esg, ConfidenceScore
    from models.data_quality import make_no_data_quality
    from config.constants import STATE_STATUS_NO_DATA

    now = datetime.datetime.now().isoformat(timespec="seconds")
    carbon = make_zero_inventory(org_id, period, "")
    esg    = make_provisional_esg(org_id)
    dq     = make_no_data_quality()

    confidence = ConfidenceScore(
        esg_confidence     = esg["confidence_score"],
        esg_is_provisional = esg["is_provisional"],
        dq_confidence      = dq["confidence_score"],
        dq_is_provisional  = dq["is_provisional"],
        interpretation     = "No data — upload a dataset to begin.",
    )

    return ComputedState(
        state_id            = str(uuid.uuid4()),
        org_id              = org_id,
        period              = period,
        version             = 0,
        previous_version_id = None,
        input_hash          = "",
        status              = STATE_STATUS_NO_DATA,
        carbon              = carbon,
        esg                 = esg,
        data_quality        = dq,
        confidence          = confidence,
        computed_at         = now,
        computation_time_ms = 0,
    )
