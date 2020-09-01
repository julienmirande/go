# -*- coding: utf-8 -*-

import time
import Goban
from random import randint, choice
from playerInterface import *

class randomPlayer(PlayerInterface):

    def __init__(self):
        self._board = Goban.Board()
        self._mycolor = None

    def getPlayerName(self):
        return "Random Player"

    def getPlayerMove(self):
        if self._board.is_game_over():
            print("Referee told me to play but the game is over!")
            return "PASS"
        moves = self._board.legal_moves()
        move = choice(moves)
        self._board.push(move)
        print("I am playing ", move)
        print("My current board :")
        self._board.prettyPrint()
        return move

    def playOpponentMove(self, move):
        print("Opponent played ", move)
        self._board.push(move)

    def newGame(self, color):
        self._mycolor = color
        self._opponent = Goban.Board.flip(color)

    def endGame(self, winner):
        if self._mycolor == winner:
            print("I won!!!")
        else:
            print("I lost :(!!")
