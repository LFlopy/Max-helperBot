from services.admin import AdminTariff, AdminUserCard, AdminUserPage


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


def subscription_management_keyboard(user_id: int, return_page: int) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Выдать / продлить тариф",
                        "payload": (
                            f"admin:user:{user_id}:grant:page:{return_page}"
                        ),
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Отменить подписку",
                        "payload": (
                            f"admin:user:{user_id}:cancel:page:{return_page}"
                        ),
                    }
                ],
                [
                    {
                        "type": "callback",
                        "text": "Назад",
                        "payload": f"admin:user:{user_id}:page:{return_page}",
                    }
                ],
            ]
        },
    }


def tariff_selection_keyboard(
    user_id: int,
    tariffs: tuple[AdminTariff, ...],
    return_page: int,
) -> dict:
    buttons = [
        [
            {
                "type": "callback",
                "text": tariff.name,
                "payload": (
                    f"admin:user:{user_id}:grant:tariff:{tariff.id}:page:"
                    f"{return_page}"
                ),
            }
        ]
        for tariff in tariffs
    ]
    buttons.append(
        [
            {
                "type": "callback",
                "text": "Назад",
                "payload": (
                    f"admin:user:{user_id}:subscriptions:page:{return_page}"
                ),
            }
        ]
    )
    return {"type": "inline_keyboard", "payload": {"buttons": buttons}}


def grant_confirmation_keyboard(
    user_id: int,
    tariff_id: int,
    return_page: int,
) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Подтвердить",
                        "payload": (
                            f"admin:user:{user_id}:grant:tariff:{tariff_id}:"
                            f"confirm:page:{return_page}"
                        ),
                    },
                    {
                        "type": "callback",
                        "text": "Отмена",
                        "payload": (
                            f"admin:user:{user_id}:subscriptions:page:"
                            f"{return_page}"
                        ),
                    },
                ]
            ]
        },
    }


def cancel_confirmation_keyboard(user_id: int, return_page: int) -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": "Подтвердить",
                        "payload": (
                            f"admin:user:{user_id}:cancel:confirm:page:"
                            f"{return_page}"
                        ),
                    },
                    {
                        "type": "callback",
                        "text": "Отмена",
                        "payload": (
                            f"admin:user:{user_id}:subscriptions:page:"
                            f"{return_page}"
                        ),
                    },
                ]
            ]
        },
    }
