from bot.handlers.draw import router as draw_router
from bot.handlers.echo import router as echo_router

# draw_router first so /draw doesn't get caught by catch-all echo
routers = [draw_router, echo_router]
