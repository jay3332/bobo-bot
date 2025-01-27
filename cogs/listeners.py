import discord
from discord.ext import commands

from core import Cog

class Listeners(Cog):
    @Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if messages := await self.bot.delete_message_manager.get_messages(payload.message_id):
            try:
                await self.bot.http.delete_messages(payload.channel_id, messages) # Well if someone were to edit their message 100 times then uhh idk.
            except (discord.Forbidden, discord.NotFound):
                for m in messages:
                    await self.bot.http.delete_message(payload.channel_id, m)
            
            await self.bot.delete_message_manager.delete_messages(payload.message_id)

setup = Listeners.setup
