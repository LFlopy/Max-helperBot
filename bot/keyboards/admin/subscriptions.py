from services.admin import ActiveSubscriptionPage


def subscriptions_overview_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Активные подписки",
                        "payload": "admin:subscriptions:active",
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Тарифы",
                        "payload": "admin:subscriptions:tariffs",
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


def active_subscriptions_keyboard(page: ActiveSubscriptionPage) -> dict:
    navigation: list[dict[str, str]] = []
    if page.page > 1:
        navigation.append(
            {
                "type": "callback",
                "text": "<",
                "payload": f"admin:subscriptions:active:page:{page.page - 1}",
            }
        )
    navigation.append(
        {
            "type": "callback",
            "text": f"{page.page}/{page.page_count}",
            "payload": f"admin:subscriptions:active:page:{page.page}",
        }
    )
    if page.page < page.page_count:
        navigation.append(
            {
                "type": "callback",
                "text": ">",
                "payload": f"admin:subscriptions:active:page:{page.page + 1}",
            }
        )
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                navigation,
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": "admin:subscriptions",
                    }
                ],
            ]
        },
    }


def tariffs_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": "admin:subscriptions",
                    }
                ]
            ]
        },
    }
