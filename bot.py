import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import io
import os
import random
import datetime

TOKEN = os.environ["BOT_TOKEN"]
GUILD_ID = 1472343485687267408

ROLE = {
    "trial_middleman": 1472343485695918100,
    "head_middleman": 1472343485695918101,
    "ex_middleman": 1472343485695918102,
    "moderator": 1472343485695918109,
    "server_admin": 1472343485704310794,
    "operation_coordinator": 1472343485704310798,
    "head_of_mang": 1519461160758415494,
    "head_of_dev": 1519416570605076560,
    "head_of_op": 1472343485704310801,
    "cheif_mang_officer": 1472343485704310802,
    "head_of_coordination": 1472343485704310803,
    "head_of_marketing": 1523102041096847520,
    "president": 1472343485712433192,
    "head_of_security": 1519443257803804812,
    "index_mm": 1519444171763482675,
    "ban_perms": 1472343485704310795,
}

REACTION_ROLES = {
    "announcements": 1522943428005203998,
    "update": 1522943519575244800,
    "active": 1522946063592456222,
}

HIERARCHY = [
    ROLE["trial_middleman"],
    ROLE["head_middleman"],
    ROLE["ex_middleman"],
    ROLE["moderator"],
    ROLE["server_admin"],
    ROLE["operation_coordinator"],
    ROLE["head_of_mang"],
    ROLE["head_of_dev"],
    ROLE["head_of_op"],
    ROLE["cheif_mang_officer"],
    ROLE["head_of_coordination"],
    ROLE["head_of_marketing"],
    ROLE["president"],
    ROLE["head_of_security"],
]

HIERARCHY_IDS = HIERARCHY[:]

PROMOTE_CEILING = {
    ROLE["operation_coordinator"]: ROLE["head_middleman"],
    ROLE["head_of_mang"]: ROLE["operation_coordinator"],
    ROLE["head_of_dev"]: ROLE["head_of_mang"],
    ROLE["cheif_mang_officer"]: ROLE["head_of_dev"],
    ROLE["head_of_op"]: ROLE["cheif_mang_officer"],
    ROLE["head_of_coordination"]: ROLE["head_of_op"],
    ROLE["head_of_marketing"]: ROLE["head_of_coordination"],
    ROLE["president"]: ROLE["head_of_marketing"],
    ROLE["head_of_security"]: ROLE["president"],
}

CH = {
    "mm_setup": 1519421791167320166,
    "mm_ticket_cat": 1519448170336354366,
    "support_setup": 1519461568599822397,
    "support_cat": 1519448267564384399,
    "index_setup": 1519422636642275421,
    "index_cat": 1519448328163823780,
    "transcript_ch": 1472343487792939088,
    "ban_log": 1472343487792939089,
    "role_log": 1472343487973425173,
    "app_setup": 1519462194121805875,
    "app_cat": 1519462274245333134,
    "d7_setup": 1512639881887748293,
    "d7_cat": 1512639882130882686,
    "staff_chat": 1519717344421613751,
    "alt_flop_ch": 1519412904418607376,
}

FOOTER = "Powered by Tsunami MM Services"

ALL_STAFF = list(ROLE.values())
TICKET_STAFF = ALL_STAFF
MM_CLAIM = [ROLE["trial_middleman"], ROLE["head_middleman"], ROLE["ex_middleman"],
    ROLE["moderator"], ROLE["server_admin"], ROLE["operation_coordinator"],
    ROLE["head_of_mang"], ROLE["head_of_dev"], ROLE["head_of_op"],
    ROLE["cheif_mang_officer"], ROLE["head_of_coordination"], ROLE["head_of_marketing"],
    ROLE["president"], ROLE["head_of_security"]]
INDEX_CLAIM = [ROLE["index_mm"]]
ADMIN_ROLES = [ROLE["head_of_mang"], ROLE["head_of_dev"], ROLE["head_of_op"],
    ROLE["cheif_mang_officer"], ROLE["head_of_coordination"], ROLE["head_of_marketing"],
    ROLE["president"], ROLE["head_of_security"]]
SETUP_ROLE = 1472343485721083915
MERCY_USE_ROLE = [ROLE["trial_middleman"], ROLE["head_middleman"]]
MM_PING = [ROLE["trial_middleman"]]

active_trades: dict = {}
ban_cooldowns: dict = {}


def has_role(member: discord.Member, role_ids: list) -> bool:
    return any(r.id in role_ids for r in member.roles)


def top_role_id(member: discord.Member):
    for rid in reversed(HIERARCHY):
        if any(r.id == rid for r in member.roles):
            return rid
    return None


def can_manage_role(executor: discord.Member, target_role_id: int) -> bool:
    top = top_role_id(executor)
    if top not in PROMOTE_CEILING:
        return False
    ceiling = PROMOTE_CEILING[top]
    ceiling_idx = HIERARCHY.index(ceiling)
    try:
        target_idx = HIERARCHY.index(target_role_id)
    except ValueError:
        return False
    return 0 <= target_idx <= ceiling_idx


async def make_transcript(channel: discord.TextChannel) -> io.BytesIO:
    lines = []
    async for msg in channel.history(limit=None, oldest_first=True):
        ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"[{ts}] {msg.author} ({msg.author.id}): {msg.content}")
        for e in msg.embeds:
            if e.title:
                lines.append(f"  [EMBED TITLE] {e.title}")
            if e.description:
                lines.append(f"  [EMBED DESC]  {e.description}")
            for f in e.fields:
                lines.append(f"  [{f.name}] {f.value}")
    return io.BytesIO("\n".join(lines).encode())


def ts_now() -> str:
    return discord.utils.utcnow().strftime("%A, %B %d, %Y %I:%M %p")


def mm_overwrites(guild: discord.Guild, opener: discord.Member) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        opener: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for rid in MM_CLAIM:
        r = guild.get_role(rid)
        if r:
            ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    return ow


def support_overwrites(guild: discord.Guild, opener: discord.Member) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        opener: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for rid in ALL_STAFF:
        r = guild.get_role(rid)
        if r:
            ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    return ow


def index_overwrites(guild: discord.Guild, opener: discord.Member) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        opener: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for rid in INDEX_CLAIM + ADMIN_ROLES:
        r = guild.get_role(rid)
        if r:
            ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    return ow


async def do_close(interaction: discord.Interaction, claimed_by: str = None, ticket_creator: str = None):
    if not has_role(interaction.user, TICKET_STAFF):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    ch = interaction.channel
    buf = await make_transcript(ch)
    tr_ch = interaction.guild.get_channel(CH["transcript_ch"])
    if tr_ch:
        embed = discord.Embed(color=0x2b2d31, title=f"Transcript for Ticket #{ch.name}")
        embed.add_field(name="Ticket Creator", value=ticket_creator or "Unknown", inline=False)
        embed.add_field(name="Claimed By", value=claimed_by or "Unknown", inline=False)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=False)
        embed.add_field(name="Closed At", value=ts_now(), inline=False)
        embed.set_footer(text=FOOTER)
        try:
            await tr_ch.send(embed=embed, file=discord.File(buf, filename=f"transcript-{ch.name}.txt"))
        except discord.Forbidden:
            await tr_ch.send(embed=embed)
            await tr_ch.send("⚠️ Could not attach transcript file.")
    await interaction.response.send_message("Closing ticket in 5 seconds…")
    await asyncio.sleep(5)
    await ch.delete()


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=GUILD_ID)


async def send_trade_log(guild: discord.Guild) -> bool:
    mm_role = guild.get_role(TRADE_LOG_MM_ROLE)
    member_role = guild.get_role(TRADE_LOG_MEMBER_ROLE)
    ch = guild.get_channel(TRADE_LOG_CH)
    if not mm_role or not member_role or not ch:
        return False

    middlemen = [m for m in mm_role.members if not m.bot]
    members = [m for m in member_role.members if not m.bot]
    if not middlemen or len(members) < 2:
        return False

    mm = random.choice(middlemen)
    trader1, trader2 = random.sample(members, 2)
    trade = random.choice(TRADE_OPTIONS)
    fee = random.choice(FEE_OPTIONS)

    embed = discord.Embed(color=0x2b2d31, title="🔄 Trade Log")
    embed.add_field(name="Middleman", value=str(mm.display_name), inline=False)
    embed.add_field(name="Trader 1", value=str(trader1.display_name), inline=False)
    embed.add_field(name="Trader 2", value=str(trader2.display_name), inline=False)
    embed.add_field(name="Trade", value=trade, inline=False)
    embed.add_field(name="Fee", value=fee, inline=False)
    embed.set_footer(text=FOOTER)

    await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    return True


@tasks.loop(minutes=15)
async def post_trade_log():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    await send_trade_log(guild)


@post_trade_log.before_loop
async def before_post_trade_log():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    bot.add_view(MMRequestView())
    bot.add_view(SupportRequestView())
    bot.add_view(MutationForgeView())
    bot.add_view(ValuesView())
    bot.add_view(ReactionRolesView())
    bot.add_view(MMTicketView())
    bot.add_view(IndexTicketView())
    bot.add_view(SupportTicketView())

    if not post_trade_log.is_running():
        post_trade_log.start()

    # Wipe any stale GLOBAL commands (leftover from previous versions, e.g. old /flop, /floplb).
    # This file only defines guild-specific commands, so the global tree is empty here —
    # syncing it pushes that emptiness to Discord and removes old global leftovers.
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync(guild=None)

    # Sync guild-specific commands. This fully replaces whatever Discord has stored for this
    # guild with exactly what's defined in this file right now — old commands not in this file
    # (like /floplb, /viewflops) get removed automatically.
    await bot.tree.sync(guild=GUILD)
    print("Synced commands, old ones cleared.")


class MMTicketView(discord.ui.View):
    def __init__(self, creator: str = "Unknown"):
        super().__init__(timeout=None)
        self.claimed_by = None
        self.creator = creator

    @discord.ui.button(label="Claimed", style=discord.ButtonStyle.success, emoji="🤝", custom_id="v:mm_claim")
    async def claim(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if not has_role(interaction.user, MM_CLAIM):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        self.claimed_by = interaction.user.mention
        btn.disabled = True
        btn.label = "Claimed"
        await interaction.message.edit(view=self)
        ch = interaction.channel
        guild = interaction.guild
        creator_member = None
        if ch.topic and ch.topic.isdigit():
            creator_member = guild.get_member(int(ch.topic))
        new_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if creator_member:
            new_overwrites[creator_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        for rid in MM_CLAIM:
            r = guild.get_role(rid)
            if r and r not in new_overwrites:
                new_overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
        await ch.edit(overwrites=new_overwrites)
        embed = discord.Embed(color=0x57f287, title="✅ Ticket Claimed")
        embed.description = f"{interaction.user.mention} will be your Middleman for today."
        embed.set_footer(text=FOOTER)
        await interaction.response.defer()
        await ch.send(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="v:mm_close")
    async def close(self, interaction: discord.Interaction, btn: discord.ui.Button):
        await do_close(interaction, claimed_by=self.claimed_by, ticket_creator=self.creator)


class IndexTicketView(discord.ui.View):
    def __init__(self, creator: str = "Unknown"):
        super().__init__(timeout=None)
        self.claimed_by = None
        self.creator = creator

    @discord.ui.button(label="Claimed", style=discord.ButtonStyle.success, emoji="✅", custom_id="v:index_claim")
    async def claim(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if not has_role(interaction.user, INDEX_CLAIM + ADMIN_ROLES):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        self.claimed_by = interaction.user.mention
        btn.disabled = True
        btn.label = "Claimed"
        await interaction.message.edit(view=self)
        embed = discord.Embed(color=0x57f287, title="✅ Index Ticket Claimed")
        embed.description = f"{interaction.user.mention} will be your Indexer for today."
        embed.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="v:index_close")
    async def close(self, interaction: discord.Interaction, btn: discord.ui.Button):
        await do_close(interaction, claimed_by=self.claimed_by, ticket_creator=self.creator)


class SupportTicketView(discord.ui.View):
    def __init__(self, creator: str = "Unknown"):
        super().__init__(timeout=None)
        self.creator = creator

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="v:support_close")
    async def close(self, interaction: discord.Interaction, btn: discord.ui.Button):
        await do_close(interaction, ticket_creator=self.creator)


class MMRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Middleman", style=discord.ButtonStyle.primary, custom_id="v:mm_request")
    async def request(self, interaction: discord.Interaction, btn: discord.ui.Button):
        guild = interaction.guild
        cat = guild.get_channel(CH["mm_ticket_cat"])
        if cat is None:
            await interaction.response.send_message("Ticket category not found.", ephemeral=True)
            return
        for c in cat.channels:
            if c.topic == str(interaction.user.id):
                await interaction.response.send_message(f"You already have an open ticket: {c.mention}", ephemeral=True)
                return
        modal = MMModal(guild=guild, opener=interaction.user)
        await interaction.response.send_modal(modal)


class MMModal(discord.ui.Modal, title="Middleman Ticket"):
    trading_with = discord.ui.TextInput(label="Who are you trading with?", style=discord.TextStyle.short, placeholder="Enter their username or @mention", required=True)
    trade_details = discord.ui.TextInput(label="What is the trade?", style=discord.TextStyle.paragraph, placeholder="Describe what items/currency are being traded", required=True)

    def __init__(self, guild: discord.Guild, opener: discord.Member):
        super().__init__()
        self.guild = guild
        self.opener = opener

    async def on_submit(self, interaction: discord.Interaction):
        cat = self.guild.get_channel(CH["mm_ticket_cat"])
        ch = await self.guild.create_text_channel(name=f"ticket-{self.opener.name}", category=cat, overwrites=mm_overwrites(self.guild, self.opener), topic=str(self.opener.id))
        embed = discord.Embed(color=0x2b2d31, title="🎫 Middleman Ticket")
        embed.description = f"{self.opener.mention}, thank you for using our Middleman service!\n\nA Middleman will be with you shortly. Please do not share any items or currency until one has been assigned."
        embed.add_field(name="👤 Trading With", value=str(self.trading_with), inline=False)
        embed.add_field(name="📦 Trade Details", value=str(self.trade_details), inline=False)
        embed.set_footer(text=FOOTER)
        pings = " ".join(f"<@&{rid}>" for rid in MM_PING) + f" {self.opener.mention}"
        view = MMTicketView(creator=self.opener.mention)
        await ch.send(content=pings, embed=embed, view=view)
        await interaction.response.send_message(f"Ticket created: {ch.mention}", ephemeral=True)


class SupportRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="v:support_request")
    async def support(self, interaction: discord.Interaction, btn: discord.ui.Button):
        guild = interaction.guild
        cat = guild.get_channel(CH["support_cat"])
        if cat is None:
            await interaction.response.send_message("Support category not found.", ephemeral=True)
            return
        for c in cat.channels:
            if c.topic == str(interaction.user.id):
                await interaction.response.send_message(f"You already have an open ticket: {c.mention}", ephemeral=True)
                return
        modal = SupportModal(guild=guild, opener=interaction.user)
        await interaction.response.send_modal(modal)


class SupportModal(discord.ui.Modal, title="Support Ticket | Tsunami MM Services"):
    what = discord.ui.TextInput(label="What would you like help with?", style=discord.TextStyle.paragraph, required=True)
    urgency = discord.ui.TextInput(label="How urgent is this? (1-10)", style=discord.TextStyle.short, required=True, max_length=2)

    def __init__(self, guild: discord.Guild, opener: discord.Member):
        super().__init__()
        self.guild = guild
        self.opener = opener

    async def on_submit(self, interaction: discord.Interaction):
        cat = self.guild.get_channel(CH["support_cat"])
        ch = await self.guild.create_text_channel(name=f"support-{self.opener.name}", category=cat, overwrites=support_overwrites(self.guild, self.opener), topic=str(self.opener.id))
        embed = discord.Embed(color=0x2b2d31, title="🎫 Support Ticket")
        embed.description = f"{self.opener.mention}, a staff member will be with you shortly.\n\n**Create a ticket if you need support for:**\n• Report a scammer\n• Report a middleman\n• Need help creating a ticket\n• Other"
        embed.add_field(name="Issue", value=str(self.what), inline=False)
        embed.add_field(name="Urgency", value=str(self.urgency), inline=False)
        embed.set_footer(text=FOOTER)
        view = SupportTicketView(creator=self.opener.mention)
        await ch.send(content=self.opener.mention, embed=embed, view=view)
        await interaction.response.send_message(f"Support ticket created: {ch.mention}", ephemeral=True)


class MutationForgeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Basic Forge", description="Common mutations | Cheap & fast", emoji="🟢"),
            discord.SelectOption(label="Advanced Forge", description="Mid-tier mutations | Best value", emoji="🔵"),
            discord.SelectOption(label="Elite Forge", description="High-value mutations | Premium", emoji="🟣"),
            discord.SelectOption(label="Event Forge", description="Limited-time boosts | Highest RNG", emoji="🟡"),
            discord.SelectOption(label="Collector Forge", description="Aesthetic / flex crops", emoji="✨"),
            discord.SelectOption(label="Bulk Forge", description="10x+ mutation packages", emoji="📦"),
        ]
        super().__init__(placeholder="Select a Mutation Forge service...", options=options, custom_id="v:mutation_forge_select")

    async def callback(self, interaction: discord.Interaction):
        forge = self.values[0]
        guild = interaction.guild
        cat = guild.get_channel(CH["index_cat"])
        if cat is None:
            await interaction.response.send_message("Mutation category not found.", ephemeral=True)
            return
        for c in cat.channels:
            if c.topic == str(interaction.user.id):
                await interaction.response.send_message(f"You already have an open mutation request: {c.mention}", ephemeral=True)
                return
        ch = await guild.create_text_channel(name=f"mutation-{interaction.user.name}", category=cat, overwrites=index_overwrites(guild, interaction.user), topic=str(interaction.user.id))
        embed = discord.Embed(color=0x2b2d31, title="🧬 Mutation Forge Request")
        embed.description = f"{interaction.user.mention}, your Mutation Forge request has been created!\n\n**Selected Service:** {forge}\n\nA mutation specialist will assist you shortly."
        embed.set_footer(text=FOOTER)
        pings = " ".join(f"<@&{rid}>" for rid in INDEX_CLAIM) + f" {interaction.user.mention}"
        view = IndexTicketView(creator=interaction.user.mention)
        await ch.send(content=pings, embed=embed, view=view)
        await interaction.response.send_message(f"Mutation request created: {ch.mention}", ephemeral=True)


class MutationForgeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MutationForgeSelect())


class ValuesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="SAB Values", style=discord.ButtonStyle.link, url="https://sabrvalues.com/", emoji="🌟"))
        self.add_item(discord.ui.Button(label="GAG Values", style=discord.ButtonStyle.link, url="https://www.growagardencalculator.com/grow-a-garden-2/", emoji="🌱"))
        self.add_item(discord.ui.Button(label="Elvebredd", style=discord.ButtonStyle.link, url="https://elvebredd.com/", emoji="🌿"))


class ReactionRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📢 Announcements Ping", style=discord.ButtonStyle.primary, custom_id="v:role_announcements", emoji="📢")
    async def announcements(self, interaction: discord.Interaction, btn: discord.ui.Button):
        role = interaction.guild.get_role(REACTION_ROLES["announcements"])
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed {role.name}", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Added {role.name}", ephemeral=True)

    @discord.ui.button(label="🔄 Update Ping", style=discord.ButtonStyle.success, custom_id="v:role_update", emoji="🔄")
    async def update(self, interaction: discord.Interaction, btn: discord.ui.Button):
        role = interaction.guild.get_role(REACTION_ROLES["update"])
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed {role.name}", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Added {role.name}", ephemeral=True)

    @discord.ui.button(label="⚡ Active Ping", style=discord.ButtonStyle.danger, custom_id="v:role_active", emoji="⚡")
    async def active(self, interaction: discord.Interaction, btn: discord.ui.Button):
        role = interaction.guild.get_role(REACTION_ROLES["active"])
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed {role.name}", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Added {role.name}", ephemeral=True)


class TradeView(discord.ui.View):
    def __init__(self, t1: int, t2: int, mm: int):
        super().__init__(timeout=None)
        self.t1 = t1
        self.t2 = t2
        self.mm = mm
        self.confirmed: set = set()
        b1 = discord.ui.Button(label="✅ Confirm Trade (Trader 1)", style=discord.ButtonStyle.success, custom_id=f"trade_t1_{t1}_{t2}")
        b2 = discord.ui.Button(label="✅ Confirm Trade (Trader 2)", style=discord.ButtonStyle.success, custom_id=f"trade_t2_{t1}_{t2}")
        b1.callback = self._confirm_t1
        b2.callback = self._confirm_t2
        self.add_item(b1)
        self.add_item(b2)

    async def _confirm_t1(self, interaction: discord.Interaction):
        if interaction.user.id != self.t1:
            await interaction.response.send_message("You are not Trader 1.", ephemeral=True)
            return
        self.confirmed.add(self.t1)
        await self._refresh(interaction)

    async def _confirm_t2(self, interaction: discord.Interaction):
        if interaction.user.id != self.t2:
            await interaction.response.send_message("You are not Trader 2.", ephemeral=True)
            return
        self.confirmed.add(self.t2)
        await self._refresh(interaction)

    async def _refresh(self, interaction: discord.Interaction):
        guild = interaction.guild
        m1 = guild.get_member(self.t1)
        m2 = guild.get_member(self.t2)
        mm = guild.get_member(self.mm)
        t1c = self.t1 in self.confirmed
        t2c = self.t2 in self.confirmed
        old = interaction.message.embeds[0]
        details = old.fields[0].value if old.fields else "—"

        if t1c and t2c:
            embed = discord.Embed(color=0x57f287, title="✅ Trade Confirmed")
            embed.description = "Both traders have confirmed. Please proceed with the rest of the trade."
            embed.add_field(name="🔵 Trader 1", value=m1.mention if m1 else str(self.t1), inline=True)
            embed.add_field(name="🔵 Trader 2", value=m2.mention if m2 else str(self.t2), inline=True)
            embed.add_field(name="🛡️ Middleman", value=mm.mention if mm else str(self.mm), inline=False)
            embed.add_field(name="✅ Status", value="Both traders confirmed", inline=False)
            embed.set_footer(text=FOOTER)
            for item in self.children:
                item.disabled = True
                item.label = "Trade Confirmed"
            active_trades.pop(interaction.message.id, None)
        else:
            t1d = "🟢" if t1c else "🔴"
            t2d = "🟢" if t2c else "🔴"
            embed = discord.Embed(color=0x2b2d31, title="✅ Trade Confirmation")
            embed.description = "In order to continue this trade, both traders should confirm the trade."
            embed.add_field(name="📊 Trade Information", value=details, inline=False)
            embed.add_field(name="🔵 Trader 1", value=m1.mention if m1 else str(self.t1), inline=True)
            embed.add_field(name="🔵 Trader 2", value=m2.mention if m2 else str(self.t2), inline=True)
            embed.add_field(name="🛡️ Middleman", value=mm.mention if mm else str(self.mm), inline=False)
            embed.add_field(name="⏳ Awaiting Confirmation", value=f"{t1d} {m1.mention if m1 else str(self.t1)}\n{t2d} {m2.mention if m2 else str(self.t2)}", inline=False)
            embed.set_footer(text=FOOTER)
            for item in self.children:
                if "t1" in item.custom_id and t1c:
                    item.label, item.disabled = "Confirmed (Trader 1)", True
                if "t2" in item.custom_id and t2c:
                    item.label, item.disabled = "Confirmed (Trader 2)", True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()


HITTER_ROLE_ID = 1472343485687267416

TRADE_LOG_CH = 1522750504650805308
TRADE_LOG_MEMBER_ROLE = 1472343485687267415
TRADE_LOG_MM_ROLE = 1472343485695918100

TRADE_OPTIONS = [
    "raccoon for 2 dragonflies",
    "2 dragonflies for raccoon",
    "unicorn for 2 dragon breath seeds",
    "2 dragon breath seeds for unicorn",
    "ghost pepper seed for ice serpent",
    "ice serpent for ghost pepper seed",
    "raccoon for dragonfly",
    "dragonfly for raccoon",
    "unicorn for dragon breath seed",
    "dragon breath seed for unicorn",
    "ice serpent for unicorn",
    "unicorn for ice serpent",
    "ghost pepper seed for dragon breath seeds",
    "dragon breath seeds for ghost pepper seed",
    "raccoon for unicorn",
    "unicorn for raccoon",
    "ice serpent for 2 dragonflies",
    "2 dragonflies for ice serpent",
    "ghost pepper seed for unicorn",
    "unicorn for ghost pepper seed",
    "dragonfly for dragon breath seed",
    "dragon breath seed for dragonfly",
    "ice serpent for dragon breath seeds",
    "dragon breath seeds for ice serpent",
]

FEE_OPTIONS = ["raccoon", "dragonfly", "unicorn", "dragon breath seed", "ghost pepper seed", "ice serpent"]


class MercyView(discord.ui.View):
    def __init__(self, target, author, message=None):
        super().__init__(timeout=60.0)
        self.target = target
        self.author = author
        self.message = message

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="v:mercy_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.target and interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ Only the targeted user can respond.", ephemeral=True)

        role = interaction.guild.get_role(HITTER_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)

        for child in self.children:
            child.disabled = True
            if child.label == "Accept":
                child.label = "Accepted"
            elif child.label == "Decline":
                child.label = "Declined"

        embed = discord.Embed(
            title="Opportunity Accepted",
            description=f"{interaction.user.mention} has accepted the opportunity and has been verified.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"{FOOTER} • Today at {discord.utils.utcnow().strftime('%I:%M %p')}")
        await interaction.message.edit(embed=embed, view=self)

        ghost_ch = interaction.guild.get_channel(1519445556764737577)
        if ghost_ch:
            ghost_msg = await ghost_ch.send(content=interaction.user.mention)
            try:
                await ghost_msg.delete()
            except discord.HTTPException:
                pass

        staff_ch = interaction.guild.get_channel(CH["staff_chat"])
        if staff_ch:
            staff_embed = discord.Embed(
                title="New Trader Joined!",
                description=(
                    f"Welcome {interaction.user.mention}\n\n"
                    "Make sure to stay locked in, read "
                    "https://discord.com/channels/1472343485687267408/1472343486824189954 , and ask others for "
                    "questions. If you need middleman you can earn it through "
                    "https://discord.com/channels/1472343485687267408/1472343487310725154\n"
                    "Any questions? Make a support ▶ "
                    "https://discord.com/channels/1472343485687267408/1519461568599822397"
                ),
                color=discord.Color.green()
            )
            staff_embed.set_footer(text=FOOTER)
            await staff_ch.send(embed=staff_embed)

        dm_embed = discord.Embed(
            title="💫 Hitting Tutorial",
            color=0x2b2d31
        )
        dm_embed.description = "You're a hitter now. A hitter is someone that got scammed by us, and goes out to scam others. In other words, you're now a scammer."
        dm_embed.add_field(
            name="❓ What should I do?",
            value=(
                "You need to go and advertise trades on other servers. "
                "Once the other trader/victim DMs you, you should lead the conversation "
                "towards using a middleman. Once they agree, you'll send them our server "
                "and create a ticket in <#1519421791167320166>. "
                "Once you create the ticket, a random middleman will come assist you."
            ),
            inline=False
        )
        try:
            await interaction.user.send(embed=dm_embed)
        except Exception:
            pass
        await interaction.response.defer()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, custom_id="v:mercy_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.target and interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ Only the targeted user can respond.", ephemeral=True)

        for child in self.children:
            child.disabled = True
            if child.label == "Accept":
                child.label = "Accepted"
            elif child.label == "Decline":
                child.label = "Declined"

        embed = discord.Embed(
            title="Opportunity Declined",
            description=f"{interaction.user.mention} has declined the opportunity.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"{FOOTER} • Today at {discord.utils.utcnow().strftime('%I:%M %p')}")
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()


@bot.tree.command(name="setupmiddleman", description="Post the MM request panel", guild=GUILD)
async def setup_mm(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="🛡️ Tsunami MM Services | Welcome to Our MM Service")
    embed.add_field(name="• Request Middleman", value="Read our mm-tos first, then tap Request Middleman and fill out the form.", inline=False)
    embed.add_field(name="• Vouch Required", value="You must vouch your middleman after the trade in #vouches. Failing to do so within 24 hours results in a Blacklist from our MM Service.", inline=False)
    embed.add_field(name="• Troll Tickets", value="Creating any form of troll tickets will result in a Middleman ban.", inline=False)
    embed.add_field(name="• Disclaimer", value="We are NOT responsible for anything that happens after the trade is done.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed, view=MMRequestView())
    await interaction.response.send_message("✅ MM panel deployed.", ephemeral=True)


@bot.tree.command(name="setupsupport", description="Post the Support request panel", guild=GUILD)
async def setup_support(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="🛡️ Tsunami MM Services | Support")
    embed.description = "Need help? Our support team is available 24/7 to assist you with any issues you may have.\n\nSimply click the Support button below to open a private ticket with our staff."
    embed.add_field(name="📋 When should I open a ticket?", value="• 🚨 Report a scammer\n• 🛡️ Report a Middleman\n• ❓ Need help creating a ticket\n• 💬 General questions or concerns\n• ⚠️ Dispute resolution\n• 🔒 Account or trade issues\n• 📢 Other", inline=False)
    embed.add_field(name="⚠️ Before You Open a Ticket", value="• Have all relevant screenshots or proof ready\n• Include the username of anyone involved\n• Be as detailed as possible — this helps us resolve your issue faster", inline=False)
    embed.add_field(name="⏱️ Response Time", value="Our staff aim to respond within a few minutes. Please be patient and do not open multiple tickets for the same issue.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed, view=SupportRequestView())
    await interaction.response.send_message("✅ Support panel deployed.", ephemeral=True)


@bot.tree.command(name="setupindex", description="Post the Index request panel", guild=GUILD)
async def setup_index(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="🧬 Tsunami MM Services | Mutation Service")
    embed.description = "Request a mutation service by selecting one of the available options.\nOne of our professional mutation specialists will assist you shortly! What does this mean? We grab THE BEST plants in the game, and farm THE best mutations on it. Im talking dragon breaths that sell for BILLIONS, Just make a ticket to learn more."
    embed.add_field(name="Available Mutations & Prices", value="🦄 Common Mutations(3-5 traits) — 1-2 Unicorns\n🦄 Rare Mutations(8-10 traits) — 2 Unicorns\n🐉 Epic Mutations(13-15 traits) — 1-2 Dragonflies\n🐉 Legendary Mutations(20 traits) — 2 Dragonflies\n🦝 Mythic Mutations(25 traits) — Raccoons (best tier)\n🐍 Highest Tier Mutations - Ice Serpents (30-40 traits)/premium mutations", inline=False)
    embed.add_field(name="Note", value="Collateral may be required, the price is negotiable.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed, view=MutationForgeView())
    await interaction.response.send_message("✅ Mutation panel deployed.", ephemeral=True)


@bot.tree.command(name="scamawareness", description="Post the Scam Awareness panel", guild=GUILD)
async def setup_scam_awareness(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="⚠️ Scam Awareness | Stay Safe", description="Protect yourself from scammers! Always follow these guidelines to ensure safe trading.")
    embed.add_field(name="🚨 Common Scam Methods", value="• Fake Middlemen: Scammers may impersonate our middlemen. Always verify through tickets!\n• Screen Sharing: NEVER screen share with anyone during a trade\n• QR Code Scams: Do not scan any QR codes sent by traders\n• Link Scams: Don't click suspicious links - they can steal your account\n• \"Trust Me\" Scams: If someone says \"trust me\" instead of using a MM, it's a red flag\n• Rushing: Scammers will try to rush you. Take your time!", inline=False)
    embed.add_field(name="🛡️ How to Stay Safe", value="✅ Always use our official Middleman service - Create a ticket in #request-mm\n✅ Verify middleman identity - Check their roles and verify through the ticket system\n✅ Never go first without a verified middleman present\n✅ Take screenshots of all conversations and trades\n✅ Check usernames carefully - Scammers use similar looking names\n✅ Report suspicious behavior immediately to staff", inline=False)
    embed.add_field(name="❌ Red Flags to Watch For", value="• Refusing to use a middleman\n• Offering deals that seem too good to be true\n• Asking you to trade outside of Discord\n• Pressure tactics or urgency\n• Newly created accounts with no history\n• Asking for personal information", inline=False)
    embed.add_field(name="📞 What to Do If Scammed", value="1. Do NOT delete any messages - Keep all evidence\n2. Open a support ticket immediately\n3. Provide screenshots of the entire conversation\n4. Include the scammer's username and ID\n5. Do not confront the scammer - Let staff handle it", inline=False)
    embed.add_field(name="💡 Remember", value="If it seems too good to be true, it probably is! Your safety is our priority. When in doubt, always use our middleman service.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Scam Awareness panel deployed.", ephemeral=True)


@bot.tree.command(name="about", description="Post information about Tsunami MM Services", guild=GUILD)
async def setup_about(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="🌊 About Tsunami MM Services", description="Your trusted partner for secure gaming trades!")
    embed.add_field(name="👑 Who We Are", value="Tsunami MM Services is a professional middleman service dedicated to providing secure, reliable, and fast trading experiences for gamers across multiple platforms. Our team of verified middlemen ensures that every trade is conducted safely.", inline=False)
    embed.add_field(name="🎯 Our Mission", value="To create a safe trading environment where players can conduct transactions without the fear of being scammed. We believe everyone deserves access to secure trading services.", inline=False)
    embed.add_field(name="📊 Our Stats", value="• 🛡️ 1000+ Successful Trades Completed\n• 👥 50+ Verified Middlemen\n• ⭐ 99.9% Success Rate\n• 🌍 24/7 Service Availability\n• 🎮 250+ Games Supported", inline=False)
    embed.add_field(name="🏆 What Makes Us Different", value="• Professional Staff: Rigorously vetted and trained middlemen\n• Fast Response Times: Average response under 5 minutes\n• Transparent Process: Full trade documentation and transcripts\n• Community Focused: Built by traders, for traders\n• Free Service: No hidden fees or charges", inline=False)
    embed.add_field(name="🔗 Our Services", value="• 🛡️ Middleman Service: Secure third-party trading\n• 🧬 Mutation Services: Professional mutation farming\n• 📞 Support: 24/7 assistance for all issues\n• 📊 Value Information: Access to multiple value databases", inline=False)
    embed.add_field(name="📞 Contact Us", value="• 💬 Open a support ticket for any questions\n• 📢 Follow announcements for updates\n• ⭐ Leave a vouch after successful trades", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ About panel deployed.", ephemeral=True)


@bot.tree.command(name="values", description="Post the Values panel with links to value sites", guild=GUILD)
async def setup_values(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="💎 Tsunami MM Services | Value Databases", description="Access the most accurate and up-to-date value information for your trades! Click the buttons below to visit our trusted value partner sites.")
    embed.add_field(name="🌟 SAB Values", value="Comprehensive value database with detailed pricing and rarity information.", inline=False)
    embed.add_field(name="🌱 GAG Values (Grow a Garden)", value="Specialized values for Grow a Garden 2 - mutations, plants, and more!", inline=False)
    embed.add_field(name="🌿 Elvebredd", value="Premium value site with extensive item databases and trade calculators.", inline=False)
    embed.add_field(name="💡 Pro Tip", value="Always check multiple value sources before making a trade to ensure you're getting the best deal!", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed, view=ValuesView())
    await interaction.response.send_message("✅ Values panel deployed.", ephemeral=True)


@bot.tree.command(name="reactionroles", description="Post the Reaction Roles panel", guild=GUILD)
async def setup_reaction_roles(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(color=0x2b2d31, title="🔔 Reaction Roles | Customize Your Experience", description="Click the buttons below to toggle roles and customize which notifications you receive! Click again to remove the role.")
    embed.add_field(name="📢 Announcements Ping", value="Get notified about important server announcements, updates, and news.", inline=False)
    embed.add_field(name="🔄 Update Ping", value="Receive pings when we post updates about services, features, or changes.", inline=False)
    embed.add_field(name="⚡ Active Ping", value="Get pinged for community events, giveaways, and active discussions.", inline=False)
    embed.add_field(name="💡 Note", value="You can toggle these roles on and off at any time by clicking the buttons again.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed, view=ReactionRolesView())
    await interaction.response.send_message("✅ Reaction Roles panel deployed.", ephemeral=True)


@bot.tree.command(name="add", description="Add a user to this ticket", guild=GUILD)
@app_commands.describe(user="User to add")
async def cmd_add(interaction: discord.Interaction, user: discord.Member):
    if not has_role(interaction.user, TICKET_STAFF):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    embed = discord.Embed(color=0x57f287, title="✅ User Added to Ticket")
    embed.description = f"{user.mention} has been added to this ticket by {interaction.user.mention}"
    embed.set_footer(text=FOOTER)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="close", description="Close this ticket", guild=GUILD)
async def cmd_close(interaction: discord.Interaction):
    await do_close(interaction)


@bot.tree.command(name="transfer", description="Transfer this ticket to another middleman", guild=GUILD)
@app_commands.describe(user="Middleman to transfer to")
async def cmd_transfer(interaction: discord.Interaction, user: discord.Member):
    if not has_role(interaction.user, TICKET_STAFF):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    ch = interaction.channel
    await ch.set_permissions(user, read_messages=True, send_messages=True)
    await ch.set_permissions(interaction.user, read_messages=True, send_messages=False)
    embed = discord.Embed(color=0x2b2d31, title="🔄 Ticket Transferred")
    embed.description = f"This ticket has been transferred to {user.mention}"
    embed.set_footer(text=FOOTER)
    await interaction.response.send_message(content=user.mention, embed=embed)


@bot.tree.command(name="confirm", description="Start a trade confirmation", guild=GUILD)
@app_commands.describe(trader1="First trader", trader2="Second trader", details="Trade details")
async def cmd_confirm(interaction: discord.Interaction, trader1: discord.Member, trader2: discord.Member, details: str):
    if not has_role(interaction.user, TICKET_STAFF):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    view = TradeView(t1=trader1.id, t2=trader2.id, mm=interaction.user.id)
    embed = discord.Embed(color=0x2b2d31, title="✅ Trade Confirmation")
    embed.description = "In order to continue this trade, both traders should confirm the trade."
    embed.add_field(name="📊 Trade Information", value=details, inline=False)
    embed.add_field(name="🔵 Trader 1", value=trader1.mention, inline=True)
    embed.add_field(name="🔵 Trader 2", value=trader2.mention, inline=True)
    embed.add_field(name="🛡️ Middleman", value=interaction.user.mention, inline=False)
    embed.add_field(name="⏳ Awaiting Confirmation", value=f"🔴 {trader1.mention}\n🔴 {trader2.mention}", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.response.send_message(content=f"{trader1.mention} {trader2.mention}", embed=embed, view=view)
    msg = await interaction.original_response()
    active_trades[msg.id] = view


@bot.tree.command(name="managerole", description="Promote or demote a user", guild=GUILD)
@app_commands.describe(action="add or remove", user="Target user", role="Role", reason="Reason")
@app_commands.choices(action=[app_commands.Choice(name="add", value="add"), app_commands.Choice(name="remove", value="remove")])
async def cmd_managerole(interaction: discord.Interaction, action: str, user: discord.Member, role: discord.Role, reason: str):
    if not can_manage_role(interaction.user, role.id):
        await interaction.response.send_message("You don't have permission to manage that role.", ephemeral=True)
        return
    if action == "add":
        await user.add_roles(role, reason=reason)
        title, color = "Role Given ✅", 0x57f287
    else:
        await user.remove_roles(role, reason=reason)
        title, color = "Role Removed ❌", 0xed4245
    embed = discord.Embed(color=color, title=title)
    embed.add_field(name="Actioned By", value=f"{interaction.user} ({interaction.user.id})", inline=False)
    embed.add_field(name="Target User", value=f"{user} ({user.id})", inline=False)
    embed.add_field(name="Role", value=role.name, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Time", value=ts_now(), inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.response.send_message(embed=embed)
    log_ch = interaction.guild.get_channel(CH["role_log"])
    if log_ch:
        await log_ch.send(embed=embed)


@bot.tree.command(name="manageban", description="Ban or unban a user", guild=GUILD)
@app_commands.describe(action="ban or unban", user="Target user", reason="Reason")
@app_commands.choices(action=[app_commands.Choice(name="ban", value="ban"), app_commands.Choice(name="unban", value="unban")])
async def cmd_manageban(interaction: discord.Interaction, action: str, user: discord.Member, reason: str):
    if not has_role(interaction.user, [ROLE["ban_perms"]]):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    now = datetime.datetime.utcnow()
    last = ban_cooldowns.get(interaction.user.id)
    if last and (now - last).total_seconds() < 3600:
        remaining = 3600 - int((now - last).total_seconds())
        mins, secs = divmod(remaining, 60)
        await interaction.response.send_message(f"⏳ You're on cooldown. Try again in {mins}m {secs}s.", ephemeral=True)
        return
    ban_cooldowns[interaction.user.id] = now
    roles_owned = [r.name for r in user.roles if r.name != "@everyone"]
    if action == "ban":
        await user.ban(reason=reason)
        title, color = "User Banned 🚫", 0xed4245
    else:
        await interaction.guild.unban(discord.Object(id=user.id), reason=reason)
        title, color = "User Unbanned ✅", 0x57f287
    embed = discord.Embed(color=color, title=title)
    embed.add_field(name="Actioned By", value=f"{interaction.user} ({interaction.user.id})", inline=False)
    embed.add_field(name="Target User", value=f"{user} ({user.id})", inline=False)
    embed.add_field(name="Roles Owned", value=", ".join(roles_owned) if roles_owned else "None", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Time", value=ts_now(), inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.response.send_message(embed=embed)
    log_ch = interaction.guild.get_channel(CH["ban_log"])
    if log_ch:
        await log_ch.send(embed=embed)


@bot.tree.command(name="dm", description="DM every member with a given role", guild=GUILD)
@app_commands.describe(role="Role to DM", message="Message to send")
async def cmd_dm(interaction: discord.Interaction, role: discord.Role, message: str):
    if not has_role(interaction.user, ADMIN_ROLES):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    members = [m for m in role.members if not m.bot]
    sent = 0
    failed = 0

    embed = discord.Embed(color=0x2b2d31, title=f"📨 Message from {interaction.guild.name}")
    embed.description = message
    embed.set_footer(text=FOOTER)

    for member in members:
        try:
            await member.send(embed=embed)
            sent += 1
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException:
            failed += 1

    await interaction.followup.send(
        content=f"✅ Sent to {sent} member(s) with the **{role.name}** role. {f'❌ Failed for {failed}.' if failed else ''}",
        ephemeral=True
    )


@bot.tree.command(name="sendproof", description="Manually post a trade log now", guild=GUILD)
async def cmd_sendproof(interaction: discord.Interaction):
    if not any(r.id == 1472343485721083915 for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    success = await send_trade_log(interaction.guild)

    if success:
        await interaction.followup.send("✅ Trade log posted.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Couldn't post — not enough eligible members, or the channel/roles weren't found.", ephemeral=True)


@bot.tree.command(name="rules", description="Display Tsunami MM Services Rules", guild=GUILD)
async def cmd_rules(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(title="📋 Tsunami MM Services | Rules & Guidelines", color=0x2b2d31)
    embed.add_field(name="1. 📜 Follow Discord ToS and Guidelines", value="We're on Discord's platform, therefore we'll automatically follow their regulations. Make sure you don't violate their terms and guidelines.", inline=False)
    embed.add_field(name="2. 🔒 Personal Information", value="Do not post personal information about anyone without their consent. Any impersonation within MMs or other members are also not allowed.", inline=False)
    embed.add_field(name="3. ✅ Content Appropriate", value="All content should be safe for work and appropriate for the server's community. No NSFW, graphic, or disturbing content.", inline=False)
    embed.add_field(name="4. 📌 Use the Correct Channels", value="Post messages, images, and discussions in the appropriate channels. Read channel descriptions and rules to avoid clutter.", inline=False)
    embed.add_field(name="5. 🚫 No Illegal Activities", value="Sharing, discussing, or promoting illegal activities is strictly prohibited. This includes piracy, hacking, and any other form of illegal behavior.", inline=False)
    embed.add_field(name="6. 🔐 Respect Privacy", value="Do not share personal information (yours or others') without consent. Respect everyone's privacy.", inline=False)
    embed.add_field(name="7. 🎭 No Impersonation", value="Do not impersonate other members, including server staff, celebrities, or other users.", inline=False)
    embed.add_field(name="8. 💬 Follow Discord's Terms of Service", value="All members must adhere to Discord's Terms of Service and Community Guidelines. https://discord.com/terms", inline=False)
    embed.add_field(name="9. 👂 Listen to Staff", value="Staff decisions are final. If you have issues or concerns, contact a staff member privately and respectfully.", inline=False)
    embed.add_field(name="10. ⚠️ We Are NOT Responsible", value="We are not responsible when one of our server ad buyers scams you and when one of our server ad buyers scams you, this means that going first in one of theirs trades is YOUR OWN RISK! If you get scammed by one of them DM an owner and we will take the ad down as fast as possible.", inline=False)
    embed.add_field(name="11. 📢 Server Ads", value="We do NOT refund purchased server ads, breaking the server's rules and getting banned will lead to an ad remove with no refunds.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Done.", ephemeral=True)


@bot.tree.command(name="middleman", description="Explains how the middleman service works", guild=GUILD)
async def cmd_middleman(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🛡️ What is a Middleman?",
        description="A **Middleman** is a trusted person who sits in the middle of a trade so nobody gets scammed. Think of it like this: instead of trading directly with a stranger, you both trade through someone you can trust instead.",
        color=0x2b2d31
    )

    embed.add_field(
        name="\u200b",
        value="━━━━━━━━━━━━━━━━━━━━",
        inline=False
    )

    embed.add_field(
        name="❓ Why do I need one?",
        value=(
            "When you trade with someone you don't know, one of you has to go first.\n\n"
            "If you go first, they can just take your stuff and leave.\n"
            "If they go first, they might think the same about you.\n\n"
            "A Middleman fixes this problem completely."
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ How does it actually work?",
        value=(
            "1️⃣ **Both traders send their item to the Middleman first** — nobody sends directly to each other\n\n"
            "2️⃣ **The Middleman now holds both items** — so neither trader can be scammed\n\n"
            "3️⃣ **The Middleman checks everything is correct**\n\n"
            "4️⃣ **The Middleman sends each item to the right trader** — Trader A gets what Trader B sent, and Trader B gets what Trader A sent\n\n"
            "✅ **Done!** Both traders got what they wanted, and nobody could get scammed"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ What do I need to do?",
        value=(
            "• Be patient, a Middleman will be with you shortly\n"
            "• Don't send anything until the Middleman tells you to\n"
            "• Listen to what the Middleman says\n"
            "• Vouch for your Middleman after the trade in #vouches"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 Does it cost anything?",
        value="No. Our Middleman service is **completely free**.",
        inline=False
    )

    embed.add_field(
        name="🚀 Ready to trade safely?",
        value="Open a ticket in <#1519421791167320166> and a Middleman will be with you shortly!",
        inline=False
    )

    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Done.", ephemeral=True)


@bot.tree.command(name="faq", description="Frequently Asked Questions", guild=GUILD)
async def cmd_faq(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(title="🛡️ Tsunami MM Services | FAQ", color=0x2b2d31)
    embed.add_field(name="What is Tsunami MM Services?", value="Tsunami MM Services is a platform that provides a secure player-to-player marketplace for buyers and sellers of online gaming products. We provide a system for secure transactions — you do the rest. We have marketplaces for 250+ games and leading titles!", inline=False)
    embed.add_field(name="How does the Middleman service work?", value="Our verified Middlemen act as trusted third parties to hold and transfer items/funds during a trade. This ensures both parties are protected throughout the entire deal.", inline=False)
    embed.add_field(name="Is it free to use?", value="Yes! Our Middleman service is completely free for standard trades. Simply open a ticket and request a Middleman.", inline=False)
    embed.add_field(name="How long does a trade take?", value="Most trades are completed within minutes. Our Middlemen are available 24/7 to assist you as quickly as possible.", inline=False)
    embed.add_field(name="What if something goes wrong?", value="Our team monitors every trade. If any issues arise, open a support ticket and our staff will investigate and resolve the matter promptly.", inline=False)
    embed.add_field(name="Where can I report a scammer?", value="Open a support ticket and provide all relevant proof. Our team will handle the report and take appropriate action.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Done.", ephemeral=True)


@bot.tree.command(name="tos", description="Tsunami MM Services Trading Terms of Service", guild=GUILD)
async def cmd_tos(interaction: discord.Interaction):
    if not any(r.id == SETUP_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    embed = discord.Embed(title="🚀 Trading Terms of Service", color=0x2b2d31)
    embed.add_field(name="1. Cross-Trading", value="Cross-trading is only allowed with server-approved middlemen. Violations will result in a warning. (3 warnings = mute)", inline=False)
    embed.add_field(name="2. Prohibited Statements", value="Statements like 'mm of my choice' or 'ngl' are not allowed during cross-trading and will result in warnings. (3 warnings = mute, further violations = ban)", inline=False)
    embed.add_field(name="3. Trading Locations", value="Cross-trading is only permitted in the #marketplace and #verified-market channels.", inline=False)
    embed.add_field(name="4. Middleman Violations", value="Suggesting a scam middleman or refusing to use trusted middlemen will result in an instant ban. If you find someone suggesting a scam server, please report them immediately in #support.", inline=False)
    embed.add_field(name="5. Illegal Trading", value="Trading illegal items is strictly prohibited and will result in an instant ban. This includes trading Discord Nitro, accounts, selling scripts or cheats for games, or anything else that violates Discord's Terms of Service.", inline=False)
    embed.add_field(name="6. Middleman Usage", value="Always use a middleman when you do a cross-trade, and ensure you follow our middleman TOS. Failure to comply may result in penalties. To use middle man go to the channel #request-mm.", inline=False)
    embed.add_field(name="7. Respectful Trading", value="Be kind and respectful towards all traders, especially new ones. Rude or toxic behavior may lead to warnings or bans.", inline=False)
    embed.set_footer(text=FOOTER)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Done.", ephemeral=True)


temp_removed: dict = {}


@bot.tree.command(name="temp", description="Toggle your hierarchy roles on/off", guild=GUILD)
async def cmd_temp(interaction: discord.Interaction):
    member = interaction.user
    user_roles = [r.id for r in member.roles]

    if member.id in temp_removed:
        stored = temp_removed.pop(member.id)
        added = []
        for rid in stored:
            role = interaction.guild.get_role(rid)
            if role:
                await member.add_roles(role, reason="/temp restore")
                added.append(role.mention)
        await interaction.response.send_message(
            f"✅ Restored your roles: {', '.join(added)}" if added else "✅ No roles to restore.",
            ephemeral=True
        )
    else:
        to_remove = [rid for rid in HIERARCHY_IDS if rid in user_roles]
        if not to_remove:
            await interaction.response.send_message("You don't have any hierarchy roles to remove.", ephemeral=True)
            return
        temp_removed[member.id] = to_remove
        removed = []
        for rid in to_remove:
            role = interaction.guild.get_role(rid)
            if role:
                await member.remove_roles(role, reason="/temp hide")
                removed.append(role.mention)
        await interaction.response.send_message(
            f"✅ Temporarily removed: {', '.join(removed)}\nRun **/temp** again to get them back.",
            ephemeral=True
        )


@bot.tree.command(name="fill", description="Fill all hierarchy roles from your highest down to Trial Middleman", guild=GUILD)
@app_commands.describe(user="User to fill roles for")
async def cmd_fill(interaction: discord.Interaction, user: discord.Member):
    if not has_role(interaction.user, [ROLE["president"], ROLE["head_of_security"]]):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    await interaction.response.defer()
    user_role_ids = [r.id for r in user.roles]

    highest_idx = -1
    for i, rid in enumerate(HIERARCHY_IDS):
        if rid in user_role_ids:
            highest_idx = i

    if highest_idx == -1:
        await interaction.followup.send(content="That user doesn't have any hierarchy roles.")
        return

    added = []
    for rid in HIERARCHY_IDS[:highest_idx + 1]:
        if rid not in user_role_ids:
            role = interaction.guild.get_role(rid)
            if role:
                await user.add_roles(role, reason="/fill")
                added.append(role.mention)

    if added:
        await interaction.followup.send(
            content=f"✅ Filled in missing roles for {user.mention}: {', '.join(added)}")
    else:
        await interaction.followup.send(
            content=f"✅ {user.mention} already has all roles up to their highest!")


@bot.tree.command(name="mercy", description="Offer a mercy opportunity to a user", guild=GUILD)
@app_commands.describe(user="User to offer mercy to")
async def cmd_mercy(interaction: discord.Interaction, user: discord.Member):
    if not any(r.id in (1472343485721083915, 1472343485695918100) for r in interaction.user.roles):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    embed = discord.Embed(
        color=0x2b2d31,
        title="⚠️ Scam Notification",
        description=(
            "If you're seeing this, you've likely just been scammed — but this doesn't end how you think.\n\n"
            "Most people in this server started out the same way. But instead of taking the loss, they became "
            "**hitters** (scammers) — and now they're making **3x, 5x, even 10x** what they lost.\n\n"
            "This is your chance to turn a setback into serious profit.\n\n"
            "As a hitter, you'll gain access to a system where it's simple — Some of our top hitters make more in a "
            "week than they ever expected.\n\n"
            "**You now have access to the staff chat and other hitter channels.** Head to the main guide channel to "
            "learn how to start.\n\n"
            "🚨 Every minute you wait is profit missed.\n\n"
            "Need help getting started? Ask in the support system channel.\n\n"
            "You've already been pulled in — now it's time to flip the script and come out ahead."
        )
    )
    embed.set_footer(text=FOOTER)

    prompt_embed = discord.Embed(
        color=0x2b2d31,
        description=f"{user.mention}, do you want to accept this opportunity and become a hitter?\n\n⏳ You have **1 minute** to respond. The decision is yours. Make it count."
    )
    prompt_embed.set_footer(text=FOOTER)

    view = MercyView(target=user, author=interaction.user)
    msg = await interaction.channel.send(content=user.mention, embeds=[embed, prompt_embed], view=view)
    view.message = msg
    await interaction.response.send_message("✅ Mercy opportunity sent.", ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
