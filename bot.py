import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 🧠 Хранилище ролей
role_storage = {}

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ==================== UI ====================
class RoleSelect(discord.ui.Select):
    def __init__(self, guild_id: int):
        roles = role_storage.get(guild_id, {})
        options = [
            discord.SelectOption(label=role_name, description=f"Выдать или убрать роль {role_name}")
            for role_name in roles.keys()
        ]

        super().__init__(
            placeholder="🎭 Выбери одну или несколько ролей (повторное нажатие — снять)",
            min_values=1,
            max_values=len(options),
            options=options
        )

        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        guild_roles = role_storage.get(self.guild_id, {})
        bot_member = interaction.guild.me

        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message("🚫 У меня нет права **управлять ролями**.", ephemeral=True)
            return

        added_roles = []
        removed_roles = []

        for role_name in self.values:
            role_id = guild_roles.get(role_name)
            role = interaction.guild.get_role(role_id)

            if not role:
                continue
            if role >= bot_member.top_role:
                continue

            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                removed_roles.append(role_name)
            else:
                await interaction.user.add_roles(role)
                added_roles.append(role_name)

        # Формируем сообщение с результатом
        result_parts = []
        if added_roles:
            result_parts.append("✅ Выданы роли: " + ", ".join(f"**{r}**" for r in added_roles))
        if removed_roles:
            result_parts.append("🔻 Сняты роли: " + ", ".join(f"**{r}**" for r in removed_roles))
        if not result_parts:
            result_parts.append("⚠️ Не удалось изменить роли (возможно, они выше моей роли).")

        # 🔁 Пересоздаём меню, чтобы можно было снова выбирать
        view = RoleSelectView(self.guild_id)
        await interaction.response.edit_message(content="\n".join(result_parts) + "\n🎭 Выбери роли:", view=view)


class RoleSelectView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(guild_id))


# ==================== СОБЫТИЯ ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Бот {bot.user} запущен!")
    print("Slash-команды синхронизированы для всех серверов.")


# ==================== КОМАНДЫ ====================

@bot.tree.command(name="addrole", description="Добавить роль в меню выбора (по ID)")
@app_commands.describe(role_id="ID роли, которую нужно добавить")
async def cmd_add_role(interaction: discord.Interaction, role_id: str):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("🚫 У тебя нет прав для этой команды.", ephemeral=True)
        return

    guild = interaction.guild
    role = guild.get_role(int(role_id))
    if not role:
        await interaction.response.send_message("❌ Роль с таким ID не найдена.", ephemeral=True)
        return

    if guild.id not in role_storage:
        role_storage[guild.id] = {}

    role_storage[guild.id][role.name] = role.id
    await interaction.response.send_message(f"✅ Роль **{role.name}** добавлена в меню!", ephemeral=True)


@bot.tree.command(name="createmenu", description="Создать меню выбора ролей")
async def cmd_create_menu(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("🚫 У тебя нет прав для этой команды.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    if guild_id not in role_storage or not role_storage[guild_id]:
        await interaction.response.send_message("⚠️ Нет добавленных ролей. Используй `/addrole <id>`.", ephemeral=True)
        return

    view = RoleSelectView(guild_id)
    await interaction.response.send_message("🎭 Выбери себе роли из списка ниже:", view=view)


# ==================== ЗАПУСК ====================
bot.run(TOKEN)
