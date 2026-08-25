def capabilities_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Питание",
                        "payload": "capabilities:food",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Вес",
                        "payload": "capabilities:weight",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Сон",
                        "payload": "capabilities:sleep",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Стресс",
                        "payload": "capabilities:stress",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Анализы",
                        "payload": "capabilities:analyses",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Гормоны и цикл",
                        "payload": "capabilities:hormones",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Другой вопрос",
                        "payload": "capabilities:another",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Главное меню",
                        "payload": "user:main",
                    }
                ],
            ]
        },
    }
