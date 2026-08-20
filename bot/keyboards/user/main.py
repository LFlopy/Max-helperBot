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
                ]
            ]
        },
    }
