from bot.handlers.admin.broadcasts import router as admin_broadcasts_router
from bot.handlers.admin.main import router as admin_main_router
from bot.handlers.admin.statistics import router as admin_statistics_router
from bot.handlers.admin.subscriptions import router as admin_subscriptions_router
from bot.handlers.admin.users import router as admin_users_router
from bot.handlers.user.capabilities import router as user_capabilities_router
from bot.handlers.user.consultation import router as user_consultation_router
from bot.handlers.user.main_menu import router as user_main_menu_router
from bot.handlers.user.start import router as user_start_router
from bot.handlers.user.subscriptions import router as user_subscriptions_router
from bot.router import Router


ROUTERS: tuple[Router, ...] = (
    user_start_router,
    user_capabilities_router,
    user_consultation_router,
    admin_main_router,
    admin_statistics_router,
    admin_subscriptions_router,
    admin_users_router,
    admin_broadcasts_router,
    user_main_menu_router,
    user_subscriptions_router,
)
