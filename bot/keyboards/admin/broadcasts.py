def broadcasts_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Всем пользователям",
                        "payload": "admin:broadcasts:all",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Последние рассылки",
                        "payload": "admin:broadcasts:status",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": "admin:main",
                    }
                ],
            ]
        },
    }


def broadcast_list_keyboard(broadcast_ids: tuple[int, ...]) -> dict:
    buttons = [
        [
            {
                "type": "callback",
                "text": f"Рассылка #{broadcast_id}",
                "payload": f"admin:broadcast:{broadcast_id}",
            }
        ]
        for broadcast_id in broadcast_ids
    ]
    buttons.append(
        [
            {
                "type": "callback",
                "text": "Назад",
                "payload": "admin:broadcasts",
            }
        ]
    )
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}


def broadcast_status_keyboard(
    broadcast_id: int | None = None,
    can_cancel: bool = False,
) -> dict:
    buttons: list[list[dict[str, str]]] = []
    if broadcast_id is not None and can_cancel:
        buttons.append(
            [
                {
                    "type": "callback",
                    "text": "Отменить рассылку",
                    "payload": f"admin:broadcast:{broadcast_id}:cancel",
                }
            ]
        )
    buttons.append(
        [
            {
                "type": "callback",
                "text": "Назад",
                "payload": "admin:broadcasts:status",
            }
        ]
    )
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": buttons},
    }


def broadcast_preview_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Отправить",
                        "payload": "admin:broadcasts:confirm",
                    },
                    {
                        "type": "callback",
                        "text": "Отмена",
                        "payload": "admin:broadcasts:cancel",
                    },
                ]
            ]
        },
    }


def broadcast_cancel_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Отмена",
                        "payload": "admin:broadcasts:cancel",
                    }
                ]
            ]
        },
    }
