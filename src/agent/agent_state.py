class AgentState:
    VALID_STATES = (
        "IDLE",
        "ANALYZING",
        "TRADING",
        "STOPPED"
    )

    def __init__(self):
        self.state = "IDLE"

    def get_state(self):
        return self.state

    def set_state(self, state):
        if state not in self.VALID_STATES:
            raise ValueError(f"Invalid agent state: {state}")

        if self.state == "STOPPED":
            return

        self.state = state

    def stop(self):
        self.state = "STOPPED"

    def is_stopped(self):
        return self.state == "STOPPED"
        