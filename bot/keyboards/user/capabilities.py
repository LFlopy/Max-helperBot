def capabilities_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Питание",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Вес",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Сон",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Стресс",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Анализы",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Гормоны и цикл",
                        "payload": "nothing for now",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Другой вопрос",
                        "payload": "nothing for now",
                    }
                ],
            ]
        },
    }
