def back() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "назад к темам",
                        "payload": "user:capabilities",
                    }
                ]
            ],
        },
    }
