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


def tariffs_keyboard(tariffs: tuple[tuple[int, str], ...]) -> dict:
    buttons = [
        [
            {
                "type": "callback",
                "text": name,
                "payload": f"user:tariff:{tariff_id}",
            }
        ]
        for tariff_id, name in tariffs
    ]
    buttons.extend(
        [
            [
                {
                    "type": "callback",
                    "text": "Назад",
                    "payload": "user:profile",
                }
            ],
            [
                {
                    "type": "callback",
                    "text": "Главная",
                    "payload": "user:main",
                }
            ],
        ]
    )
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}


def tariff_details_keyboard(tariff_id: int) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Купить",
                        "payload": f"user:tariff:{tariff_id}:buy",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": "user:tariffs",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Главная",
                        "payload": "user:main",
                    }
                ],
            ]
        },
    }


def checkout_keyboard(payment_id: int, checkout_url: str) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "link",
                        "text": "Перейти к тестовой оплате",
                        "url": checkout_url,
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Проверить статус",
                        "payload": f"payment:status:{payment_id}",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Назад к тарифам",
                        "payload": "user:tariffs",
                    }
                ],
            ]
        },
    }
