import discord
from discord.ext import commands
import json
import os
import random
import re

# =========================
# RYAN AIR CONCIERGE CONFIG
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    TOKEN = TOKEN.strip()

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in Railway Variables.")

if TOKEN.startswith("Bot "):
    raise RuntimeError("Remove 'Bot ' from your token. Paste only the raw bot token.")

if "DISCORD_TOKEN=" in TOKEN:
    raise RuntimeError("In Railway value, paste only the token, not DISCORD_TOKEN=token.")

PREFIX = "-"

# Put your Ryan Air Concierge staff/support role ID here
SUPPORT_ROLE_ID = 123456789012345678

# Your ticket category ID
TICKET_CATEGORY_ID = 1502957109560606871

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
intents.dm_messages = True

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
    name = name.strip("-")
    return name[:24] if name else "user"


async def safe_delete(message):
    try:
        await message.delete()
    except:
        pass


def has_support_perms(member):
    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_messages:
        return True

    return any(role.id == SUPPORT_ROLE_ID for role in member.roles)


def is_support():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        return has_support_perms(ctx.author)

    return commands.check(predicate)


def get_ticket_user_id_from_channel(channel):
    if not channel.topic:
        return None

    match = re.search(r"ryanair-dm-user:(\d+)", channel.topic)

    if not match:
        return None

    return int(match.group(1))


def is_ticket_channel(channel):
    return get_ticket_user_id_from_channel(channel) is not None


async def get_ticket_category():
    category = bot.get_channel(TICKET_CATEGORY_ID)

    if category is None:
        try:
            category = await bot.fetch_channel(TICKET_CATEGORY_ID)
        except:
            return None

    if not isinstance(category, discord.CategoryChannel):
        return None

    return category


async def get_ticket_user(channel):
    user_id = get_ticket_user_id_from_channel(channel)

    if user_id is None:
        return None

    try:
        return await bot.fetch_user(user_id)
    except:
        return None


async def find_existing_ticket(user_id):
    category = await get_ticket_category()

    if category is None:
        return None

    topic_key = f"ryanair-dm-user:{user_id}"

    for channel in category.text_channels:
        if channel.topic and topic_key in channel.topic:
            return channel

    return None


async def create_ticket_channel(user, first_message=None):
    category = await get_ticket_category()

    if category is None:
        return None

    guild = category.guild
    support_role = guild.get_role(SUPPORT_ROLE_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            attach_files=True,
            embed_links=True
        )
    }

    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            attach_files=True,
            embed_links=True
        )

    channel = await guild.create_text_channel(
        name=f"ticket-{clean_name(user.name)}",
        category=category,
        overwrites=overwrites,
        topic=f"Ryan Air Concierge DM ticket | ryanair-dm-user:{user.id}",
        reason=f"Ryan Air Concierge DM ticket opened by {user}"
    )

    opening_embed = discord.Embed(
        title=f"{RYR_PLANE} Ryan Air Concierge",
        description=(
            f"{RYR_DECENT} providing assistance of high quality\n\n"
            f"**Commendations,** a new user has contacted the **Ryan Air Concierge** through direct messages.\n\n"
            f"> {RYR_BLUE_ARROW} Staff may communicate with this user directly from this channel.\n\n"
            f"{RYR_CHECKLIST} **Available Staff Commands**\n"
            f"{RYR_YELLOW_ARROW} `-r message` — reply to the user\n"
            f"{RYR_YELLOW_ARROW} `-ra message` — anonymous reply\n"
            f"{RYR_YELLOW_ARROW} `-snippets` — view saved snippets\n"
            f"{RYR_YELLOW_ARROW} `-close` — close this ticket\n\n"
            f"{RYR_FLAG} Please remain **professional**, **patient**, and **clear** while handling this inquiry."
        ),
        color=BRAND_COLOR
    )

    opening_embed.set_author(name="Ryan Air Concierge", icon_url=LOGO_URL)
    opening_embed.set_thumbnail(url=LOGO_URL)
    opening_embed.add_field(name="User", value=f"{user.mention}", inline=True)
    opening_embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
    opening_embed.set_footer(text="Ryan Air Concierge Modmail")

    mention_text = support_role.mention if support_role else ""

    await channel.send(
        content=mention_text,
        embed=opening_embed,
        view=TicketCloseView()
    )

    if first_message:
        await forward_user_message_to_channel(channel, first_message, is_first=True)

    return channel


async def forward_user_message_to_channel(channel, message, is_first=False):
    user = message.author

    description = message.content if message.content else "*No text content provided.*"

    embed = discord.Embed(
        title=f"{RYR_BOARDINGPASS} {'New Ticket Message' if is_first else 'User Reply'}",
        description=description,
        color=BRAND_COLOR
    )

    embed.set_author(name=f"{user} • {user.id}", icon_url=user.display_avatar.url)
    embed.set_footer(text="Message received through DM")

    if message.attachments:
        attachment_lines = []

        for attachment in message.attachments:
            attachment_lines.append(f"[{attachment.filename}]({attachment.url})")

        embed.add_field(
            name=f"{RYR_MAINTENANCE} Attachments",
            value="\n".join(attachment_lines),
            inline=False
        )

        first_attachment = message.attachments[0]

        if first_attachment.content_type and first_attachment.content_type.startswith("image"):
            embed.set_image(url=first_attachment.url)

    await channel.send(embed=embed)


async def send_staff_reply_to_user(ctx, anonymous=False, message_text=""):
    target_user = await get_ticket_user(ctx.channel)

    if target_user is None:
        return await ctx.send(
            f"{RYR_BLUE_ARROW} This command must be used inside a Ryan Air Concierge ticket channel."
        )

    files = []

    for attachment in ctx.message.attachments:
        try:
            files.append(await attachment.to_file())
        except:
            pass

    if not message_text and not files:
        return await ctx.send(
            f"{RYR_BLUE_ARROW} Please provide a message or attachment to send."
        )

    if anonymous:
        random_names = [
            "Ryan Air Concierge",
            "Concierge Agent",
            "Guest Relations Agent",
            "Customer Relations",
            "Support Representative",
            "Ryan Air Assistant"
        ]

        shown_name = random.choice(random_names)
    else:
        shown_name = "Ryan Air Concierge"

    dm_embed = discord.Embed(
        title=f"{RYR_PLANE} {shown_name}",
        description=message_text if message_text else "*Attachment sent by Ryan Air Concierge.*",
        color=BRAND_COLOR
    )

    dm_embed.set_author(name=shown_name, icon_url=LOGO_URL)
    dm_embed.set_footer(text="Ryan Air Concierge")

    try:
        await target_user.send(embed=dm_embed, files=files)
    except discord.Forbidden:
        return await ctx.send(
            f"{RYR_BLUE_ARROW} I cannot DM this user. Their DMs may be closed."
        )
    except:
        return await ctx.send(
            f"{RYR_BLUE_ARROW} Failed to send the message to the user."
        )

    log_embed = discord.Embed(
        title=f"{RYR_ASCENT} Reply Sent",
        description=message_text if message_text else "*Attachment sent.*",
        color=BRAND_COLOR
    )

    log_embed.add_field(name="Sent To", value=f"{target_user} (`{target_user.id}`)", inline=False)
    log_embed.add_field(name="Sent By", value=f"{ctx.author.mention}", inline=True)
    log_embed.add_field(name="Anonymous", value="Yes" if anonymous else "No", inline=True)
    log_embed.set_footer(text="Ryan Air Concierge Staff Reply")

    await safe_delete(ctx.message)
    await ctx.send(embed=log_embed)


# =========================
# BUTTONS
# =========================

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="ryanair_close_dm_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_support_perms(interaction.user):
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} Only Ryan Air Concierge staff can close this ticket.",
                ephemeral=True
            )

        target_user = await get_ticket_user(interaction.channel)

        if target_user:
            close_embed = discord.Embed(
                title=f"{RYR_MAINTENANCE} Ticket Closed",
                description=(
                    f"{RYR_BLUE_ARROW} Your Ryan Air Concierge ticket has now been closed.\n\n"
                    f"Thank you for contacting us."
                ),
                color=BRAND_COLOR
            )

            close_embed.set_footer(text="Ryan Air Concierge")

            try:
                await target_user.send(embed=close_embed)
            except:
                pass

        await interaction.response.send_message(f"{RYR_MAINTENANCE} Closing ticket...")
        await interaction.channel.delete(reason="Ryan Air Concierge ticket closed")


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    bot.add_view(TicketCloseView())

    print("==============================")
    print(f"Logged in as {bot.user}")
    print("Ryan Air Concierge is online.")
    print("==============================")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # DM MODMAIL SYSTEM
    if isinstance(message.channel, discord.DMChannel):
        existing_channel = await find_existing_ticket(message.author.id)

        if existing_channel is None:
            new_channel = await create_ticket_channel(message.author, first_message=message)

            if new_channel is None:
                return await message.author.send(
                    "Ryan Air Concierge could not create your ticket. Please contact staff directly."
                )

            confirm_embed = discord.Embed(
                title=f"{RYR_LOGO} Ryan Air Concierge",
                description=(
                    f"{RYR_FLAG} **Dia dhuit,** thank you for contacting **Ryan Air Concierge**.\n\n"
                    f"> {RYR_BLUE_ARROW} Your ticket has been created and forwarded to our support team.\n\n"
                    f"{RYR_YELLOW_ARROW} You may continue sending messages here, and our staff will reply shortly."
                ),
                color=BRAND_COLOR
            )

            confirm_embed.set_thumbnail(url=LOGO_URL)
            confirm_embed.set_footer(text="Ryan Air Concierge")

            await message.author.send(embed=confirm_embed)

        else:
            await forward_user_message_to_channel(existing_channel, message)

        return

    # SERVER PREFIX COMMANDS
    await bot.process_commands(message)


# =========================
# PREFIX COMMANDS
# =========================

@bot.command(name="r")
@is_support()
async def reply(ctx, *, message: str = ""):
    await send_staff_reply_to_user(ctx, anonymous=False, message_text=message)


@bot.command(name="ra")
@is_support()
async def anonymous_reply(ctx, *, message: str = ""):
    await send_staff_reply_to_user(ctx, anonymous=True, message_text=message)


@bot.command(name="snippets")
@is_support()
async def snippets(ctx):
    data = load_snippets()

    if not data:
        return await ctx.send(f"{RYR_BLUE_ARROW} No snippets have been added yet.")

    description = ""

    for name, content in data.items():
        preview = content.replace("\n", " ")

        if len(preview) > 90:
            preview = preview[:90] + "..."

        description += f"{RYR_YELLOW_ARROW} `{name}` — {preview}\n"

    embed = discord.Embed(
        title=f"{RYR_CHECKLIST} Saved Snippets",
        description=description,
        color=BRAND_COLOR
    )

    embed.set_footer(text="Ryan Air Concierge Snippets")
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
            f"{RYR_BLUE_ARROW} A snippet named `{name}` already exists. Use `-snippet edit {name} content`."
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

    except:
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


@bot.command(name="close")
@is_support()
async def close_ticket(ctx):
    if not is_ticket_channel(ctx.channel):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} This command can only be used inside a Ryan Air Concierge ticket channel."
        )

    target_user = await get_ticket_user(ctx.channel)

    if target_user:
        close_embed = discord.Embed(
            title=f"{RYR_MAINTENANCE} Ticket Closed",
            description=(
                f"{RYR_BLUE_ARROW} Your Ryan Air Concierge ticket has now been closed.\n\n"
                f"Thank you for contacting us."
            ),
            color=BRAND_COLOR
        )

        try:
            await target_user.send(embed=close_embed)
        except:
            pass

    await ctx.send(f"{RYR_MAINTENANCE} Closing this ticket...")
    await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")


@bot.command(name="help")
@is_support()
async def help_command(ctx):
    embed = discord.Embed(
        title=f"{RYR_LOGO} Ryan Air Concierge Commands",
        description=(
            f"{RYR_YELLOW_ARROW} `-r message` — reply to the DM user\n"
            f"{RYR_YELLOW_ARROW} `-ra message` — anonymous reply to the DM user\n"
            f"{RYR_YELLOW_ARROW} `-snippets` — view snippets\n"
            f"{RYR_YELLOW_ARROW} `-snippet add name content` — add snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet edit name content` — edit snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet delete name` — delete snippet\n"
            f"{RYR_YELLOW_ARROW} `-edit message_id content` — edit bot message\n"
            f"{RYR_YELLOW_ARROW} `-d message_id` — delete a channel message\n"
            f"{RYR_YELLOW_ARROW} `-close` — close ticket\n\n"
            f"{RYR_FLAG} Users create tickets by **DMing the bot**."
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
@close_ticket.error
@help_command.error
async def command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} You do not have permission to use this command."
        )

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} Missing information. Use `-help` for command formats."
        )

    await ctx.send(f"{RYR_BLUE_ARROW} Something went wrong while running this command.")


# =========================
# RUN BOT
# =========================

bot.run(TOKEN)
