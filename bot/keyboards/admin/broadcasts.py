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
                        "text": "Назад",
                        "payload": "admin:main",
                    }
                ],
            ]
        },
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
