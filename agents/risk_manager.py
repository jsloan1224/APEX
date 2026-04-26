class KillSwitch:
    def __init__(self, config: dict):
        risk = config['risk']
        self.max_daily_loss_usd      = risk['max_daily_loss_usd']
        self.max_drawdown_usd        = risk['max_drawdown_usd']
        self.max_consecutive_losses  = risk['max_consecutive_losses']
        self.cool_off_minutes        = risk['cool_off_minutes']
        self.news_window_minutes     = risk['news_window_minutes']
        self.max_open_positions      = risk['max_open_positions']
        self.triggered               = False
        self.trigger_reason          = None

    def check(self, daily_pnl: float, drawdown: float,
              open_positions: int, consecutive_losses: int) -> bool:
        # Stub — full logic Phase 6
        return False

    def trigger(self, reason: str):
        self.triggered = True
        self.trigger_reason = reason

    def reset(self):
        self.triggered = False
        self.trigger_reason = None
