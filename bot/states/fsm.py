class FSM:
    def __init__(self) -> None:
        self.states: dict[int, str] = {}
        self.data: dict[int, dict[str, object]] = {}

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

    async def set_data(
        self,
        user_id: int,
        data: dict[str, object],
    ) -> None:
        self.data[user_id] = data

    async def get_data(self, user_id: int) -> dict[str, object]:
        return self.data.get(user_id, {}).copy()

    async def clear(
        self,
        user_id: int,
    ) -> None:
        self.states.pop(
            user_id,
            None,
        )
        self.data.pop(user_id, None)


fsm = FSM()
