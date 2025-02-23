"""This is a cog for a discord.py bot.
It will add general commands and responses to a bot

Commands:
    gif             make the bot post a random gif for a given search term
    search          make the bot post a web-search link
    howto           make the bot post tutorials
     ├ codeblocks       how to send discord markdown codeblocks
     ├ ask              how to ask question on the server
     └ sticker          how to apply EM's stickers
    links           make the bot post links to the engineerman github pages
    memberinfo      provide information about the given member
    question        ask a question which the bot will answer using wolframalpha
    urbandictionary look up a word on urbandictionary.com
    video           make the bot post links to EM Videos on youtube
    weather         get the weather for a specific location
    inspect         print source code of a command
    statuscat       Commands that gives the requested HTTP statuses described and visualized by cats."
    statusdog       Commands that gives the requested HTTP statuses described and visualized by dogs."
    chucknorris     Shows a random chuck norris fun fact
    nasa            NASA's Astronomy Picture of the Day
"""

import re
import random
import typing
import hashlib
from inspect import getsourcelines
from datetime import datetime as dt
from urllib.parse import quote_plus
import discord

from discord.ext import commands, tasks
from discord import Embed, DMChannel, Member

# pylint: disable=E1101


class General(commands.Cog, name='General'):
    def __init__(self, client):
        self.client = client
        self.load_cat_http_codes.start()
        self.load_dog_http_codes.start()
        self.load_chuck_http_codes.start()
        self.re_converter = re.compile(r'(?i)(?P<num>[0-9]+(?:\.[0-9]*)?)\s?(?P<unit>[a-zA-Z°]+)')

    @tasks.loop(count=1)
    async def load_cat_http_codes(self):
        async with self.client.session.get('https://http.cat/') as response:
            text = await response.text()
            http_codes = re.findall(r'<a href="/(\d{3})">', text)
            http_codes.append(0)
            self.http_codes = [int(x) for x in http_codes]

    @tasks.loop(count=1)
    async def load_dog_http_codes(self):
        async with self.client.session.get('https://httpstatusdogs.com/') as response:
            text = await response.text()
            http_codes_dog = re.findall(r'<a href=\"(\d{3})-[^\"]*\"', text)
            self.http_codes_dog = [int(x) for x in http_codes_dog]

    @tasks.loop(count=1)
    async def load_chuck_http_codes(self):
        async with self.client.session.get('https://api.chucknorris.io/jokes/categories') as response:
            categories = await response.json()
            self.chuck_categories = [x for x in categories if x != 'explicit']

    # ----------------------------------------------
    # Helper Functions
    # ----------------------------------------------
    def get_year_string(self):
        now = dt.utcnow()
        year_end = dt(now.year+1, 1, 1)
        year_start = dt(now.year, 1, 1)
        year_percent = (now - year_start) / (year_end - year_start) * 100
        return f'For your information, the year is {year_percent:.1f}% over!'

    async def gif_url(self, terms):
        url = (
            f'http://api.giphy.com/v1/gifs/search'
            + f'?api_key={self.client.config["giphy_key"]}'
            + f'&q={terms}'
            + f'&limit=20'
            + f'&rating=R'
            + f'&lang=en'
        )
        async with self.client.session.get(url) as response:
            gifs = await response.json()
        if 'data' not in gifs:
            if 'message' in gifs:
                if 'Invalid authentication credentials' in gifs['message']:
                    print('ERROR: Giphy API key is not valid')
            return None
        if not gifs['data']:
            return None
        gif = random.choice(gifs['data'])['images']['original']['url']
        return gif

    # ----------------------------------------------
    # Cog Event listeners
    # ----------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, msg):
        # Ignore messages sent by bots
        if msg.author.bot:
            return

        # Ignore DM
        if isinstance(msg.channel, DMChannel):
            return

        if re.search(r'(?i).*what a twist.*', msg.content):
            await msg.channel.send('` - directed by M. Night Shyamalan.`')

        if re.search(
            r'(?i)(?:the|this) (?:current )?year is '
            + r'(?:almost |basically )?(?:over|done|finished)',
            msg.content
        ):
            await msg.channel.send(self.get_year_string())

        if re.search(
            r'(?i)send bobs and vagene',
            msg.content
        ):
            await msg.channel.send('😏 *sensible chuckle*')

        if re.search(
            r'(?i)^(?:hi|what\'s up|yo|hey|hello) felix',
            msg.content
        ):
            await msg.channel.send('hello')

        if re.search(
            r'(?i)^felix should (?:i|he|she|they|we|<@!?\d+>)',
            msg.content
        ):
            if random.random() >= 0.5:
                response = 'the answer I am getting from my entropy is: Yes.'
            else:
                response = 'the answer I am getting from my entropy is: No.'
            await msg.channel.send(response)

        if re.search(
            r'(?i)^html is a programming language',
            msg.content
        ):
            await msg.channel.send('no it\'s not, don\'t be silly')

        if re.search(
            r'(?i)^you wanna fight, felix\?',
            msg.content
        ):
            await msg.channel.send('bring it on pal (╯°□°）╯︵ ┻━┻')

        if re.search(
            r'(?i)^arrays start at 0',
            msg.content
        ):
            await msg.channel.send('arrays definitely start at 0')

        if re.search(
            r'(?i)^arrays start at 1',
            msg.content
        ):
            await msg.channel.send('arrays do not start at 1, they start at 0')

        if re.search(
            r'(?i)^felix meow',
            msg.content
        ):
            await msg.channel.send('ฅ^•ﻌ•^ฅ')

        if match := self.re_converter.search(msg.content):
            unit_aliases = {
                'mile' : 'miles',
                'kilometer' : 'km',
                'kilometers' : 'km',
                'kilometre' : 'km',
                'kilometres' : 'km',
                'fahrenheit' : '°f',
                '°fahrenheit' : '°f',
                'celsius' : '°c',
                '°celsius' : '°c',
            }
            conversions = {
                'miles': (lambda x:x*1.609344, 'km'),
                'km': (lambda x:x*0.6213712, 'miles'),
                '°f': (lambda x:(x-32)/1.8, '°C'),
                '°c': (lambda x:x*1.8+32, '°F'),
                'lb': (lambda x:x*0.4535924, 'kg'),
                'kg': (lambda x:x*2.204623, 'lb'),
            }
            n, unit = match.groups()
            if unit.lower() not in unit_aliases | conversions:
                return
            unit = unit_aliases.get(unit.lower(), unit)
            n = float(n)
            converter, new = conversions[unit]
            await msg.channel.send(f'{round(n, 2)} {unit} = {round(converter(n), 2)} {new}')

    # ----------------------------------------------
    # Cog Commands
    # ----------------------------------------------

    @commands.command(
        name='gif'
    )
    async def gif_embed(self, ctx, *, gif_name):
        """Post a gif
        Displays a random gif for the specified search term"""
        await ctx.trigger_typing()
        gif_url = await self.gif_url(gif_name)
        if gif_url is None:
            await ctx.send(f'Sorry {ctx.author.mention}, no gif found 😔')
            # await ctx.message.add_reaction('❌')
        else:
            e = Embed(color=0x000000)
            e.set_image(url=gif_url)
            e.set_footer(
                text=ctx.author.display_name,
                icon_url=ctx.author.avatar_url
            )

            await ctx.send(embed=e)
    # ------------------------------------------------------------------------

    @commands.command(
        name='search',
        aliases=['lmgtfy', 'duck', 'duckduckgo', 'google']
    )
    async def search(self, ctx, *, search_text):
        """Post a duckduckgo search link"""
        await ctx.trigger_typing()
        await ctx.send(
            f'here you go! <https://duckduckgo.com/?q={quote_plus(search_text)}>'
        )
    # ------------------------------------------------------------------------

    @commands.command(
        name='stackoverflow',
        aliases=['stacko', 'stack']
    )
    async def stackoverflow(self, ctx, *, search_text):
        """Post a stackoverflow search link"""
        await ctx.trigger_typing()
        await ctx.send(
            f'here you go! <https://stackoverflow.com/search?q={quote_plus(search_text)}>'
        )

    @commands.group(
        name="howto",
        invoke_without_command=True,
        aliases=['how-to', 'info']
    )
    async def howto(self, ctx):
        """Show useful information for newcomers"""
        await ctx.send_help('how-to')

    @howto.command(
        name='codeblocks',
        aliases=['codeblock', 'code-blocks', 'code-block', 'code']
    )
    async def codeblocks(self, ctx):
        """Instructions on how to properly paste code"""
        code_instructions = (
            "Discord has an awesome feature called **Text Markdown** which "
            "supports code with full syntax highlighting using codeblocks."
            "To use codeblocks all you need to do is properly place the "
            "backtick characters *(not single quotes)* and specify your "
            "language *(optional, but preferred)*.\n\n"
            "**This is what your message should look like:**\n"
            "*\\`\\`\\`[programming language]\nYour code here\n\\`\\`\\`*\n\n"
            "**Here's an example:**\n"
            "*\\`\\`\\`python\nprint('Hello world!')\n\\`\\`\\`*\n\n"
            "**This will result in the following:**\n"
            "```python\nprint('Hello world!')\n```\n"
            "**NOTE:** Codeblocks are also used to run code via `/run`."
        )
        link = (
            'https://support.discordapp.com/hc/en-us/articles/'
            '210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-'
        )

        e = Embed(title='Text markdown',
                  url=link,
                  description=code_instructions,
                  color=0x2ECC71)
        await ctx.send(embed=e)

    @howto.command(
        name='ask',
        aliases=['questions', 'question']
    )
    async def ask(self, ctx):
        """How to properly ask a question"""
        ask_instructions = (
            "From time to time you'll stumble upon a question like this:\n"
            "*Is anyone good at [this]?* / *Does anyone know [topic]?*\n"
            "Please **just ask** your question.\n\n"
            "• Make sure your question is easy to understand.\n"
            "• Use the appropriate channel to ask your question.\n"
            "• Always search before you ask (the internet is a big place).\n"
            "• Be patient (someone will eventually try to help you)."
        )

        e = Embed(title='Just ask',
                  description=ask_instructions,
                  color=0x2ECC71)
        await ctx.send(embed=e)

    @howto.command(
        name='font',
        aliases=['format', 'formatting', 'write']
    )
    async def font_format(self, ctx):
        """Instructions on how to format your text"""
        font_instructions = (
            "Discord supports font formatting with the following options:\n"
            "*italics*\u1160 \u1160 \u1160 \u1160\u1160\u1160\u1160"
            "\\*italics\\* | \\_italics\\_\n"
            "**bold**\u1160 \u1160 \u1160 \u1160 \u1160 \u1160\u1160"
            "\\*\\*bold\\*\\*\n"
            "***bold italics***\u1160 \u1160 \u1160\u1160\u1160"
            "\\*\\*\\*bold italics\\*\\*\\*\n"
            "__underline__\u1160 \u1160\u1160\u1160\u1160\u1160"
            "\\_\\_underline\\_\\_\n"
            "__*underline italics*__\u1160 \u1160 \u1160 "
            "\\_\\_\\*underline italics\\*\\_\\_\n"
            "__**underline bold**__\u1160\u1160\u1160\u1160"
            "\\_\\_\\*\\*underline bold\\*\\*\\_\\_\n"
            "__***underline bold italics***__\u1160 "
            "\\_\\_\\*\\*\\*underline bold italics\\*\\*\\*\\_\\_\n"
            "~~strikethrough~~\u1160 \u1160 \u1160 \u1160"
            "\\~\\~strikethrough\\~\\~\n"
        )
        link = (
            'https://support.discordapp.com/hc/en-us/articles/'
            '210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-'
        )

        e = Embed(title='Font Formatting',
                  url=link,
                  description=font_instructions,
                  color=0x2ECC71)
        await ctx.send(embed=e)

    @commands.command(
        name='links',
        aliases=['urls', 'sauce', 'source'],
    )
    async def links(self, ctx):
        """Show links to all things EngineerMan"""
        links = (
            '• [Youtube](https://www.youtube.com/engineerman)'
            + '\n• [Discord](https://engineerman.org/discord)'
            + '\n• [EMKC](https://emkc.org/)'
            + '\n• [EMKC Snippets](https://emkc.org/snippets)'
            + '\n• [EMKC Challenges](https://emkc.org/challenges)'
            + '\n• [Github Youtube](https://github.com/engineer-man/youtube-code)'
            + '\n• [Github EMKC](https://github.com/engineer-man/emkc)'
            + '\n• [Github Felix](https://github.com/engineer-man/felix)'
            + '\n• [Github Piston](https://github.com/engineer-man/piston)'
            + '\n• [Github Piston-Bot](https://github.com/engineer-man/piston-bot)'
            + '\n• [Twitter](https://twitter.com/_EngineerMan)'
            + '\n• [Facebook](https://www.facebook.com/engineermanyt)'
            + '\n• [Reddit](https://www.reddit.com/r/engineerman/)'
            + '\n• [Reddit Resources](https://www.reddit.com/r/engineerman/search/?q=flair%3AResource&restrict_sr=1)'
        )
        e = Embed(
            title='Links',
            description=links,
            color=0x2ECC71
        )
        await ctx.send(embed=e)

    @commands.command(
        name='faq'
    )
    async def faq(self, ctx):
        """Show answers to frequently asked questions"""
        embed = Embed(color=0x2ECC71)
        embed.set_author(name='Frequently Asked Questions')
        questions = {
            'What do you do professionally?':
                'In addition to YouTube, Engineer Man works on various client '
                'projects and oversees several projects.',
            'How long have you been programming?':
                'About ' + str(dt.now().year - 1994) + ' years',
            'What distro and editor do you use?':
                'Distro: Xubuntu, Editor: Atom',
            'I want to get into programming, how should I get started?':
                'First, figure out what sort of programming interests you, '
                'such as web, desktop, game, systems, etc. '
                'From there, choose a language that relates to that area and '
                'begin reviewing documentation, reading tutorials, and '
                'watching videos. Finally, start creating your own projects.',
            'What is the best way to learn Language X':
                'Most languages are similar in the types of things they '
                'accomplish, where they differ is in how they accomplish them. '
                'If you\'re new to programming, it\'s important to learn '
                'syntax first. After that, learning that language\'s standard '
                'library is a good use of time. Beyond that, it\'s just '
                'experimenting with the language and working on projects in '
                'that language.',
            'How can I stay focused/prevent burn out?':
                'The best way is to try to finish something, anything, even '
                'if it\'s not as complete as you want. Finishing things is '
                'satisfying, and once you do you\'ll be more motivated to '
                'improve what you have. Allowing a project to drone on '
                'forever without finishing is a way to get bored with it.'
        }
        for question, answer in questions.items():
            embed.add_field(
                name=question,
                value=answer,
                inline=False
            )
        await ctx.send(embed=embed)
    # ------------------------------------------------------------------------

    @commands.group(
        invoke_without_command=True,
        name='memberinfo',
        aliases=['member']
    )
    async def memberinfo(self, ctx, member: Member = None):
        """Provides information about the given member."""
        if not member:
            member = ctx.author
        url = 'https://emkc.org/api/v1/stats/discord/messages'
        params = [('discord_id', member.id)]
        async with self.client.session.get(url, params=params) as r:
            if r.status != 200:
                raise commands.BadArgument('Bad response from EMKC API')
            data = await r.json()
        embed = Embed(color=member.color)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(
            text=ctx.author.display_name,
            icon_url=ctx.author.avatar_url
        )
        message_count = data[0]['messages'] if data else 0
        guild_time = (dt.utcnow() - member.joined_at).total_seconds() / 86400
        # In this case a dict is used for readability, but this must be changed
        # if "inline" needs to be specified for individual fields
        fields = {
            'Username:': str(member),
            'Display name:': member.display_name,
            'Account created at:': member.created_at.strftime("%Y/%m/%d"),
            'Status:': str(member.status).title(),
            'Joined at:': member.joined_at.strftime("%Y/%m/%d"),
            'Top role:': member.top_role.mention
            if str(member.top_role) != '@everyone' else '@everyone',
            'Message count:': message_count,
            'Messages per day:': round(message_count / guild_time, 1)
            if guild_time >= 1 else message_count,
            'Flagged:': 'True'
            if 484183734686318613 in (i.id for i in member.roles) else 'False',
            'Current activities:':
            '\n'.join(i.name for i in member.activities if i.name)
            or 'No current activities'
        }
        for name, value in fields.items():
            embed.add_field(
                name=name,
                value=value
            )
        await ctx.send(embed=embed)

    @memberinfo.command(
        name='oldest',
    )
    async def oldest(self, ctx):
        """Get the oldest Discord account on the Server"""
        oldst = min([x for x in ctx.guild.members], key=lambda y: y.created_at)
        await ctx.send(
            'Oldest Discord account on this Server:\n'
            f'`{str(oldst)} created {oldst.created_at}`'
        )
    # ------------------------------------------------------------------------

    @commands.command(
        name='question',
        aliases=['q']
    )
    async def question(self, ctx, *, question):
        """Ask Felix a question"""
        await ctx.trigger_typing()
        url = 'https://api.wolframalpha.com/v1/result?i=' + \
            f'{quote_plus(question)}&appid={self.client.config["wolfram_key"]}'
        async with self.client.session.get(url) as response:
            answer = await response.text()
        if 'did not understand' in answer:
            answer = 'Sorry, I did not understand that'
        await ctx.send(answer)
    # ------------------------------------------------------------------------

    @commands.command(
        name='urban',
        aliases=['ud', 'urbandictionary', 'urbandict'],
    )
    async def urbandictionary(self, ctx, *, term):
        """Ask urbandictionary
        Get the definition of a word from Urbandictionary"""
        url = f'http://api.urbandictionary.com/v0/define?term={quote_plus(term)}'
        async with self.client.session.get(url) as response:
            answer = await response.json()
        if not answer['list']:
            await ctx.send('Sorry, I did not understand that')
            return
        definition = answer["list"][0]["definition"]
        example = answer["list"][0]["example"]
        if len(definition + example) > 1950:
            definition = definition[:1950 - len(example)] + ' (...)'
        response = (
            '\n**Definition:**\n'
            f'{definition}\n'
            '\n**Example:**\n'
            f'{example}'
        )
        embed = Embed(
            title=f'"**{term}**" according to urbandictionary.com',
            url=f'https://urbandictionary.com/define.php?term={quote_plus(term)}',
            description=response.replace('[', '').replace(']', ''),
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_footer(
            text=ctx.author.display_name,
            icon_url=ctx.author.avatar_url
        )
        await ctx.send(embed=embed)
    # ------------------------------------------------------------------------

    @commands.command(
        name='video'
    )
    async def video(self, ctx, *, term):
        """Search Youtube for EM videos"""
        video_list = []
        page_token = ''

        while True:
            url = 'https://www.googleapis.com/youtube/v3/search' +\
                '?key=' + self.client.config['yt_key'] +\
                '&channelId=UCrUL8K81R4VBzm-KOYwrcxQ' +\
                '&part=snippet,id' +\
                '&order=date' +\
                '&maxResults=50'

            if page_token:
                url += '&pageToken=' + page_token

            async with self.client.session.get(url) as response:
                videos = await response.json()

            for video in videos['items']:
                if 'youtube#video' not in video['id']['kind']:
                    continue
                video_list.append({
                    'id': video['id']['videoId'],
                    'title': video['snippet']['title']
                })

            if 'nextPageToken' not in videos:
                break

            page_token = videos['nextPageToken']

        to_send = [v for v in video_list if all(
            keyword in v['title'].lower() for keyword in term.lower().split())]

        if not to_send:
            response = 'Sorry, no videos found for: ' + term
            await ctx.send(response)
        else:
            to_send = to_send[:5]
            description = [
                f'[{v["title"]}](https://www.youtube.com/watch?v={v["id"]})' for v in to_send]
            description = '\n'.join(description)
            e = Embed(
                title='Search Results',
                description=description
            )
            await ctx.send(embed=e)

    # ------------------------------------------------------------------------

    @commands.command(
        name='weather'
    )
    async def weather(
        self, ctx,
        location: str,
        days: typing.Optional[int] = 0,
        units: typing.Optional[str] = 'm',
    ):
        """Get the current weather/forecast in a location

        Probably difficult to view on mobile

        Options:
          \u1160**location** examples:
            \u1160\u1160berlin
            \u1160\u1160~Eiffel+tower
            \u1160\u1160Москва
            \u1160\u1160muc
            \u1160\u1160@stackoverflow.com
            \u1160\u116094107
            \u1160\u1160-78.46,106.79
          \u1160**days** (0-3):  The amount of forecast days
          \u1160**units** (m/u/mM/uM): m = Metric | u = US | M = wind in M/s

          API used: https://en.wttr.in/:help"""
        if units not in ["m", "u", "mM", "uM"]:
            location = f"{location} {units}"
            units = "m"
        location = location.replace('.png', '')
        moon = location.startswith('moon')
        url = (
            'https://wttr.in/'
            f'{location}?{units}{days}{"" if days else "q"}nTAF'
        )
        async with self.client.session.get(url) as response:
            weather = await response.text()
            weather = weather.split('\n')
        if len(weather) < 8:
            weather = f'the weather api returned an invalid response, try again later'
            await ctx.send(weather)
            return
        if 'Sorry' in weather[0] or (weather[1] and not moon):
            return
        if days:
            weather = [weather[0]]+weather[7:]
            if len(weather[-1]) == 0:
                weather = weather[:-1]
            if weather[-1].startswith('Location'):
                weather = weather[:-1]
        weather_codeblock = '```\n' + '\n'.join(weather) + '```'
        if len(weather_codeblock) > 2000:
            weather_codeblock = 'Sorry - response longer than 2000 characters'
        await ctx.send(weather_codeblock)

    @commands.command(
        name='inspect'
    )
    async def inspect(self, ctx, *, command_name: str):
        """Print a link and the source code of a command"""
        cmd = self.client.get_command(command_name)
        if cmd is None:
            return
        module = cmd.module
        saucelines, startline = getsourcelines(cmd.callback)
        url = (
            '<https://github.com/engineer-man/felix/blob/master/python/'
            f'{"/".join(module.split("."))}.py#L{startline}>\n'
        )
        sauce = ''.join(saucelines)
        # Little hack so triple quotes don't end discord codeblocks when printed
        sanitized = sauce.replace('`', '\u200B`')
        if len(sanitized) > 1900:
            sanitized = sanitized[:1900] + '\n[...]'
        await ctx.send(url + f'```python\n{sanitized}\n```')

    @commands.command(
        name='run'
    )
    async def run_message(self, ctx):
        await ctx.send('Please use `/run` to run code.')

    # ------------------------------------------------------------------------

    @commands.command(name=chr(99)+chr(116)+chr(102), hidden=True)
    async def ftc(self, ctx, s):
        await ctx.message.delete()
        if hashlib.sha1(s.encode()).digest().startswith(b'felix'):
            try:
                await ctx.author.send(self.client.config[chr(99)+chr(116)+chr(102)])
            except discord.errors.Forbidden:
                return
    # ------------------------------------------------------------------------

    @commands.command(
        name='statuscat',
        aliases=['cat']
    )
    async def statuscat(self, ctx, code: int = None):
        """Sends an embed with an image of a cat, portraying the status code.
           If no status code is given it will return a random status cat."""
        if not hasattr(self, 'http_codes'):
            raise commands.BadArgument('HTTP cats codes not loaded yet')

        if code is None:
            code = random.choice(self.http_codes)
        else:
            if code not in self.http_codes:
                raise commands.BadArgument(f'Invalid status code: **{code}**')

        embed = Embed()
        embed.set_image(url=f'https://http.cat/{code}.jpg')
        embed.set_footer(text=f'Provided by: https://http.cat')
        await ctx.send(embed=embed)

    @commands.command(
        name='statusdog',
        aliases=['dog']
    )
    async def statusdog(self, ctx, code: int = None):
        """Sends an embed with an image of a dog, portraying the status code.
           If no status code is given it will return a random status dog."""
        if not hasattr(self, 'http_codes_dog'):
            raise commands.BadArgument('HTTP dogs codes not loaded yet')

        if code is None:
            code = random.choice(self.http_codes_dog)
        else:
            if code not in self.http_codes_dog:
                raise commands.BadArgument(f'Invalid status code: **{code}**')

        embed = Embed()
        embed.set_image(url=f'https://httpstatusdogs.com/img/{code}.jpg')
        embed.set_footer(text=f'Provided by: https://httpstatusdogs.com/')
        await ctx.send(embed=embed)

    @commands.command(
        name='chucknorris',
        aliases=['chuck', 'cn']
    )
    async def chucknorris(self, ctx, category: str = None):
        """ Collects a random chuck norris joke, or collect a random joke
            by specifying a specific category of joke. """
        if not hasattr(self, 'chuck_categories'):
            raise commands.BadArgument('Hold up partner, still locating Chuck!')

        if category is None:
            category = random.choice(self.chuck_categories)
        else:
            if category not in self.chuck_categories:
                raise commands.BadArgument(
                    f'Invalid category - please pick from:\n{", ".join(self.chuck_categories)}'
                )

        try:
            async with self.client.session.get(
                f'https://api.chucknorris.io/jokes/random?category={category}'
            ) as response:
                chuck = await response.json()
                chuck = chuck['value']

                embed = Embed(
                    description=chuck,
                    color=random.randint(0, 0xFFFFFF))
                embed.set_author(
                    name='Chuck Norris fun fact...',
                    icon_url=f'https://assets.chucknorris.host/img/avatar/chuck-norris.png'
                )
                embed.set_footer(text=f'Category: {category} - https://api.chucknorris.io')
                await ctx.send(embed=embed)

        except:
            raise commands.BadArgument('Chuck not found, currently evading GPS in Texas!')

    # ------------------------------------------------------------------------

    @commands.command(
        name='nasa',
        aliases=['apod', 'space']
    )
    async def apod_day(self, ctx, date: str = ''):
        """ Show "Astronomy Picture of the Day" of specified date (YYYY-MM-DD)
            Show today's picture if no date is provided"""
        if '-' not in date and date.isnumeric() and len(date) == 8:
            date = '-'.join((date[:4], date[4:6], date[6:8]))
        async with self.client.session.get(
            'https://api.nasa.gov/planetary/apod'
            + f'?api_key={self.client.config["nasa_key"]}&date={date}'
        ) as response:

            apod_data=await response.json()
            if apod_data.get('code', 200) != 200:
                raise commands.BadArgument(apod_data.get('msg', 'Error'))
            embed=Embed(description=apod_data['explanation'],
                          color=random.randint(0, 0xFFFFFF))

            if apod_data['media_type'] == 'image':
                embed.set_image(url=apod_data['hdurl'])
            else:
                embed.add_field(name='Video URI', value=apod_data['url'])
            embed.set_author(
                name=apod_data['title'],
                icon_url='https://api.nasa.gov/assets/img/favicons/favicon-192.png')

            if 'copyright' in apod_data:
                embed.set_footer(
                    text=f'Copyright: {apod_data["copyright"]}\n'
                    + f'Date: {apod_data["date"]}\n'
                    + 'Provided By: https://api.nasa.gov/')
            else:
                embed.set_footer(
                    text=f'Date: {apod_data["date"]}\n'
                    + 'Provided By: https://api.nasa.gov/')

            await ctx.send(embed=embed)

    # ------------------------------------------------------------------------

    @staticmethod
    def result_fmt(url: str, language: str, body_text: str) -> str:
        """Format Result."""
        body_space=min(1992 - len(language) - len(url), 1000)

        if len(body_text) > body_space:
            description=(
                f'**Result Of cht.sh**\n```{language}\n{body_text[:body_space - 20]}'
                + f'\n... (truncated - too many lines)```\nFull results: {url} '
            )
            return description

        description=f'**Result Of cht.sh**\n```{language}\n{body_text}```\n{url}'
        return description

    @ commands.command(
        name='cheat',
        aliases=('cht.sh', 'cheatsheet', 'cheat-sheet', 'cht'),
    )
    async def cheat_sheet(
            self, ctx, language: str, *search_terms: str
    ) -> None:
        """Search cheat.sh."""
        url=f'https://cheat.sh/{quote_plus(language)}'
        if search_terms:
            url += f'/{quote_plus(" ".join(search_terms))}'
        escape_tt=str.maketrans({'`': '\\`'})
        ansi_re=re.compile(r'\x1b\[.*?m')

        async with self.client.session.get(
                url,
                headers={'User-Agent': 'curl/7.68.0'}
        ) as response:
            result=ansi_re.sub('', await response.text()).translate(escape_tt)

        await ctx.send(self.result_fmt(url, language, result))


def setup(client):
    client.add_cog(General(client))
