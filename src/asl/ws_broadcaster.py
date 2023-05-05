import asyncio
import websockets

class WebsocketBroadcaster:
	
	def __init__(self):
		self.waiter = asyncio.Future()

	def set_waiter(self, Future):
		self.waiter = Future

	def publish(self, value):
		waiter, self.waiter = self.waiter, asyncio.Future()
		waiter.set_result((value, self.waiter))

	async def subscribe(self):
		waiter = self.waiter
		while True:
			value, waiter = await waiter
			yield value

	__aiter__ = subscribe


