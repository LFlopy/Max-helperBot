def profile_keyboard(can_activate_trial: bool) -> dict:
    buttons: list[list[dict[str, str]]] = [
        [
            {
                "type": "callback",
                "text": "Тарифы",
                "payload": "user:tariffs",
            }
        ]
    ]
    if can_activate_trial:
        buttons.append(
            [
                {
                    "type": "callback",
                    "text": "Попробовать бесплатно",
                    "payload": "user:trial:activate",
                }
            ]
        )
    buttons.append(
        [
            {
                "type": "callback",
                "text": "Главная",
                "payload": "user:main",
            }
        ]
    )
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}
