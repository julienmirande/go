# -*- coding: utf-8 -*-

import math
import time
import Goban
from random import randint, choice
from playerInterface import *

class myPlayer(PlayerInterface):

    def __init__(self):
        self._board = Goban.Board()
        self._mycolor = None

    def getPlayerName(self):
        return "My Player"

    def getPlayerMove(self):
        if self._board.is_game_over():
            print("Referee told me to play but the game is over!")
            return "PASS"
        move,_ = self.MaxMinCoupAB(2)
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


    '''
    retourne le meilleur coup à jouer et sa valeur, selon
    une recherche MinMax + AlphaBeta à profondeur depth
    '''
    def MaxMinCoupAB(self, depth=3):
        if self._board.is_game_over() or depth == 0:
            return None

        v, coup = None, None
        bestMoves = []
        alpha = -math.inf
        beta = math.inf
        for m in self._board.legal_moves():
            self._board.push(m)
            ret = self.MinMaxAB(alpha, beta, depth - 1)
            if v is None or ret > v:
                bestMoves.clear()
                bestMoves.append(m)
                v = ret
            elif v is None or ret == v:
                bestMoves.append(m)
            self._board.pop()

        coup = choice(bestMoves)
        return (coup, v)

    def MaxMinAB(self, alpha, beta, depth=3):
        if self._board.is_game_over():
            res = self._board.result()
            if res == "1-0":
                return 400
            elif res == "0-1":
                return -400
            else:
                return 0

        if depth == 0:
            return self.evaluate()

        for m in self._board.legal_moves():
            self._board.push(m)
            ret = self.MinMaxAB(alpha, beta, depth - 1)
            alpha = max(alpha, ret)
            self._board.pop()
            if alpha >= beta:
                return beta

        return alpha

    def MinMaxAB(self, alpha, beta, depth=3):
        if self._board.is_game_over():
            res = self._board.result()
            if res == "1-0":
                return 400
            elif res == "0-1":
                return -400
            else:
                return 0

        if depth == 0:
            return self.evaluate()

        for m in self._board.legal_moves():
            self._board.push(m)
            ret = self.MaxMinAB(alpha, beta, depth - 1)
            beta = min(beta, ret)
            self._board.pop()
            if alpha >= beta:
                return alpha

        return beta


    def canReach(m, color):
        return 0


    # calcule la différence de score entre le joueur et l'adversaire
    def computeScore(self):
        myScore = 0
        oppScore = 0
        for m in range(self._board._BOARDSIZE**2):
            if self._board._board[m] == self._mycolor:
                myScore += 1
            elif self._board._board[m] == self._opponent:
                oppScore += 1
                '''
            else:
                if canReach(m, self._mycolor) and not (canReach(m, self._opponent)):
                    myScore += 1
                elif not (canReach(m, self._mycolor)) and canReach(m, self._opponent):
                    oppScore += 1
                    '''
        return myScore - oppScore

    def computeScore2(self):
        #print("Score :", (self._board._nbWHITE + self._board._capturedBLACK) - (self._board._nbBLACK + self._board._capturedWHITE), "----------------------------------------------------------------")
        return (self._board._nbWHITE + self._board._capturedBLACK) - (self._board._nbBLACK + self._board._capturedWHITE)

    def evaluate(self):
        return self.computeScore()
