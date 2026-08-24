def broadcasts_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Для всех",
                        "payload": "broadcasts:to everyone",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "определённая группа",
                        "payload": "broadcasts:some one",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Догревающая рассылка",
                        "payload": "broadcasts:heating up",
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
