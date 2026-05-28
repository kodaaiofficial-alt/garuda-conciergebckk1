# main.py
# Garuda Concierge Premium ModMail Bot + Logs
# Prefix: ?

import os
import json
import discord
from discord.ext import commands, tasks
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


# ---------------- ROTATING STATUS ----------------
STATUSES = [
    "Passenger Inquiries",
    "Garuda Operations",
    "New Tickets",
    "Cabin Services",
    "Have inquiries? Ananya is available to assist, 24/7",
]
status_index = 0

@tasks.loop(seconds=30)
async def rotate_status():
    global status_index
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=STATUSES[status_index],
        ),
    )
    status_index = (status_index + 1) % len(STATUSES)


# ---------------- READY ----------------
@bot.event
async def on_ready():
    rotate_status.start()
    print(f"{bot.user} is online. Rotating status started.")


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
            await ctx.channel.send(embed=embed)

            # LOG
            log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="💬 Staff Reply",
                    description=f"Staff: {ctx.author.mention}\nChannel: {ctx.channel.mention}\nMessage: {msg}",
                    color=COLOR,
                )
                await log_channel.send(embed=log_embed)




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
            await ctx.channel.send(embed=embed)

            # LOG
            log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🕶️ Anonymous Reply",
                    description=f"Channel: {ctx.channel.mention}\nMessage: {msg}",
                    color=COLOR,
                )
                await log_channel.send(embed=log_embed)


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


# ---------------- REOPEN ----------------
@bot.command()
async def reopen(ctx, user_id: int):
    staff_member = ctx.guild.get_member(ctx.author.id)
    if not staff_member or not any(r.id == STAFF_ROLE_ID for r in staff_member.roles):
        await ctx.send("You do not have permission to use this command.", delete_after=5)
        return

    if user_id in tickets:
        await ctx.send("That user already has an open ticket.", delete_after=5)
        return

    user = await bot.fetch_user(user_id)
    if not user:
        await ctx.send("Could not find that user.", delete_after=5)
        return

    guild = ctx.guild
    category = guild.get_channel(CATEGORY_ID)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name}", category=category
    )

    tickets[user_id] = channel.id
    save_tickets()

    embed = discord.Embed(
        title="Ticket Reopened",
        description=f"Ticket reopened for: {user.mention}\nReopened by: {ctx.author.mention}",
        color=COLOR,
    )
    embed.set_footer(text=f"User ID: {user_id}")
    await channel.send(f"<@&{STAFF_ROLE_ID}>", embed=embed)

    # Notify user via DM
    try:
        dm_embed = discord.Embed(
            title="Ticket Reopened",
            description="Your Garuda Concierge support ticket has been reopened. A staff member will be with you shortly.",
            color=COLOR,
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    # LOG
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(
            title="🔓 Ticket Reopened",
            description=f"User: {user.mention}\nReopened By: {ctx.author.mention}\nChannel: {channel.mention}",
            color=COLOR,
        )
        await log_channel.send(embed=log_embed)

    await ctx.send(f"Ticket reopened for {user.mention} in {channel.mention}.", delete_after=10)


# ---------------- OPEN FOR ----------------
@bot.command()
async def openfor(ctx, user_id: int):
    staff_member = ctx.guild.get_member(ctx.author.id)
    if not staff_member or not any(r.id == STAFF_ROLE_ID for r in staff_member.roles):
        await ctx.send("You do not have permission to use this command.", delete_after=5)
        return

    if user_id in tickets:
        await ctx.send("That user already has an open ticket.", delete_after=5)
        return

    user = await bot.fetch_user(user_id)
    if not user:
        await ctx.send("Could not find that user.", delete_after=5)
        return

    guild = ctx.guild
    category = guild.get_channel(CATEGORY_ID)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name}", category=category
    )

    tickets[user_id] = channel.id
    save_tickets()

    embed = discord.Embed(
        title="Staff-Initiated Ticket",
        description=f"Ticket opened for: {user.mention}\nOpened by: {ctx.author.mention}",
        color=COLOR,
    )
    embed.set_footer(text=f"User ID: {user_id}")
    await channel.send(f"<@&{STAFF_ROLE_ID}>", embed=embed)

    # Notify user via DM
    try:
        dm_embed = discord.Embed(
            title="Garuda Concierge — Ticket Opened",
            description="A support ticket has been opened for you by a Garuda Concierge staff member. You will receive a reply shortly.",
            color=COLOR,
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    # LOG
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(
            title="📋 Staff-Initiated Ticket",
            description=f"User: {user.mention}\nOpened By: {ctx.author.mention}\nChannel: {channel.mention}",
            color=COLOR,
        )
        await log_channel.send(embed=log_embed)

    await ctx.send(f"Ticket opened for {user.mention} in {channel.mention}.", delete_after=10)


# ---------------- EDIT ----------------
@bot.command()
async def edit(ctx, message_id: int, *, new_text):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("This command can only be used inside a ticket channel.", delete_after=5)
        return

    try:
        target_msg = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("Message not found in this channel.", delete_after=5)
        return

    # The message must be from the bot (all reply/replyan messages are sent by the bot)
    if target_msg.author.id != bot.user.id:
        await ctx.send("That message was not sent by the bot.", delete_after=5)
        return

    # Must have at least one embed to edit
    if not target_msg.embeds:
        await ctx.send("That message has no embed to edit.", delete_after=5)
        return

    original_embed = target_msg.embeds[0]

    # Only allow staff to edit messages whose footer matches their own name/rank,
    # or anonymous replies (footer: "Ananya Mehta • Support Agent")
    member = ctx.guild.get_member(ctx.author.id)
    if not member or not any(r.id == STAFF_ROLE_ID for r in member.roles):
        await ctx.send("You do not have permission to use this command.", delete_after=5)
        return

    staff_name = member.display_name
    rank = member.top_role.name
    footer_text = original_embed.footer.text if original_embed.footer else ""

    # Allow edit if footer matches this staff member OR it's an anonymous reply
    if footer_text != f"{staff_name} • {rank}" and footer_text != "Ananya Mehta • Support Agent":
        await ctx.send("You can only edit your own replies.", delete_after=5)
        return

    new_embed = discord.Embed(
        title=original_embed.title,
        description=new_text,
        color=original_embed.color,
    )
    new_embed.set_footer(text=footer_text)

    await target_msg.edit(embed=new_embed)

    # Also update the user's DM if possible — find the user for this ticket
    user_id = None
    for uid, cid in tickets.items():
        if cid == ctx.channel.id:
            user_id = uid
            break

    # LOG
    log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(
            title="✏️ Reply Edited",
            description=f"Staff: {ctx.author.mention}\nChannel: {ctx.channel.mention}\nNew Message: {new_text}",
            color=COLOR,
        )
        await log_channel.send(embed=log_embed)

    await ctx.message.delete()


bot.run(TOKEN)
