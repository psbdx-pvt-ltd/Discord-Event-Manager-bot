import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import datetime
import re
import asyncio
from aiohttp import web
from typing import List, Optional, Union
from io import BytesIO

# --- CONFIGURATION & ENV ---
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERROR: 'DISCORD_TOKEN' environment variable is missing!")

ADM_ID = int(os.getenv("ADM_ID", "0"))
SRCE_CHNL = int(os.getenv("SRCE_CHNL", "0"))
EVNT_CHNL = int(os.getenv("EVNT_CHNL", "0"))
USE_DISCORD_STORAGE = os.getenv("USE_DISCORD_STORAGE", "False").lower() == "true"

# --- WEB SERVER FOR CRONJOB ---
async def handle_home(request):
    return web.Response(text="Bot is alive! Ready for cronjobs.")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_home)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web server started on port 8080")

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- STORAGE HANDLERS ---
async def save_event_data(ctx_or_interaction, data):
    """Saves event data to Discord channel or local file."""
    json_data = json.dumps(data, indent=4)
    
    if USE_DISCORD_STORAGE:
        try:
            channel = bot.get_channel(SRCE_CHNL)
            if not channel:
                channel = await bot.fetch_channel(SRCE_CHNL)
            
            if not channel:
                print(f"❌ Storage Error: Could not find channel ID {SRCE_CHNL}")
                return False

            file_data = BytesIO(json_data.encode('utf-8'))
            await channel.send(
                content=f"EVENT_DB_UPDATE: {datetime.datetime.now()}",
                file=discord.File(file_data, filename="current_event.json")
            )
            return True
        except discord.Forbidden:
            print("❌ Storage Error: Bot permissions missing in SRCE_CHNL.")
            return False
        except Exception as e:
            print(f"❌ Storage Error: {e}")
            return False
    else:
        try:
            with open("current_event.json", "w") as f:
                f.write(json_data)
            return True
        except Exception as e:
            print(f"❌ Local Storage Error: {e}")
            return False

async def get_event_data():
    if USE_DISCORD_STORAGE:
        try:
            channel = bot.get_channel(SRCE_CHNL)
            if not channel:
                channel = await bot.fetch_channel(SRCE_CHNL)
            
            messages = [message async for message in channel.history(limit=1)]
            if not messages:
                return None
            
            last_msg = messages[0]
            if last_msg.attachments:
                file_bytes = await last_msg.attachments[0].read()
                return json.loads(file_bytes.decode('utf-8'))
            else:
                return None
        except Exception as e:
            print(f"❌ Read Error: {e}")
            return None
    else:
        if not os.path.exists("current_event.json"):
            return None
        try:
            with open("current_event.json", "r") as f:
                return json.load(f)
        except:
            return None

# --- UI COMPONENTS ---

class EventSetupModal(discord.ui.Modal, title="Create New Event"):
    name = discord.ui.TextInput(label="Event Name", required=True)
    end_date = discord.ui.TextInput(
        label="End Date (YYYY-MM-DD)", 
        placeholder="2025-12-31", 
        required=True,
        min_length=10, max_length=10
    )
    banner_url = discord.ui.TextInput(
        label="Banner Image URL (Optional)", 
        required=False,
        placeholder="https://imgur.com/..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            datetime.datetime.strptime(self.end_date.value, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format.", ephemeral=True)
            return

        event_data = {
            "name": self.name.value,
            "end_date": self.end_date.value,
            "banner": self.banner_url.value,
            "fields": []
        }
        
        view = FieldSetupView(event_data)
        await interaction.response.send_message(
            f"Event '{self.name.value}' initialized.\nNow, add questions (Max 10).", 
            view=view, 
            ephemeral=True
        )

class FieldSetupView(discord.ui.View):
    def __init__(self, event_data):
        super().__init__(timeout=600)
        self.event_data = event_data

    def update_embed(self):
        embed = discord.Embed(title=f"Setup: {self.event_data['name']}", color=discord.Color.blue())
        embed.add_field(name="End Date", value=self.event_data['end_date'])
        
        fields_desc = ""
        for i, field in enumerate(self.event_data['fields']):
            req = "*(Required)*" if field['required'] else "(Optional)"
            fields_desc += f"**{i+1}. {field['question']}** [{field['type']}] {req}\n"
        
        if not fields_desc:
            fields_desc = "No fields added yet."
        
        embed.description = fields_desc
        return embed

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.green)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.event_data['fields']) >= 10:
            await interaction.response.send_message("Maximum 10 fields allowed!", ephemeral=True)
            return
        await interaction.response.send_modal(AddFieldModal(self))

    @discord.ui.button(label="Finish & Save", style=discord.ButtonStyle.blurple)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        success = await save_event_data(interaction, self.event_data)
        if success:
            await interaction.followup.send("✅ Event saved and published!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error saving event.", ephemeral=True)

class AddFieldModal(discord.ui.Modal, title="Add a Question"):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    question = discord.ui.TextInput(label="Question/Prompt", required=True)
    field_type = discord.ui.TextInput(
        label="Type (text, number, email, img, video, pdf)", 
        placeholder="text", 
        required=True
    )
    required = discord.ui.TextInput(
        label="Is Required? (yes/no)", 
        placeholder="yes", 
        required=True,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        ftype = self.field_type.value.lower()
        if any(x in ftype for x in ["img", "image", "photo"]): ftype = "img"
        elif any(x in ftype for x in ["vid", "video"]): ftype = "video"
        elif "pdf" in ftype: ftype = "pdf"
        elif "num" in ftype: ftype = "number"
        elif "mail" in ftype: ftype = "email"
        else: ftype = "text"

        is_req = self.required.value.lower() in ['yes', 'y', 'true', '1']

        self.parent_view.event_data['fields'].append({
            "question": self.question.value,
            "type": ftype,
            "required": is_req
        })
        
        await interaction.response.edit_message(embed=self.parent_view.update_embed(), view=self.parent_view)

# --- USER INTERACTION FLOW ---

class EventSubmissionHandler:
    def __init__(self, user, event_data, bot, thread):
        self.user = user
        self.event_data = event_data
        self.bot = bot
        self.thread = thread
        self.answers = []
        self.current_step = 0

    async def start(self):
        await self.thread.send(f"👋 Hello {self.user.mention}! Welcome to **{self.event_data['name']}**.\nI'll ask questions here. Only you and admins can see this.")
        await self.ask_question()

    async def ask_question(self):
        if self.current_step >= len(self.event_data['fields']):
            await self.finish_submission()
            return

        field = self.event_data['fields'][self.current_step]
        prompt = f"**Question {self.current_step + 1}/{len(self.event_data['fields'])}:**\n{field['question']}"
        
        if field['required']:
            prompt += " *(Required)*"
        else:
            prompt += " *(Type 'skip' to skip)*"

        if field['type'] == 'img': prompt += "\n🖼️ **Upload an Image (PNG/JPG).**"
        elif field['type'] == 'video': prompt += "\n🎥 **Upload a Video (MP4/MOV).**"
        elif field['type'] == 'pdf': prompt += "\n📄 **Upload a PDF.**"
        
        await self.thread.send(prompt)

        def check(m):
            return m.author.id == self.user.id and m.channel.id == self.thread.id

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=600.0)
            
            if not field['required'] and msg.content.lower() == 'skip' and not msg.attachments:
                self.answers.append({"q": field['question'], "a": "Skipped"})
                self.current_step += 1
                await self.ask_question()
                return

            answer = ""
            if field['type'] in ['img', 'video', 'pdf']:
                if msg.attachments:
                    att = msg.attachments[0]
                    valid = True
                    if field['type'] == 'img' and not att.content_type.startswith('image/'): valid = False
                    if field['type'] == 'video' and not att.content_type.startswith('video/'): valid = False
                    if field['type'] == 'pdf' and 'pdf' not in att.content_type: valid = False
                    
                    if not valid and field['required']:
                        await self.thread.send("⚠️ **Incorrect file type.** Try again.")
                        await self.ask_question()
                        return
                    answer = att.url 
                elif field['required']:
                    await self.thread.send("⚠️ **No file detected.** Please upload.")
                    await self.ask_question()
                    return
                else:
                    answer = msg.content
            
            elif field['type'] == 'email':
                if not re.match(r"[^@]+@[^@]+\.[^@]+", msg.content):
                    await self.thread.send("⚠️ Invalid email format.")
                    await self.ask_question()
                    return
                answer = msg.content
            elif field['type'] == 'number':
                if not msg.content.isdigit():
                    await self.thread.send("⚠️ Please enter a number.")
                    await self.ask_question()
                    return
                answer = msg.content
            else:
                answer = msg.content

            self.answers.append({"q": field['question'], "a": answer})
            self.current_step += 1
            await self.ask_question()

        except asyncio.TimeoutError:
            await self.thread.send("❌ Timeout. Run `/join` again.")

    async def finish_submission(self):
        await self.thread.send("✅ **Submission Received!** Closing this thread shortly.")
        
        channel = self.bot.get_channel(EVNT_CHNL)
        if channel:
            # 1. Create the base Embed
            embed = discord.Embed(
                title=f"New Participant: {self.event_data['name']}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.set_author(name=self.user.display_name, icon_url=self.user.avatar.url if self.user.avatar else None)
            
            file_urls = []
            image_set_in_embed = False

            # 2. Sort answers into Embed Fields or File Lists
            for item in self.answers:
                val = str(item['a'])
                
                # Check if it's a URL from Discord CDN
                if "cdn.discordapp.com" in val or "media.discordapp.net" in val:
                    # It's a file
                    file_urls.append(val)
                    embed.add_field(name=item['q'], value="*(See attachment below)*", inline=False)
                    
                    # If it's an image and we haven't set the main embed image yet, do it!
                    is_image = any(ext in val.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif'])
                    if is_image and not image_set_in_embed:
                        embed.set_image(url=val)
                        image_set_in_embed = True
                else:
                    # It's text
                    embed.add_field(name=item['q'], value=val, inline=False)
            
            # 3. Send the Embed First
            await channel.send(content=f"🎉 {self.user.mention} has joined the event!", embed=embed)

            # 4. Send remaining files as separate links (Discord auto-previews them)
            if file_urls:
                for url in file_urls:
                    # Don't re-send the main image if it's already big in the embed
                    if image_set_in_embed and url == embed.image.url:
                        continue 
                    await channel.send(content=f"📎 **Attachment:** {url}")

        # Archive Thread
        try:
            await self.thread.edit(locked=True, archived=True)
        except:
            pass

# --- COMMANDS ---

@bot.tree.command(name="new_event", description="Create a new event (Admin Only)")
async def new_event(interaction: discord.Interaction):
    if interaction.user.id != ADM_ID:
        await interaction.response.send_message("⛔ Not authorized.", ephemeral=True)
        return
    await interaction.response.send_modal(EventSetupModal())

@bot.tree.command(name="join", description="Join the latest event")
async def join_event(interaction: discord.Interaction):
    data = await get_event_data()
    if not data:
        await interaction.response.send_message("📭 No active events.", ephemeral=True)
        return

    end_date = datetime.datetime.strptime(data['end_date'], "%Y-%m-%d")
    if datetime.datetime.now() > end_date:
        await interaction.response.send_message(f"🔒 Event ended.", ephemeral=True)
        return

    try:
        thread_name = f"apply-{interaction.user.name}"
        thread = await interaction.channel.create_thread(
            name=thread_name,
            auto_archive_duration=60,
            type=discord.ChannelType.private_thread
        )
        await thread.add_user(interaction.user)
        await interaction.response.send_message(f"📩 Application opened: {thread.mention}", ephemeral=True)
        
        handler = EventSubmissionHandler(interaction.user, data, bot, thread)
        await handler.start()

    except discord.Forbidden:
        await interaction.response.send_message("❌ **Permission Error**: I need 'Create Private Threads' permission.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="about", description="Bot Information")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(title="About This Bot", color=discord.Color.gold())
    embed.add_field(name="Package Name", value="Discord Event Manager", inline=False)
    embed.add_field(name="Version", value="1.3 (Media Fix)", inline=False)
    embed.add_field(name="License", value="Open Source", inline=False)
    embed.add_field(name="Developed by", value="PSBDx", inline=False)
    embed.set_footer(text="Render Friendly & Cornjob Compatible")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands')
    except Exception as e:
        print(f"Error syncing commands: {e}")
    bot.loop.create_task(start_server())

if TOKEN:
    bot.run(TOKEN)
