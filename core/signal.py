from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SignalCandidate:
    # Core identification
    signal_id:                    str
    created_at:                   datetime    # UTC
    traded_instrument:            str          # ES | NQ | YM
    direction:                    str          # bullish | bearish
    model_name:                   str

    # Bias chain — three timeframes only
    bias_timeframes:              list         # e.g. [240, 60, 15]
    bias_per_timeframe:           dict         # e.g. {240: 'bullish', 60: 'bullish', 15: 'bullish'}
    bias_alignment:               bool         # True only if ALL agree
    bias_alignment_checked_at:    datetime    # UTC

    # FVG context
    fvg_timeframe:                int          # which TF the entry FVG came from (typically 1, 3, or 5)
    fvg_high:                     float        = 0.0
    fvg_low:                      float        = 0.0
    fvg_midpoint:                 float        = 0.0
    fvg_size_ticks:               int          = 0
    fvg_first_touch:              bool         = False

    # Key ICT levels at time of signal
    prev_day_high:                float        = 0.0
    prev_day_low:                 float        = 0.0
    daily_high:                   float        = 0.0
    daily_low:                    float        = 0.0
    midnight_open:                float        = 0.0
    ny_open:                      float        = 0.0
    weekly_open:                  float        = 0.0

    # Liquidity sweep details
    liquidity_level_swept:        float        = 0.0
    sweep_direction:              str          = ''     # 'BSL' | 'SSL'
    sweep_time:                   Optional[datetime] = None  # UTC

    # MSS
    mss_confirmed:                bool         = False
    mss_bar_index:                int          = -1

    # ICT confirmations
    liquidity_swept:              bool         = False
    fvg_identified:               bool         = False

    # Entry parameters (from instrument_params for traded_instrument)
    entry_price:                  float        = 0.0
    stop_loss_price:              float        = 0.0
    take_profit_price:            float        = 0.0
    stop_ticks:                   int          = 0
    target_ticks:                 int          = 0
    contracts:                    int          = 1

    # Session context
    session:                      str          = ''     # LONDON | NY_AM | NY_PM
    kill_zone_active:             bool         = False

    # SMT context (sister instruments, set by smt_agent at Step 3.5)
    sister_1_symbol:              str          = ''
    sister_1_bias:                str          = ''     # bullish | bearish | neutral
    sister_1_smt_divergence:      bool         = False
    sister_2_symbol:              str          = ''
    sister_2_bias:                str          = ''
    sister_2_smt_divergence:      bool         = False

    # AI gate result (set by validation_gate at Step 7)
    ai_gate_displacement_score:   Optional[int]   = None
    ai_gate_sweep_score:          Optional[int]   = None
    ai_gate_environment_score:    Optional[int]   = None
    ai_gate_average:              Optional[float] = None
    ai_gate_result:               str          = ''     # APPROVE | REJECT | TIMEOUT | ERROR
    ai_gate_reason:               str          = ''
    ai_gate_latency_ms:           Optional[int]   = None

    # Outcome
    discard_reason:               str          = ''     # populated if rejected at any step
    executed:                     bool         = False
    order_id:                     Optional[str]   = None
