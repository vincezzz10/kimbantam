import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import yt_dlp
import datetime  # <- 추가

intents = discord.Intents.default()
intents.message_content = True

# command_prefix를 반드시 넣어야 합니다. 멘션으로도 호출 가능하게 설정.
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

# ----- 봇 시작 -----
@bot.event
async def on_ready():
    # 서버에 명령어 등록(sync)
    await bot.tree.sync()
    print(f"✅ 봇 준비 완료: {bot.user} (ID: {bot.user.id})")

# ----- 리마인드 -----
@bot.tree.command(name="리마인드", description="몇 분 후에 할 일을 알려줍니다.")
@app_commands.describe(시간="몇 분 후에 알림을 줄까요?", 내용="알림 내용")
async def 리마인드(interaction: discord.Interaction, 시간: int, 내용: str):
    await interaction.response.send_message(f"{시간}분 후에 '{내용}' 알려드릴게요!")
    await asyncio.sleep(시간 * 60)
    await interaction.followup.send(f"⏰ {interaction.user.mention}, 지금 '{내용}' 할 시간이야!")

# ----- 운세 -----
@bot.tree.command(name="운세", description="오늘의 운세를 알려줍니다.")
async def 운세(interaction: discord.Interaction):
    운세리스트 = [
        "🌞 오늘은 좋은 일이 있을 거예요!",
        "🌧 약간 우울할 수도 있지만, 극복할 수 있어요.",
        "🍀 행운의 날! 도전해보세요.",
        "🌀 조심하세요! 뜻밖의 변수에 대비를.",
        "🔥 열정 가득! 하고 싶은 걸 해보세요.",
        "😴 쉬는 것도 필요해요. 무리하지 마세요.",
        "📚 배움의 기회! 오늘은 공부에 집중!"
    ]
    운세_결과 = random.choice(운세리스트)
    await interaction.response.send_message(f"{interaction.user.mention}의 오늘의 운세:\n{운세_결과}")

# ----- 욕설 필터링 -----
욕설_목록 = ["씨발", "시발", "개새끼", "애미", "뒤져", "운지", "섹스", "미친새끼", "지랄", "ㅈㄹ", "ㅅㅂ", "ㅇㅁ", "ㅇㅂ", "ㅅㅅ"]

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content_lower = message.content.lower()
    for 욕 in 욕설_목록:
        if 욕 in content_lower:
            try:
                await message.delete()
            except Exception:
                pass

            embed = discord.Embed(
                title="🚫 경고: 부적절한 언어 사용",
                description=f"{message.author.mention}, 욕설은 사용하실 수 없습니다.",
                color=discord.Color.red()
            )
            embed.set_footer(text="서버 규칙을 지켜주세요!")
            await message.channel.send(embed=embed)
            return

    # (중요) 메시지 기반 명령어를 쓰려면 process_commands 호출 유지
    await bot.process_commands(message)

# ----- 역할 자동 부여 -----
@bot.tree.command(name="가입", description="멤버 역할을 부여합니다.")
async def 가입(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("서버(길드)에서만 사용하세요.", ephemeral=True)
        return

    역할 = discord.utils.get(interaction.guild.roles, name="멤버")
    if not 역할:
        await interaction.response.send_message("서버에 '멤버' 역할이 없어요. 먼저 만들어주세요.", ephemeral=True)
        return

    # interaction.user는 길드에서 Member일 가능성이 높지만 안전하게 처리
    member = interaction.guild.get_member(interaction.user.id) or interaction.user
    try:
        await member.add_roles(역할)
        await interaction.response.send_message(f"{member.mention}님, 멤버 역할이 부여되었어요!")
    except Exception as e:
        await interaction.response.send_message(f"역할 부여 실패: {e}", ephemeral=True)

# ----- 보안 기능 -----
경고_데이터 = {}

@bot.tree.command(name="경고", description="대상에게 경고를 부여합니다.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(대상="경고를 줄 대상", 이유="경고 사유")
async def 경고(interaction: discord.Interaction, 대상: discord.Member, 이유: str = "이유 없음"):
    if 대상.bot:
        await interaction.response.send_message("봇에게는 경고를 줄 수 없어요.", ephemeral=True)
        return

    uid = str(대상.id)
    경고_데이터[uid] = 경고_데이터.get(uid, 0) + 1
    await interaction.response.send_message(f"{대상.mention}님에게 경고를 부여했어요. (총 {경고_데이터[uid]}회)\n이유: {이유}")

    if 경고_데이터[uid] >= 3:
        try:
            duration = 600
            # datetime.timedelta 사용
            await 대상.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=duration), reason="경고 3회 누적")
            await interaction.followup.send(f"{대상.mention}님이 경고 3회 누적으로 10분간 타임아웃 처리됐어요. ⏱")
            경고_데이터[uid] = 0
        except Exception as e:
            await interaction.followup.send(f"⚠ 타임아웃 실패: {e}")

@bot.tree.command(name="경고확인", description="대상의 경고 횟수를 확인합니다.")
@app_commands.checks.has_permissions(manage_messages=True)
async def 경고확인(interaction: discord.Interaction, 대상: discord.Member):
    uid = str(대상.id)
    count = 경고_데이터.get(uid, 0)
    embed = discord.Embed(
        title="⚠ 경고 확인",
        description=f"{대상.mention}님의 현재 경고 횟수는 **{count}회**입니다.",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"확인 요청자: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url if hasattr(interaction.user, 'display_avatar') else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="경고삭제", description="대상의 경고를 삭제합니다.")
@app_commands.checks.has_permissions(manage_messages=True)
async def 경고삭제(interaction: discord.Interaction, 대상: discord.Member):
    uid = str(대상.id)
    if uid in 경고_데이터:
        del 경고_데이터[uid]
        await interaction.response.send_message(f"{대상.mention}의 경고가 모두 삭제되었습니다.")
    else:
        await interaction.response.send_message(f"{대상.mention}님은 현재 경고가 없습니다.")

@bot.tree.command(name="추방", description="대상을 서버에서 추방합니다.")
@app_commands.checks.has_permissions(kick_members=True)
async def 추방(interaction: discord.Interaction, 대상: discord.Member, 이유: str = "이유 없음"):
    try:
        await 대상.kick(reason=이유)
        await interaction.response.send_message(f"{대상.mention}님을 추방했어요. 🚪\n이유: {이유}")
    except Exception as e:
        await interaction.response.send_message(f"⚠ 추방 실패: {e}")

@bot.tree.command(name="차단", description="대상을 서버에서 차단합니다.")
@app_commands.checks.has_permissions(ban_members=True)
async def 차단(interaction: discord.Interaction, 대상: discord.Member, 이유: str = "이유 없음"):
    try:
        await 대상.ban(reason=이유)
        await interaction.response.send_message(f"{대상.mention}님을 차단했어요. 🔨\n이유: {이유}")
    except Exception as e:
        await interaction.response.send_message(f"⚠ 차단 실패: {e}")

# ----- 공지 -----
@bot.tree.command(name="공지", description="서버 전체에 공지를 보냅니다.")
@app_commands.checks.has_permissions(administrator=True)
async def 공지(interaction: discord.Interaction, 내용: str):
    embed = discord.Embed(
        title="📢 공지",
        description=내용,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"작성자: {interaction.user.display_name}")
    # mention을 포함하려면 channel.send로 직접 보내는 편이 낫습니다.
    await interaction.channel.send("@everyone", embed=embed)
    await interaction.response.send_message("공지 전송 완료.", ephemeral=True)

# ----- 돈 시스템 & 도박 시스템 -----

돈_데이터 = {}  # 사용자별 잔액 저장용 (기본값 1000)

@bot.tree.command(name="돈", description="현재 보유 중인 금액을 확인합니다.")
async def 돈(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    잔액 = 돈_데이터.get(uid, 1000)  # 기본 잔액 1000
    돈_데이터[uid] = 잔액  # 처음 조회 시 저장

    await interaction.response.send_message(f"💰 {interaction.user.mention}님의 현재 보유 금액: **{잔액}원**")

@bot.tree.command(name="도박", description="돈을 걸고 도박을 시도합니다.")
@app_commands.describe(금액="얼마를 걸고 도박하실 건가요?")
async def 도박(interaction: discord.Interaction, 금액: int):
    if 금액 <= 0:
        await interaction.response.send_message("도박 금액은 **1원 이상**이어야 해요.", ephemeral=True)
        return

    uid = str(interaction.user.id)
    잔액 = 돈_데이터.get(uid, 1000)

    if 금액 > 잔액:
        await interaction.response.send_message("💸 가진 돈보다 많은 금액을 걸 수는 없어요.", ephemeral=True)
        return

    결과 = random.choice(["성공", "실패"])

    if 결과 == "성공":
        잔액 += 금액
        메시지 = f"🎉 도박 **성공!** {금액}원을 얻었습니다.\n💰 현재 잔액: {잔액}원"
    else:
        잃는_금액 = max(1, 금액 // 2)  # 최소 1원은 잃게 함
        잔액 -= 잃는_금액
        메시지 = f"💥 도박 **실패!** {잃는_금액}원을 잃었습니다.\n💰 현재 잔액: {잔액}원"

    돈_데이터[uid] = 잔액
    await interaction.response.send_message(f"{interaction.user.mention}님, 도박 결과: **{결과}**\n{메시지}")

# ----- 서버통계 -----

@bot.tree.command(name="서버정보", description="서버의 통계 정보를 보여줍니다.")
async def 서버정보(interaction: discord.Interaction):
    guild = interaction.guild

    total_members = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    category_channels = len(guild.categories)
    roles = len(guild.roles)
    created_at = guild.created_at.strftime("%Y년 %m월 %d일 %H:%M:%S")

    embed = discord.Embed(
        title=f"📊 {guild.name} 서버 정보",
        color=discord.Color.blue()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="👑 서버 소유자", value=str(guild.owner), inline=True)
    embed.add_field(name="📅 생성일", value=created_at, inline=True)
    embed.add_field(name="👥 전체 멤버", value=total_members, inline=True)
    embed.add_field(name="🧑 사람 수", value=humans, inline=True)
    embed.add_field(name="🤖 봇 수", value=bots, inline=True)
    embed.add_field(name="💬 텍스트 채널", value=text_channels, inline=True)
    embed.add_field(name="🔊 음성 채널", value=voice_channels, inline=True)
    embed.add_field(name="📁 카테고리", value=category_channels, inline=True)
    embed.add_field(name="🏷️ 역할 수", value=roles, inline=True)

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    channel = bot.get_channel(1402932723307515954)  # 채널ID를 숫자로 바꿔주세요

    embed = discord.Embed(
        title="봇 상태 알림",
        description="봇이 온라인되었습니다!",
        color=0x00ff00
    )
    embed.set_footer(text="봇 자동 알림")

    await channel.send(embed=embed)

# ----- 봇 실행 -----
import os
bot.run(os.getenv("DISCORD_TOKEN"))
