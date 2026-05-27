# main.py
# Garuda Concierge Premium ModMail Bot + Logs
# Prefix: ?

import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

# ================= CONFIG =================
GUILD_ID = 1500768649638580334
CATEGORY_ID = 1502957109560606871
STAFF_ROLE_ID = 1500774142423863337
LOG_CHANNEL_ID = 1506965821883154574
COLOR = 0x083B7C
# =========================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

TICKETS_FILE = "tickets.json"

def load_tickets():
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "r") as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_tickets():
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f)

tickets = load_tickets()


# ---------------- READY ----------------
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Have inquiries? Ananya is available to assist, 24/7",
        ),
    )
    print(f"{bot.user} is online and presence set: Ananya is available to assist, 24/7.")


# ---------------- BUTTON VIEW ----------------
class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Please choose a reason below:", view=ReasonView(), ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Ticket creation cancelled.", ephemeral=True
        )


# ---------------- DROPDOWN ----------------
class ReasonSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Inquiry"),
            discord.SelectOption(label="Career / Hiring"),
            discord.SelectOption(label="Complaint"),
            discord.SelectOption(label="Booking Support"),
            discord.SelectOption(label="Other"),
        ]

        super().__init__(
            placeholder="Choose your ticket reason",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user

        if user.id in tickets:
            await interaction.response.send_message(
                "You already have an open ticket.", ephemeral=True
            )
            return

        guild = bot.get_guild(GUILD_ID)
        category = guild.get_channel(CATEGORY_ID)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}", category=category
        )

        tickets[user.id] = channel.id
        save_tickets()

        embed = discord.Embed(
            title="New Garuda Concierge Ticket",
            description=f"Opened by: {user.mention}\nReason: **{self.values[0]}**",
            color=COLOR,
        )
        embed.set_footer(text=f"User ID: {user.id}")

        await channel.send(f"<@&{STAFF_ROLE_ID}>", embed=embed)

        # LOG OPEN
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📩 Ticket Opened",
                description=f"User: {user.mention}\nReason: {self.values[0]}\nChannel: {channel.mention}",
                color=COLOR,
            )
            await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            "Your support ticket has been created.", ephemeral=True
        )


class ReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ReasonSelect())


# ---------------- USER DM ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.author.id not in tickets:
            embed = discord.Embed(
                title="Garuda Concierge",
                description="Would you like to continue creating a support ticket?",
                color=COLOR,
            )
            await message.channel.send(embed=embed, view=StartView())
            return

        channel = bot.get_channel(tickets[message.author.id])

        if channel:
            embed = discord.Embed(
                title="Customer Message", description=message.content, color=COLOR
            )
            embed.set_footer(text=str(message.author))
            await channel.send(embed=embed)

    await bot.process_commands(message)


# ---------------- REPLY ----------------
@bot.command()
async def reply(ctx, *, msg):
    if ctx.channel.name.startswith("ticket-"):
        user_id = None
        for uid, cid in tickets.items():
            if cid == ctx.channel.id:
                user_id = uid
                break

        if user_id:
            user = await bot.fetch_user(user_id)

            member = ctx.guild.get_member(ctx.author.id)
            staff_name = member.display_name
            rank = member.top_role.name

            embed = discord.Embed(
                title="Garuda Concierge Response", description=msg, color=COLOR
            )
            embed.set_footer(text=f"{staff_name} • {rank}")

            await user.send(embed=embed)

            # LOG
            log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="💬 Staff Reply",
                    description=f"Staff: {ctx.author.mention}\nChannel: {ctx.channel.mention}\nMessage: {msg}",
                    color=COLOR,
                )
                await log_channel.send(embed=log_embed)

            await ctx.message.add_reaction("✅")


# ---------------- ANON REPLY ----------------
@bot.command()
async def replyan(ctx, *, msg):
    if ctx.channel.name.startswith("ticket-"):
        user_id = None
        for uid, cid in tickets.items():
            if cid == ctx.channel.id:
                user_id = uid
                break

        if user_id:
            user = await bot.fetch_user(user_id)

            embed = discord.Embed(
                title="Garuda Concierge Reply", description=msg, color=COLOR
            )
            embed.set_footer(text="Ananya Mehta • Support Agent")

            await user.send(embed=embed)

            # LOG
            log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🕶️ Anonymous Reply",
                    description=f"Channel: {ctx.channel.mention}\nMessage: {msg}",
                    color=COLOR,
                )
                await log_channel.send(embed=log_embed)

            await ctx.message.add_reaction("✅")


# ---------------- CLOSE ----------------
@bot.command()
async def close(ctx):
    if ctx.channel.name.startswith("ticket-"):
        user_id = None
        for uid, cid in tickets.items():
            if cid == ctx.channel.id:
                user_id = uid
                break

        if user_id:
            user = await bot.fetch_user(user_id)

            embed = discord.Embed(
                title="Ticket Closed",
                description="Your Garuda Concierge request has been resolved.",
                color=COLOR,
            )

            await user.send(embed=embed)
            del tickets[user_id]
            save_tickets()

        # LOG
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"Closed By: {ctx.author.mention}\nChannel: {ctx.channel.name}",
                color=COLOR,
            )
            await log_channel.send(embed=log_embed)

        await ctx.channel.delete()


bot.run(TOKEN)
