#!/usr/bin/python

import threading
import asyncio
import json
from requests import HTTPError
import websockets
from typing import Optional
from time import sleep
from locust import HttpUser, task
from play import Reader, Action
from dataclasses import dataclass, asdict

from itertools import count as iter_count
import os

user_counter = iter_count(0)

base_url = os.environ["BASE_URL"]
print("__BASE_URL__", base_url)


@dataclass
class UserInfo:
    username: str
    password: str
    googleSignIn: bool = False


class User:
    info: UserInfo
    game_reader: Optional[Reader]
    color: str

    def __init__(self, info, color):
        self.info = info
        self.color = color


class Game:
    player1: User
    player2: Optional[User] = None
    id: str
    game_reader: Reader
    lock: threading.Lock

    def __init__(self):
        self.lock = threading.Lock()

    def set_id(self, id: str):
        self.id = id

    def add_first(self, p1: UserInfo):
        self.player1 = User(p1, "B")

    def add_second(self, p2: UserInfo):
        self.player2 = User(p2, "W")

        self.game_reader = Reader()

        self.player1.game_reader = self.game_reader
        self.player2.game_reader = self.game_reader


games: list[Game] = []
game_creation_locks: list[threading.Lock] = []


class HelloWorldUser(HttpUser):
    web_socket_lock: threading.Lock
    p: User

    def get_headers(self):
        print(self.token)

        headers = {
            "Content-Type": "application/json",
        }

        if getattr(self, "token", None):
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    s_authentication = "/Authentication"
    s_password_login = f"{s_authentication}/PasswordLogin"

    def ws_url(self):
        return f"wss://{base_url}/mainHub?negotiateVersion=1&token={self.token}"

    signalr_sep = "\x1e"

    s_player = "/Player"
    s_create_game = f"{s_player}/CreateGame"
    s_join_game = f"{s_player}/JoinGame"

    s_game = "/Game"

    def s_game_id(self):
        return f"{self.s_game}/{self.game.id}"

    def s_make_move(self):
        return f"{self.s_game_id()}/MakeMove"

    def __init__(self, environment):
        super().__init__(environment)
        self.ws = None

    def get_event_loop(self):
        """Ensure each Locust thread has its own event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    async def connect(self):
        """Establish WebSocket connection and perform the SignalR handshake."""
        self.ws = await websockets.connect(self.ws_url())

        # Send handshake request
        handshake = json.dumps(
            {"protocol": "json", "version": 1}) + self.signalr_sep
        await self.ws.send(handshake)

        # Read handshake response
        response = await self.ws.recv()
        print("Handshake Response:", response)

        self.web_socket_lock.release()
        return response

    def run_sync_connect(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            print("Creating new one")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect())
        else:
            print("Running in existing loop")
            asyncio.create_task(self.connect())  # Use create_task instead

    def on_start(self):
        self.idx = next(user_counter)
        self.token = None

        print("Password login", self.s_password_login)
        print("Hello")

        user_info = UserInfo(f"p_{self.idx}", "string")
        print("Login User: ", user_info)

        response = self.client.post(
            self.s_password_login,
            json=asdict(user_info),
            headers=self.get_headers(),
        )

        login_res = response.json()
        print("login body", login_res)

        self.token = login_res["creds"]["token"]

        lock = threading.Lock()

        game_creation_locks.append(lock)
        lock.acquire()

        self.web_socket_lock = threading.Lock()
        self.web_socket_lock.acquire()

        self.run_sync_connect()

        self.web_socket_lock.acquire()

        if len(games) == 0:
            game = Game()
            game.add_first(user_info)
            self.p = game.player1
            self.create_game(game)
            games.append(game)
            self.game = game
            lock.release()
        else:
            lock = game_creation_locks.pop()
            game = games.pop()

            try:
                game.add_second(user_info)
                self.p = game.player2
                self.join_game(game)
                self.game = game
            except HTTPError as e:
                # user now just makes rando requests, doesn't get to play
                pass
            finally:
                lock.release()

    def create_game(self, game: Game) -> str:
        data = {
            "rows": 19,
            "columns": 19,
            "firstPlayerStone": 0,
            "timeControl": {
                "mainTimeSeconds": 300,
                "incrementSeconds": 10,
            },
            "rankedOrCasual": 0,
        }
        response = self.client.post(
            self.s_create_game, json=data, headers=self.get_headers()
        )
        data = response.json()
        print(data)
        game_id = data["gameId"]
        game.set_id(game_id)

    def join_game(self, game: Game):
        data = {
            "gameId": game.id,
        }
        response = self.client.post(
            self.s_join_game, json=data, headers=self.get_headers()
        )
        print(response.json())

    @task
    def keep_alive(self):
        # This basically emulates that user is calling random endpoints all the time
        sleep(5)
        self.client.get("/")

    @task
    def make_move(self):
        sleep(2)

        if self.game.player2 is None:
            return

        print("Adding move: ", self.p.color)

        self.game.game_reader.add_callback(
            action=Action(
                col=self.p.color, callback=lambda x, y: self.__make_move(x, y)
            ),
        )

    def __make_move(self, a: int, b: int):
        data = {"x": a, "y": b}
        response = self.client.post(
            self.s_make_move(),
            json=data,
            headers=self.get_headers(),
        )

        print("Make Move: ", response.json())
