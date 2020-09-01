import Goban
import myPlayer
import randomPlayer
import time
from io import StringIO
import sys

b = Goban.Board()

players = []
player1 = myPlayer.myPlayer()
player1.newGame(Goban.Board._BLACK)
players.append(player1)
player2 = randomPlayer.randomPlayer()
player2.newGame(Goban.Board._WHITE)
players.append(player2)

totalTime = [0,0] # total real time for each player
nextplayer = 0
nextplayercolor = Goban.Board._BLACK
nbmoves = 1

outputs = ["",""]
sysstdout= sys.stdout
stringio = StringIO()
# Probleme : quand on est en fin de partie, le ID est relance des milliers de fois avec une profondeur max tres grande
#print(b.legal_moves())
wrongmovefrom = 0
while not b.is_game_over():
    print("Referee Board:")
    b.prettyPrint()
    print("Before move", nbmoves)
    legals = b.legal_moves()
    print("Legal Moves: ", legals)
    nbmoves += 1
    otherplayer = (nextplayer + 1) % 2
    othercolor = Goban.Board.flip(nextplayercolor)

    currentTime = time.time()
    sys.stdout = stringio
    move = players[nextplayer].getPlayerMove()
    sys.stdout = sysstdout
    playeroutput = "\r" + stringio.getvalue()
    stringio.truncate(0)
    print(("[Player "+str(nextplayer) + "] ").join(playeroutput.splitlines(True)))
    outputs[nextplayer] += playeroutput
    totalTime[nextplayer] += time.time() - currentTime
    print("Player ", nextplayercolor, players[nextplayer].getPlayerName(), "plays" + str(move))
    if not move in legals:
        print(otherplayer, nextplayer, nextplayercolor)
        print("Problem: illegal move")
        wrongmovefrom = nextplayercolor
        break
    b.push(move)
    players[otherplayer].playOpponentMove(move)

    nextplayer = otherplayer
    nextplayercolor = othercolor

print("The game is over")
b.prettyPrint()
result = b.result()
print("Time:", totalTime)
print("Winner: ", end="")
if wrongmovefrom > 0:
    if wrongmovefrom == b._WHITE:
        print("BLACK")
    elif wrongmovefrom == b._BLACK:
        print("WHITE")
    else:
        print("ERROR")
elif result == "1-0":
    print("WHITE")
elif result == "0-1":
    print("BLACK")
else:
    print("DEUCE")
