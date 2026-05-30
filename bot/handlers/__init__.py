from bot.handlers.draw import router as draw_router
from bot.handlers.echo import router as echo_router
from bot.handlers.subscription import router as subscription_router

routers = [draw_router, subscription_router, echo_router]
