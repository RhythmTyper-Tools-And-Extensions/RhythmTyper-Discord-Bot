import discord
from discord.ext import bridge, commands
from discord import SelectOption
from discord.ui import Select

from utils.api import fetch_api
from utils.logger import debug


class MapView(discord.ui.View):
    def __init__(self, maps):
        super().__init__()
        self.maps = maps

        options = [
            SelectOption(
                label=map_data['songName'][:100],
                value=map_data['id'],
                description=f"Mapper: {map_data['mapper']}, ID: {map_data['id']}"[:100]
            )
            for map_data in maps
        ]

        select = Select(
            placeholder="Choose a map",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        selected_id = interaction.data['values'][0]
        selected_map = next((m for m in self.maps if m['id'] == selected_id), None)
        if selected_map:
            await interaction.response.edit_message(
                content=f"You selected: {selected_map['songName']} by {selected_map['mapper']}\nhttps://rhythmtyper.net/beatmap/{selected_map['id']}"
            )

class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(name="map", aliases=["m"])
    async def map(
            self,
            ctx,
            keywords: str,
            status: str = None
    ):
        if status is None:
            status = "all"

        message = await ctx.respond("Fetching map...")

        maps = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/getBeatmaps?limit=50&status={status}&sortBy=relevance&showExplicit=true&language=all&search={keywords}")
        debug(maps)

        if not maps["beatmaps"]:
            await message.edit(f"No maps found with those keywords : {keywords}")
            return

        beatmaps = maps["beatmaps"]
        await message.edit(
            f"https://rhythmtyper.net/beatmap/{beatmaps[0]['id']}",
            view=MapView(beatmaps)
        )

def setup(bot):
    bot.add_cog(Map(bot))