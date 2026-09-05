def main_menu() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Что я умею",
                        "payload": "user:capabilities",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Профиль",
                        "payload": "user:profile",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Тарифы",
                        "payload": "user:tariffs",
                    }
                ],
            ]
        },
    }
