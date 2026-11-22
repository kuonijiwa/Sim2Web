import os,sys
sys.path.append(os.environ["SIM2WEB_R6_TRAME_LIB"])
from aiohttp import web
async def echo(request):
    sock=web.WebSocketResponse(compress=False)
    await sock.prepare(request)
    async for msg in sock:
        if msg.type==web.WSMsgType.BINARY:
            await sock.send_bytes(msg.data)
    return sock
app=web.Application()
app.router.add_get("/echo",echo)
app.router.add_get("/",lambda req:web.Response(text="<title>WS probe</title>",content_type="text/html"))
web.run_app(app,host="127.0.0.1",port=18773)
