from services.admin import AdminUserCard, AdminUserPage


def users_keyboard(page: AdminUserPage) -> dict:
    buttons = [
        [
            {
                "type": "callback",
                "text": item.first_name or f"Пользователь {item.id}",
                "payload": f"admin:user:{item.id}:page:{page.page}",
            }
        ]
        for item in page.items
    ]

    navigation: list[dict[str, str]] = []
    if page.page > 1:
        navigation.append(
            {
                "type": "callback",
                "text": "<",
                "payload": f"admin:users:page:{page.page - 1}",
            }
        )
    navigation.append(
        {
            "type": "callback",
            "text": f"{page.page}/{page.page_count}",
            "payload": f"admin:users:page:{page.page}",
        }
    )
    if page.page < page.page_count:
        navigation.append(
            {
                "type": "callback",
                "text": ">",
                "payload": f"admin:users:page:{page.page + 1}",
            }
        )
    buttons.append(navigation)
    buttons.append(
        [
            {
                "type": "callback",
                "text": "Назад",
                "payload": "admin:main",
            }
        ]
    )
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": buttons},
    }


def user_card_keyboard(card: AdminUserCard, return_page: int) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Управление подпиской",
                        "payload": (
                            f"admin:user:{card.id}:subscriptions:page:"
                            f"{return_page}"
                        ),
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": f"admin:users:page:{return_page}",
                    }
                ],
            ]
        },
    }
