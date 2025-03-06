# Intro

Load testing my FossGo server

Used locust library.

The program emulates user behaviour

1. logging in.
2. Creating game/Joining Created game.
3. Playing moves by turn.

This repo doesn't really serve any purpose beyond initial testing, but i'm just putting here for reference.

If you wanna run it for fun.

1. Install [requirements](./requirements.txt) `pip install -r requirements.txt`
2. Set BASE_URL environment variable to point to a FossGo server.
3. Run `locust`
4. All players are playing the same game, reading the [game](./DRKCCHFCDK.sgf) file.
5. Watch as the players make moves in locust dashboard :)
