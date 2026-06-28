import discord
from discord.ext import commands
import json
import os
import random
import re

# =========================
# RYAN AIR CONCIERGE CONFIG
# =========================

TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
PREFIX = "-"

# Replace these with your real Discord IDs
SUPPORT_ROLE_ID = 123456789012345678
TICKET_CATEGORY_ID = 123456789012345678

# Put 0 if you want "hi" to trigger everywhere
SUPPORT_TRIGGER_CHANNEL_ID = 0

SNIPPETS_FILE = "snippets.json"
BRAND_COLOR = 0x122E63

# =========================
# RYAN AIR EMOJIS
# =========================

RYR_LOGO = "<:RYR_Logo:1520474699602198703>"
RYR_TAIL = "<:RYR_Tail:1520472457427947762>"
RYR_BLUE_ARROW = "<:RYR_BlueArrow:1520469707797561557>"
RYR_PLANE = "<:RYR_Plane:1520469683390779583>"
RYR_PARTNERSHIP = "<:RYR_Partnership:1520469654865449101>"
RYR_NETWORK = "<:RYR_Network:1520469628508307610>"
RYR_MAINTENANCE = "<:RYR_Maintenance:1520469600876232704>"
RYR_FLAG = "<:RYR_Flag:1520469508735635597>"
RYR_YELLOW_ARROW = "<:RYR_YellowArrow:1520469233933226035>"
RYR_DECENT = "<:RYR_Decent:1520469200982904882>"
RYR_CUTLERY = "<:RYR_Cutlery:1520469179067535421>"
RYR_CHECKLIST = "<:RYR_Checklist:1520469158498795616>"
RYR_BOARDINGPASS = "<:RYR_BoardingPass:1520469122536706058>"
RYR_ASCENT = "<:RYR_Ascent:1520469095357874196>"
RYR_ANALYTICS = "<:RYR_Analytics:1520469075736793220>"
RYR_ACADEMY = "<:RYR_Academy:1520469058087030924>"

LOGO_URL = "https://cdn.discordapp.com/emojis/1520474699602198703.png"

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# =========================
# HELPER FUNCTIONS
# =========================

def load_snippets():
    if not os.path.exists(SNIPPETS_FILE):
        return {}

    try:
        with open(SNIPPETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_snippets(data):
    with open(SNIPPETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def clean_name(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    return name[:20]


async def safe_delete(message):
    try:
        await message.delete()
    except:
        pass


def has_support_perms(member):
    if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
        return True

    return any(role.id == SUPPORT_ROLE_ID for role in member.roles)


def is_support():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        return has_support_perms(ctx.author)

    return commands.check(predicate)


def make_confirm_embed():
    embed = discord.Embed(
        title=f"{RYR_LOGO} Confirm thread creation",
        description=(
            f"{RYR_FLAG} **Dia dhuit,** thank you for contacting **Ryan Air Concierge**.\n\n"
            f"> {RYR_BLUE_ARROW} We appreciate your interest in consulting with us today, "
            f"but are you sure you want to create a ticket? Please select below."
        ),
        color=BRAND_COLOR
    )

    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="Ryan Air Concierge")
    return embed


def make_opening_embed(user):
    embed = discord.Embed(
        title=f"{RYR_PLANE} Ryan Air Concierge",
        description=(
            f"{RYR_DECENT} providing assistance of high quality\n\n"
            f"**Commendations,** thank you for contacting the **Ryan Air Concierge**.\n\n"
            f"> {RYR_BLUE_ARROW} An agent will be **assigned** to you shortly, and we request your "
            f"**patience** while an available one is located.\n\n"
            f"Whilst assistance is found, please inform us with what support we may assist you with, "
            f"by selecting an **inquiry** from the following selections that corresponds to your inquiry today.\n\n"
            f"{RYR_PARTNERSHIP} **[1] Public Relations Inquiry**\n"
            f"{RYR_ACADEMY} **[2] Human Resources Inquiry**\n"
            f"{RYR_PLANE} **[3] Operations Inquiry**\n"
            f"{RYR_CHECKLIST} **[4] General Concerns**\n"
            f"{RYR_ANALYTICS} **[5] Rank Request**\n"
            f"{RYR_NETWORK} **[6] Auxiliary Inquiry**\n\n"
            f"{RYR_BLUE_ARROW} Please remain **patient** as we locate an agent to **assist you**, "
            f"and feel free to provide us with other relevant information regarding your claim today."
        ),
        color=BRAND_COLOR
    )

    embed.set_author(name="Ryan Air Concierge", icon_url=LOGO_URL)
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=f"Ticket opened by {user}", icon_url=user.display_avatar.url)
    return embed


def find_existing_ticket(guild, user):
    topic_text = f"ryanair-ticket-user:{user.id}"

    for channel in guild.text_channels:
        if channel.topic and topic_text in channel.topic:
            return channel

    return None


# =========================
# VIEWS / BUTTONS / DROPDOWN
# =========================

class TicketPromptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        emoji=RYR_YELLOW_ARROW,
        custom_id="ryanair_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            return await interaction.response.send_message(
                "This can only be used inside a server.",
                ephemeral=True
            )

        existing = find_existing_ticket(guild, user)

        if existing:
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} You already have an open ticket: {existing.mention}",
                ephemeral=True
            )

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

        channel = await guild.create_text_channel(
            name=f"ticket-{clean_name(user.name)}",
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            topic=f"Ryan Air Concierge ticket | ryanair-ticket-user:{user.id}",
            reason="Ryan Air Concierge ticket created"
        )

        opening_embed = make_opening_embed(user)

        mention_text = f"{user.mention}"
        if support_role:
            mention_text += f" {support_role.mention}"

        await channel.send(
            content=mention_text,
            embed=opening_embed,
            view=TicketControlView()
        )

        await interaction.response.send_message(
            f"{RYR_YELLOW_ARROW} Your ticket has been created: {channel.mention}",
            ephemeral=True
        )

        try:
            await interaction.message.edit(view=None)
        except:
            pass

    @discord.ui.button(
        label="No, thanks",
        style=discord.ButtonStyle.gray,
        emoji=RYR_BLUE_ARROW,
        custom_id="ryanair_no_ticket"
    )
    async def no_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{RYR_LOGO} Ryan Air Concierge",
            description=f"{RYR_BLUE_ARROW} Alright, no ticket was created.",
            color=BRAND_COLOR
        )

        await interaction.response.edit_message(embed=embed, view=None)


class InquirySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Public Relations Inquiry",
                description="Partnerships, affiliates, relations, or media concerns.",
                emoji=RYR_PARTNERSHIP,
                value="Public Relations Inquiry"
            ),
            discord.SelectOption(
                label="Human Resources Inquiry",
                description="Staff, recruitment, rank, or department support.",
                emoji=RYR_ACADEMY,
                value="Human Resources Inquiry"
            ),
            discord.SelectOption(
                label="Operations Inquiry",
                description="Flights, operations, events, or aviation-related support.",
                emoji=RYR_PLANE,
                value="Operations Inquiry"
            ),
            discord.SelectOption(
                label="General Concerns",
                description="General server, member, or support questions.",
                emoji=RYR_CHECKLIST,
                value="General Concerns"
            ),
            discord.SelectOption(
                label="Rank Request",
                description="Request or verify a rank.",
                emoji=RYR_ANALYTICS,
                value="Rank Request"
            ),
            discord.SelectOption(
                label="Auxiliary Inquiry",
                description="Other departments or additional assistance.",
                emoji=RYR_NETWORK,
                value="Auxiliary Inquiry"
            )
        ]

        super().__init__(
            placeholder="Select your inquiry type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ryanair_inquiry_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        embed = discord.Embed(
            title=f"{RYR_CHECKLIST} Inquiry Selected",
            description=(
                f"{RYR_BLUE_ARROW} {interaction.user.mention} has selected:\n\n"
                f"**{selected}**\n\n"
                f"Please provide all relevant information below so our team can assist you."
            ),
            color=BRAND_COLOR
        )

        embed.set_footer(text="Ryan Air Concierge")
        await interaction.response.send_message(embed=embed)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(InquirySelect())

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        emoji=RYR_MAINTENANCE,
        custom_id="ryanair_close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_support_perms(interaction.user):
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} Only Ryan Air Concierge staff can close this ticket.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"{RYR_MAINTENANCE} Closing this ticket..."
        )

        await interaction.channel.delete(reason="Ryan Air Concierge ticket closed")


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    bot.add_view(TicketPromptView())
    bot.add_view(TicketControlView())

    print("==============================")
    print(f"Logged in as {bot.user}")
    print("Ryan Air Concierge is online.")
    print("==============================")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()

    # Make sure normal prefix commands still work
    if content.startswith(PREFIX):
        await bot.process_commands(message)
        return

    # Channel restriction for hi popup
    if SUPPORT_TRIGGER_CHANNEL_ID != 0 and message.channel.id != SUPPORT_TRIGGER_CHANNEL_ID:
        return

    if content in ["hi", "hello", "hey"]:
        await message.channel.send(
            embed=make_confirm_embed(),
            view=TicketPromptView()
        )

    await bot.process_commands(message)


# =========================
# PREFIX COMMANDS
# =========================

@bot.command(name="r")
@is_support()
async def reply(ctx, *, message):
    await safe_delete(ctx.message)
    await ctx.send(message)


@bot.command(name="ra")
@is_support()
async def anonymous_reply(ctx, *, message):
    await safe_delete(ctx.message)

    names = [
        "Ryan Air Concierge",
        "Concierge Agent",
        "Guest Relations Agent",
        "Support Representative",
        "Ryan Air Assistant",
        "Customer Relations"
    ]

    embed = discord.Embed(
        description=message,
        color=BRAND_COLOR
    )

    embed.set_author(name=random.choice(names), icon_url=LOGO_URL)
    embed.set_footer(text="Ryan Air Concierge")
    await ctx.send(embed=embed)


@bot.command(name="snippets")
@is_support()
async def snippets(ctx):
    data = load_snippets()

    if not data:
        return await ctx.send(f"{RYR_BLUE_ARROW} No snippets have been added yet.")

    description = ""

    for name, content in data.items():
        preview = content.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "..."

        description += f"{RYR_YELLOW_ARROW} `{name}` — {preview}\n"

    embed = discord.Embed(
        title=f"{RYR_CHECKLIST} Saved Snippets",
        description=description,
        color=BRAND_COLOR
    )

    embed.set_footer(text="Use -snippet add, -snippet edit, or -snippet delete")
    await ctx.send(embed=embed)


@bot.group(name="snippet", invoke_without_command=True)
@is_support()
async def snippet(ctx):
    embed = discord.Embed(
        title=f"{RYR_CHECKLIST} Snippet Commands",
        description=(
            f"{RYR_BLUE_ARROW} `-snippet add name content`\n"
            f"{RYR_BLUE_ARROW} `-snippet edit name content`\n"
            f"{RYR_BLUE_ARROW} `-snippet delete name`\n"
            f"{RYR_BLUE_ARROW} `-snippets`"
        ),
        color=BRAND_COLOR
    )

    await ctx.send(embed=embed)


@snippet.command(name="add")
@is_support()
async def snippet_add(ctx, name: str, *, content):
    data = load_snippets()

    if name in data:
        return await ctx.send(
            f"{RYR_BLUE_ARROW} A snippet named `{name}` already exists. Use `-snippet edit {name} ...` instead."
        )

    data[name] = content
    save_snippets(data)

    await ctx.send(f"{RYR_YELLOW_ARROW} Snippet `{name}` has been added.")


@snippet.command(name="edit")
@is_support()
async def snippet_edit(ctx, name: str, *, content):
    data = load_snippets()

    if name not in data:
        return await ctx.send(f"{RYR_BLUE_ARROW} That snippet does not exist.")

    data[name] = content
    save_snippets(data)

    await ctx.send(f"{RYR_YELLOW_ARROW} Snippet `{name}` has been updated.")


@snippet.command(name="delete")
@is_support()
async def snippet_delete(ctx, name: str):
    data = load_snippets()

    if name not in data:
        return await ctx.send(f"{RYR_BLUE_ARROW} That snippet does not exist.")

    del data[name]
    save_snippets(data)

    await ctx.send(f"{RYR_MAINTENANCE} Snippet `{name}` has been deleted.")


@bot.command(name="edit")
@is_support()
async def edit_message(ctx, msg_id: int, *, content):
    try:
        msg = await ctx.channel.fetch_message(msg_id)

        if msg.author.id != bot.user.id:
            return await ctx.send(
                f"{RYR_BLUE_ARROW} I can only edit messages sent by the bot."
            )

        if msg.embeds:
            embed = msg.embeds[0]
            embed.description = content
            await msg.edit(embed=embed)
        else:
            await msg.edit(content=content)

        await safe_delete(ctx.message)

    except Exception as e:
        await ctx.send(f"{RYR_BLUE_ARROW} Could not edit that message.")


@bot.command(name="d")
@is_support()
async def delete_message(ctx, msg_id: int):
    try:
        msg = await ctx.channel.fetch_message(msg_id)
        await msg.delete()
        await safe_delete(ctx.message)

    except:
        await ctx.send(f"{RYR_BLUE_ARROW} Could not delete that message.")


@bot.command(name="help")
@is_support()
async def help_command(ctx):
    embed = discord.Embed(
        title=f"{RYR_LOGO} Ryan Air Concierge Commands",
        description=(
            f"{RYR_YELLOW_ARROW} `-r message` — Reply normally\n"
            f"{RYR_YELLOW_ARROW} `-ra message` — Anonymous reply\n"
            f"{RYR_YELLOW_ARROW} `-snippets` — View snippets\n"
            f"{RYR_YELLOW_ARROW} `-snippet add name content` — Add snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet edit name content` — Edit snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet delete name` — Delete snippet\n"
            f"{RYR_YELLOW_ARROW} `-edit message_id content` — Edit bot message\n"
            f"{RYR_YELLOW_ARROW} `-d message_id` — Delete message\n\n"
            f"{RYR_FLAG} Typing `hi`, `hello`, or `hey` opens the ticket confirmation interface."
        ),
        color=BRAND_COLOR
    )

    embed.set_thumbnail(url=LOGO_URL)
    await ctx.send(embed=embed)


# =========================
# ERROR HANDLING
# =========================

@reply.error
@anonymous_reply.error
@snippets.error
@snippet.error
@edit_message.error
@delete_message.error
@help_command.error
async def command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} You do not have permission to use this command."
        )

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} Missing required information. Use `-help` for command formats."
        )

    await ctx.send(f"{RYR_BLUE_ARROW} Something went wrong while running this command.")


# =========================
# RUN BOT
# =========================

bot.run(TOKEN)
