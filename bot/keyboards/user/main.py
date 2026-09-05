def start_keyboard() -> dict:
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
                        "text": "Главное меню",
                        "payload": "user:main",
                    }
                ],
            ]
        },
    }
