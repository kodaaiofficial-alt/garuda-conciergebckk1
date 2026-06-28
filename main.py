import discord
from discord.ext import commands
import json
import os
import random
import re

# =========================
# CONFIG
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

# Staff role that can use commands
SUPPORT_ROLE_ID = 1500774142423863337

# Role to ping whenever a ticket opens
TICKET_PING_ROLE_ID = 1500774142423863337

# Ticket category
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
# HELPERS
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


def get_ticket_user_id_from_channel(channel):
    if not channel.topic:
        return None

    match = re.search(r"ryanair-dm-user:(\d+)", channel.topic)

    if not match:
        return None

    return int(match.group(1))


def get_claimed_user_id(channel):
    if not channel.topic:
        return None

    match = re.search(r"claimed:(\d+)", channel.topic)

    if not match:
        return None

    return int(match.group(1))


def is_ticket_channel(channel):
    return get_ticket_user_id_from_channel(channel) is not None


async def get_ticket_user(channel):
    user_id = get_ticket_user_id_from_channel(channel)

    if user_id is None:
        return None

    try:
        return await bot.fetch_user(user_id)
    except:
        return None


async def get_member_rank(guild, user_id):
    member = guild.get_member(user_id)

    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except:
            return "No rank found"

    roles = [role for role in member.roles if role.name != "@everyone"]

    if not roles:
        return "No rank found"

    highest_role = roles[-1]
    return highest_role.mention


async def find_existing_ticket(user_id):
    category = await get_ticket_category()

    if category is None:
        return None

    topic_key = f"ryanair-dm-user:{user_id}"

    for channel in category.guild.text_channels:
        if channel.category_id == TICKET_CATEGORY_ID:
            if channel.topic and topic_key in channel.topic:
                return channel

    return None


def set_embed_field(embed, field_name, field_value, inline=True):
    for index, field in enumerate(embed.fields):
        if field.name == field_name:
            embed.set_field_at(
                index,
                name=field_name,
                value=field_value,
                inline=inline
            )
            return embed

    embed.add_field(name=field_name, value=field_value, inline=inline)
    return embed


async def update_ticket_embed_field(channel, field_name, field_value, inline=True):
    async for msg in channel.history(limit=25, oldest_first=True):
        if msg.author.id == bot.user.id and msg.embeds:
            embed = msg.embeds[0]

            found_ticket_embed = any(
                field.name in ["User", "Rank Given", "Inquiry Type", "Claimed By"]
                for field in embed.fields
            )

            if found_ticket_embed:
                embed = set_embed_field(embed, field_name, field_value, inline)
                await msg.edit(embed=embed)
                return


async def update_channel_topic(channel, inquiry_type=None, claimed_user_id=None):
    topic = channel.topic or ""

    if inquiry_type is not None:
        if "inquiry:" in topic:
            topic = re.sub(r"inquiry:[^|]+", f"inquiry:{inquiry_type}", topic)
        else:
            topic += f" | inquiry:{inquiry_type}"

    if claimed_user_id is not None:
        if "claimed:" in topic:
            topic = re.sub(r"claimed:[^|]+", f"claimed:{claimed_user_id}", topic)
        else:
            topic += f" | claimed:{claimed_user_id}"

    try:
        await channel.edit(topic=topic)
    except:
        pass


# =========================
# TICKET CREATION
# =========================

async def create_ticket_channel(user, first_message):
    category = await get_ticket_category()

    if category is None:
        return None

    guild = category.guild
    support_role = guild.get_role(SUPPORT_ROLE_ID)
    ping_role = guild.get_role(TICKET_PING_ROLE_ID)

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

    if ping_role and ping_role != support_role:
        overwrites[ping_role] = discord.PermissionOverwrite(
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
        topic=f"Ryan Air Concierge DM ticket | ryanair-dm-user:{user.id} | inquiry:Not selected | claimed:None",
        reason=f"Ryan Air Concierge DM ticket opened by {user}"
    )

    rank_given = await get_member_rank(guild, user.id)
    message_content = first_message.content if first_message.content else "*No text content provided.*"

    embed = discord.Embed(
        description=message_content,
        color=BRAND_COLOR
    )

    embed.add_field(name="User", value=f"{user.mention}\n`{user.id}`", inline=True)
    embed.add_field(name="Rank Given", value=rank_given, inline=True)
    embed.add_field(name="Inquiry Type", value="Not selected yet", inline=True)
    embed.add_field(name="Claimed By", value="Not claimed yet", inline=True)

    if first_message.attachments:
        attachment_lines = []

        for attachment in first_message.attachments:
            attachment_lines.append(f"[{attachment.filename}]({attachment.url})")

        embed.add_field(
            name="Attachments",
            value="\n".join(attachment_lines),
            inline=False
        )

        first_attachment = first_message.attachments[0]

        if first_attachment.content_type and first_attachment.content_type.startswith("image"):
            embed.set_image(url=first_attachment.url)

    ping_text = ping_role.mention if ping_role else ""

    await channel.send(
        content=ping_text,
        embed=embed,
        view=TicketStaffView(),
        allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False)
    )

    return channel


async def forward_user_message_to_channel(channel, message):
    user = message.author
    description = message.content if message.content else "*No text content provided.*"

    embed = discord.Embed(
        title="User Reply",
        description=description,
        color=BRAND_COLOR
    )

    embed.set_author(name=f"{user} • {user.id}", icon_url=user.display_avatar.url)

    if message.attachments:
        attachment_lines = []

        for attachment in message.attachments:
            attachment_lines.append(f"[{attachment.filename}]({attachment.url})")

        embed.add_field(
            name="Attachments",
            value="\n".join(attachment_lines),
            inline=False
        )

        first_attachment = message.attachments[0]

        if first_attachment.content_type and first_attachment.content_type.startswith("image"):
            embed.set_image(url=first_attachment.url)

    await channel.send(embed=embed)


async def send_dm_confirmation(user):
    category = await get_ticket_category()
    rank_given = "No rank found"

    if category:
        rank_given = await get_member_rank(category.guild, user.id)

    embed = discord.Embed(
        description=(
            f"{RYR_FLAG} **Dia dhuit,** thank you for contacting **Ryan Air Concierge**.\n\n"
            f"> {RYR_BLUE_ARROW} Your message has been received by our support team.\n\n"
            f"{RYR_YELLOW_ARROW} Please press **✅** to continue with your ticket, or **❌** to cancel it."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(name="User", value=f"{user.mention}", inline=True)
    embed.add_field(name="Rank Given", value=rank_given, inline=True)

    await user.send(embed=embed, view=DMConfirmView())


# =========================
# USER DM VIEWS
# =========================

class DMConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="ryanair_dm_confirm_ticket"
    )
    async def confirm_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await find_existing_ticket(interaction.user.id)

        if channel is None:
            embed = discord.Embed(
                description=f"{RYR_BLUE_ARROW} Your ticket could not be found. Please send another DM to create a new one.",
                color=BRAND_COLOR
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        embed = discord.Embed(
            description=(
                f"{RYR_CHECKLIST} Please choose the type of inquiry you need assistance with.\n\n"
                f"{RYR_BLUE_ARROW} Once selected, our team will be notified in your ticket channel."
            ),
            color=BRAND_COLOR
        )

        await interaction.response.edit_message(embed=embed, view=InquiryTypeView())

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        emoji="❌",
        custom_id="ryanair_dm_cancel_ticket"
    )
    async def cancel_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await find_existing_ticket(interaction.user.id)

        if channel:
            try:
                await channel.delete(reason="User cancelled Ryan Air Concierge ticket")
            except:
                pass

        embed = discord.Embed(
            description=f"{RYR_MAINTENANCE} Your ticket request has been cancelled.",
            color=BRAND_COLOR
        )

        await interaction.response.edit_message(embed=embed, view=None)


class InquirySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Public Relations",
                description="Partnerships, relations, affiliates, or communication inquiries.",
                emoji=RYR_PARTNERSHIP,
                value="Public Relations"
            ),
            discord.SelectOption(
                label="Human Resources",
                description="Staffing, recruitment, rank, or department-related inquiries.",
                emoji=RYR_ACADEMY,
                value="Human Resources"
            ),
            discord.SelectOption(
                label="General",
                description="General questions, support, concerns, or assistance.",
                emoji=RYR_CHECKLIST,
                value="General"
            )
        ]

        super().__init__(
            placeholder="Select your inquiry type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ryanair_inquiry_type_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        channel = await find_existing_ticket(interaction.user.id)

        if channel is None:
            embed = discord.Embed(
                description=f"{RYR_BLUE_ARROW} Your ticket could not be found. Please send another DM to create a new one.",
                color=BRAND_COLOR
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        await update_channel_topic(channel, inquiry_type=selected)
        await update_ticket_embed_field(channel, "Inquiry Type", selected, inline=True)

        staff_embed = discord.Embed(
            description=(
                f"{RYR_CHECKLIST} {interaction.user.mention} selected the inquiry type:\n\n"
                f"**{selected}**"
            ),
            color=BRAND_COLOR
        )

        await channel.send(embed=staff_embed)

        user_embed = discord.Embed(
            description=(
                f"{RYR_YELLOW_ARROW} Your inquiry has been marked as **{selected}**.\n\n"
                f"{RYR_BLUE_ARROW} You may continue sending messages here. Staff will reply shortly."
            ),
            color=BRAND_COLOR
        )

        await interaction.response.edit_message(embed=user_embed, view=None)


class InquiryTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(InquirySelect())


# =========================
# STAFF TICKET VIEW
# =========================

class TicketStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.green,
        emoji="👁️",
        custom_id="ryanair_claim_ticket"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_support_perms(interaction.user):
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} Only Ryan Air Concierge staff can claim this ticket.",
                ephemeral=True
            )

        if not is_ticket_channel(interaction.channel):
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} This is not a ticket channel.",
                ephemeral=True
            )

        claimed_id = get_claimed_user_id(interaction.channel)

        if claimed_id and claimed_id != interaction.user.id:
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} This ticket is already claimed by <@{claimed_id}>.",
                ephemeral=True
            )

        await update_channel_topic(interaction.channel, claimed_user_id=interaction.user.id)

        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed = set_embed_field(embed, "Claimed By", interaction.user.mention, inline=True)
        else:
            embed = None

        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "ryanair_claim_ticket":
                item.label = f"Claimed by {interaction.user.display_name}"
                item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        claim_embed = discord.Embed(
            description=f"👁️ This ticket has been claimed by {interaction.user.mention}.",
            color=BRAND_COLOR
        )

        await interaction.followup.send(embed=claim_embed)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        emoji="❌",
        custom_id="ryanair_close_ticket_button"
    )
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_support_perms(interaction.user):
            return await interaction.response.send_message(
                f"{RYR_BLUE_ARROW} Only Ryan Air Concierge staff can close this ticket.",
                ephemeral=True
            )

        target_user = await get_ticket_user(interaction.channel)

        if target_user:
            close_embed = discord.Embed(
                description=(
                    f"{RYR_MAINTENANCE} Your Ryan Air Concierge ticket has now been closed.\n\n"
                    f"Thank you for contacting us."
                ),
                color=BRAND_COLOR
            )

            try:
                await target_user.send(embed=close_embed)
            except:
                pass

        await interaction.response.send_message(f"{RYR_MAINTENANCE} Closing ticket...")
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    bot.add_view(DMConfirmView())
    bot.add_view(InquiryTypeView())
    bot.add_view(TicketStaffView())

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
            new_channel = await create_ticket_channel(message.author, message)

            if new_channel is None:
                return await message.author.send(
                    "Ryan Air Concierge could not create your ticket. Please contact staff directly."
                )

            await send_dm_confirmation(message.author)

        else:
            await forward_user_message_to_channel(existing_channel, message)

        return

    # SERVER COMMANDS
    await bot.process_commands(message)


# =========================
# STAFF COMMANDS
# =========================

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
            "Concierge Agent",
            "Guest Relations Agent",
            "Customer Relations",
            "Support Representative",
            "Ryan Air Assistant"
        ]

        shown_name = random.choice(random_names)

        dm_embed = discord.Embed(
            description=message_text if message_text else "*Attachment sent.*",
            color=BRAND_COLOR
        )
        dm_embed.set_footer(text=shown_name)

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

    else:
        dm_embed = discord.Embed(
            description=message_text if message_text else "*Attachment sent.*",
            color=BRAND_COLOR
        )
        dm_embed.set_footer(text=ctx.author.display_name)

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

    rank_given = await get_member_rank(ctx.guild, target_user.id)

    log_embed = discord.Embed(
        description=message_text if message_text else "*Attachment sent.*",
        color=BRAND_COLOR
    )

    log_embed.add_field(name="User", value=f"{target_user.mention}\n`{target_user.id}`", inline=True)
    log_embed.add_field(name="Rank Given", value=rank_given, inline=True)
    log_embed.add_field(name="Sent By", value=ctx.author.mention, inline=True)
    log_embed.add_field(name="Anonymous", value="Yes" if anonymous else "No", inline=True)

    await safe_delete(ctx.message)
    await ctx.send(embed=log_embed)


@bot.command(name="r")
@is_support()
async def reply(ctx, *, message_text: str = ""):
    await send_staff_reply_to_user(ctx, anonymous=False, message_text=message_text)


@bot.command(name="ra")
@is_support()
async def anonymous_reply(ctx, *, message_text: str = ""):
    await send_staff_reply_to_user(ctx, anonymous=True, message_text=message_text)


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
            description=(
                f"{RYR_MAINTENANCE} Your Ryan Air Concierge ticket has now been closed.\n\n"
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
            f"{RYR_YELLOW_ARROW} `-r message` — reply to the user\n"
            f"{RYR_YELLOW_ARROW} `-ra message` — anonymous reply\n"
            f"{RYR_YELLOW_ARROW} `-snippets` — view snippets\n"
            f"{RYR_YELLOW_ARROW} `-snippet add name content` — add snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet edit name content` — edit snippet\n"
            f"{RYR_YELLOW_ARROW} `-snippet delete name` — delete snippet\n"
            f"{RYR_YELLOW_ARROW} `-edit message_id content` — edit bot message\n"
            f"{RYR_YELLOW_ARROW} `-d message_id` — delete message\n"
            f"{RYR_YELLOW_ARROW} `-close` — close ticket\n\n"
            f"{RYR_FLAG} Users create tickets by DMing the bot."
        ),
        color=BRAND_COLOR
    )

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

    if isinstance(error, commands.BadArgument):
        return await ctx.send(
            f"{RYR_BLUE_ARROW} Invalid format. Use `-help` for command formats."
        )

    await ctx.send(f"{RYR_BLUE_ARROW} Something went wrong while running this command.")


# =========================
# RUN BOT
# =========================

bot.run(TOKEN)
