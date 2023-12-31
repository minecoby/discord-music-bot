import discord
from discord.ext import commands
import yt_dlp
import asyncio
from datetime import timedelta


intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='~', intents=intents, help_command=None)

#노래 정보를 불러오기위한 옵션설정
ydl_opts = {
    'default_search':
    'ytsearch',
    'format':
    'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '128',
    }],
    'youtube_include_dash_manifest':
    False,
}
#노래재생에 필요한 전역변수설정
current_music = {}
music_list = {}
playing_music = {}


#봇이 정상적으로 실행되었음을 확인
@bot.event
async def on_ready():
  print(bot.user.name, '봇이 정상적으로 작동을 시작했습니다.')
  stat = discord.Game('상태입력')
  await bot.change_presence(status=discord.Status.online, activity=stat)


#노래 재생 (/play)명령어 실행
@bot.command(aliases=['p', 'ㅔ', '재생'])
async def play(ctx, *, search):
  guild_id = ctx.guild.id  # 현재 서버 ID

  if guild_id not in music_list:
    music_list[guild_id] = []

  if guild_id not in playing_music:
    playing_music[guild_id] = False

  if playing_music[guild_id] == False:
    channel = ctx.message.author.voice.channel
    voice_channel = await channel.connect()
    music_list[guild_id].append(search)
    playing_music[guild_id] = True
    await music_play(voice_channel, ctx)
  else:
    music_list[guild_id].append(search)
    embed = discord.Embed(title=f"노래가 대기열에 추가되었습니다!",
                          color=0x0000ff,
                          description=f'{search} 항목이 대기열에 추가되었습니다.')
    await ctx.send(embed=embed)


#노래재생 명령어 실행후 노래실행
async def music_play(voice_channel, ctx):
  global skip_music
  guild_id = ctx.guild.id  # 현재 서버 ID
  search = music_list[guild_id].pop(0)
  current_music[guild_id] = search
  with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(search, download=False)
    url2 = info['entries'][0]['url']
    title = info['entries'][0]['title']
    thumbnail_url = info['entries'][0]['thumbnails'][0]['url']
    youtube_url = info['entries'][0]['webpage_url']
    duration = info['entries'][0]['duration']

  duration_str = str(timedelta(seconds=duration))
  embed = discord.Embed(title=f"🎵 {title}", color=0x0000ff, description=f'\n')
  embed.add_field(name="곡 길이", value=f"{duration_str}", inline=True)
  embed.add_field(name="\u200b", value="\u200b", inline=True)
  embed.add_field(name="음원", value=f"[바로가기]({youtube_url})", inline=True)
  embed.set_thumbnail(url=thumbnail_url)
  await ctx.send(embed=embed)
  voice_channel.play(
      discord.FFmpegPCMAudio(
          url2,
          before_options=
          "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
  while voice_channel.is_playing():
    await asyncio.sleep(1)
  await play_next(voice_channel, ctx)


#노래실행후 다음노래가 있는지 확인
async def play_next(voice_channel, ctx):
  guild_id = ctx.guild.id  # 현재 서버 ID
  if len(music_list[guild_id]) > 0:
    await music_play(voice_channel, ctx)
  else:
    playing_music[guild_id] = False
    await voice_channel.disconnect()


#노래 대기열 확인
@bot.command(aliases=['대기열', 'dorlduf'])
async def queue(ctx):
  global music_list
  guild_id = ctx.guild.id  # 현재 서버 ID
  if guild_id not in music_list or len(music_list[guild_id]) == 0:
    embed = discord.Embed(title=f"🎵 노래 대기열 목록",
                          color=0x0000ff,
                          description=f'다음차례 노래가 없습니다.')
    await ctx.send(embed=embed)
  else:
    description = "\n".join(f"{i+1}. {song}"
                            for i, song in enumerate(music_list[guild_id]))
    embed = discord.Embed(title=f"노래 대기열 목록",
                          color=0x0000ff,
                          description=description)
    await ctx.send(embed=embed)


#대기열 삭제
@bot.command(aliases=['삭제'])
async def delque(ctx, index: int):
  global music_list
  guild_id = ctx.guild.id  # 현재 서버 ID
  if index < 1 or index > len(music_list[guild_id]):
    embed = discord.Embed(title=f"대기열 삭제 실패", description="존재하지 않는 대기열번호입니다.")
    await ctx.send(embed=embed)
  else:
    music_list[guild_id].pop(index - 1)
    embed = discord.Embed(title=f"대기열 삭제 성공", description="정상적으로 삭제되었습니다.")
    await ctx.send(embed=embed)


#노래 스킵하기
@bot.command(aliases=['스킵', 's'])
async def skip(ctx):
  global playing_music
  voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
  if voice_client.is_playing():
    voice_client.stop()
    await ctx.send("🎵 현재 재생 중인 노래를 스킵했습니다.")
  else:
    await ctx.send("🎵 현재 재생 중인 노래가 없습니다.")

#노래 다시재생하기
@bot.command(aliases=['다시재생','r'])
async def replay(ctx):
  guild_id = ctx.guild.id
  global playing_music,search
  music_list[guild_id].insert(0,current_music[guild_id])
  voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
  voice_client.stop()
  await ctx.send("🎵 현재노래를 다시 재생합니다.")

#노래봇 강제종료
@bot.command(aliases=['종료', 'ss'])
async def stop(ctx):
  guild_id = ctx.guild.id  # 현재 서버 ID
  playing_music[guild_id] = False
  music_list[guild_id] = []
  voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
  if voice_client.is_connected():
    await voice_client.disconnect()



bot.run('API-key')
