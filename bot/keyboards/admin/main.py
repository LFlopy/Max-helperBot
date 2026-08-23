def admin_main_keyboard() -> dict:
    return {
        "type": "inline-keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Пользователи",
                        "payload": "admin:users",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Подписки",
                        "payload": "admin:subscriptions",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Рассылки",
                        "payload": "admin:broadcasts",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Статистика",
                        "payload": "admin:statistics",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Настройки",
                        "payload": "admin:settings",
                    }
                ],
            ]
        },
    }
