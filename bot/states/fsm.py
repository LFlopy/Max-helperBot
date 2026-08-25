class FSM:
    def __init__(self) -> None:
        self.states: dict[int, str] = {}

    async def set_state(
        self,
        user_id: int,
        state: str,
    ) -> None:
        self.states[user_id] = state

    async def get_state(
        self,
        user_id: int,
    ) -> str | None:
        return self.states.get(user_id)

    async def clear(
        self,
        user_id: int,
    ) -> None:
        self.states.pop(
            user_id,
            None,
        )


fsm = FSM()
