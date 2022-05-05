from __future__ import annotations

import functools
import inspect

from typing import TYPE_CHECKING, Awaitable

import discord
from discord import Member, PartialMessageable
from discord.ext import commands

from core.constants import REPLY, CAN_DELETE, SAFE_SEND

if TYPE_CHECKING:
    from typing import Any, AsyncGenerator, Callable, TypeVar, ParamSpec

    from discord.ext.commands import Command, HybridCommand

    from core.context import BoboContext
    from core.types import OutputType
    from core.cog import Cog

    P = ParamSpec('P')
    T = TypeVar('T')


__all__ = ('user_permissions_predicate', 'bot_permissions_predicate', 'command')


def user_permissions_predicate(ctx: BoboContext) -> bool:
    if not ctx.guild:
        return True

    assert isinstance(ctx.author, Member)
    assert not isinstance(ctx.channel, PartialMessageable)

    perms = {
        'send_messages': True,
    }

    permissions = ctx.channel.permissions_for(ctx.author)

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.MissingPermissions(missing)


def bot_permissions_predicate(ctx: BoboContext) -> bool:
    if not ctx.guild:
        return True

    perms = {
        'send_messages': True,
        'attach_files': True,
        'embed_links': True,
    }

    assert not isinstance(ctx.channel, PartialMessageable)

    permissions = ctx.channel.permissions_for(ctx.guild.me)

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.BotMissingPermissions(missing)


async def process_output(ctx: BoboContext, output: OutputType | None) -> None:
    if output is None:
        return

    kwargs = {}
    des = ctx.send

    if not isinstance(output, tuple):
        output = (output,)

    for i in output:
        if isinstance(i, discord.Embed):
            kwargs['embed'] = i

        elif isinstance(i, str):
            kwargs['content'] = i

        elif isinstance(i, discord.ui.View):
            kwargs['view'] = i

        elif isinstance(i, discord.File):
            kwargs['file'] = i

        elif isinstance(i, dict):
            kwargs.update(i)

        elif i is REPLY:
            des = ctx.reply

        elif i is CAN_DELETE:
            kwargs['can_delete'] = True

        elif i is SAFE_SEND:
            kwargs['safe_send'] = True

    await des(**kwargs)


async def _command_callback(
    ctx: BoboContext, coro: AsyncGenerator[Any, None] | Awaitable[Any]
) -> None:
    if inspect.isasyncgen(coro):
        async for ret in coro:
            await process_output(ctx, ret)
    else:
        await process_output(ctx, await coro)  # type: ignore


def command_callback(
    func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]
) -> Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]:
    @functools.wraps(func)
    async def wrapper(self: Cog, ctx: BoboContext, *args: Any, **kwargs: Any) -> None:
        await _command_callback(ctx, func(self, ctx, *args, **kwargs))

    return wrapper


@discord.utils.copy_doc(commands.command)
def command(
    **attrs,
) -> Callable[
    [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]], Command
]:
    command = commands.command(**attrs)

    def wrapper(
        func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]
    ) -> Command:
        return command(command_callback(func))  # type: ignore

    return wrapper

@discord.utils.copy_doc(commands.hybrid_command)
def hybrid_command(
    **attrs,
) -> Callable[
    [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]],
    HybridCommand,
]:
    hybrid_command = commands.hybrid_command(**attrs)

    def wrapper(
        func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]
    ) -> HybridCommand:
        return hybrid_command(command_callback(func))  # type: ignore

    return wrapper


class GroupCommand(commands.Group):
    @discord.utils.copy_doc(commands.Group.command)
    def command(
        self, *args: Any, **kwargs: Any
    ) -> Callable[
        [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]],
        Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]],
    ]:
        def wrapper(
            func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]
        ) -> commands.Command:
            kwargs.setdefault('parent', self)
            command_ = command(*args, **kwargs)(func)
            self.add_command(command_)

            return command_

        return wrapper


class HybridGroup(commands.HybridGroup):
    @discord.utils.copy_doc(commands.HybridGroup.command)
    def command(
        self, *args: Any, **kwargs: Any
    ) -> Callable[
        [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]],
        Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]],
    ]:
        def wrapper(
            func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, Any]]
        ) -> commands.Command:
            kwargs.setdefault('parent', self)
            command_ = hybrid_command(*args, **kwargs)(func)
            self.add_command(command_)

            return command_

        return wrapper


def group(
    **attrs,
) -> Callable[
    [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]],
    GroupCommand,
]:
    if 'invoke_without_command' not in attrs:
        attrs['invoke_without_command'] = True

    group = commands.group(cls=GroupCommand, **attrs)

    def wrapper(
        func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]
    ) -> GroupCommand:
        return group(command_callback(func))  # type: ignore

    return wrapper


def hybrid_group(
    **attrs,
) -> Callable[
    [Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]],
    HybridGroup,
]:
    if 'invoke_without_command' not in attrs:
        attrs['invoke_without_command'] = True

    group = commands.group(cls=HybridGroup, **attrs)

    def wrapper(
        func: Callable[..., Awaitable[OutputType] | AsyncGenerator[OutputType, None]]
    ) -> HybridGroup:
        return group(command_callback(func))  # type: ignore

    return wrapper
