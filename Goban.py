# -*- coding: utf-8 -*-

''' This is a class to play small games of GO, natively coded in Python.
    I tried to use nice data structures to speed it up (union & find, Zobrist hashs,
    numpy memory efficient ...)

    Licence is MIT: you can do whatever you want with the code. But keep my name somewhere.

    (c) Laurent SIMON 2019 -- 2020

    Known Limitations:
     - No early detection of endgames (only stops when no stone can be put on the board, or superKo)
    '''

from __future__ import print_function # Used to help cython work well
import numpy as np
import random

def getProperRandom():
    return np.random.randint(np.iinfo(np.int64).max, dtype='int64')

class Board:
    _BLACK = 1
    _WHITE = 2
    _EMPTY = 0
    _BOARDSIZE = 9 # Used in static methods, do not write it
    _DEBUG = False

    def __init__(self):
      self._nbWHITE = 0
      self._nbBLACK = 0
      self._capturedWHITE = 0
      self._capturedBLACK = 0

      self._nextPlayer = self._BLACK
      self._board = np.zeros((Board._BOARDSIZE**2), dtype='int8')

      self._lastPlayerHasPassed = False
      self._gameOver = False

      self._stringUnionFind = np.full((Board._BOARDSIZE**2), -1, dtype='int16')
      self._stringLiberties = np.full((Board._BOARDSIZE**2), -1, dtype='int16')
      self._stringSizes = np.full((Board._BOARDSIZE**2), -1, dtype='int16')

      self._empties = set(range(Board._BOARDSIZE **2))

      # Zobrist values for the hashes. I use np.int64 to be machine independant
      self._positionHashes = np.empty((Board._BOARDSIZE**2, 2), dtype='int64')
      for x in range(Board._BOARDSIZE**2):
            for c in range(2):
                self._positionHashes[x][c] = getProperRandom()
      self._currentHash = getProperRandom()
      self._passHash = getProperRandom()

      self._seenHashes = set()

      self._historyMoveNames = []
      self._trailMoves = [] # data structure used to push/pop the moves

      #Building fast structures for accessing neighborhood
      self._neighbors = []
      self._neighborsEntries = []
      for nl in [self.getNeighbors(fcoord) for fcoord in range(Board._BOARDSIZE**2)] :
          self._neighborsEntries.append(len(self._neighbors))
          for n in nl:
              self._neighbors.append(n)
          self._neighbors.append(-1) # Sentinelle
      self._neighborsEntries = np.array(self._neighborsEntries, dtype='int16')
      self._neighbors = np.array(self._neighbors, dtype='int8')

    def pushBoard(self):
        currentStatus = []
        currentStatus.append(self._nbWHITE)
        currentStatus.append(self._nbBLACK)
        currentStatus.append(self._capturedWHITE)
        currentStatus.append(self._capturedBLACK)
        currentStatus.append(self._nextPlayer)
        currentStatus.append(self._board.copy())
        currentStatus.append(self._gameOver)
        currentStatus.append(self._lastPlayerHasPassed)
        currentStatus.append(self._stringUnionFind.copy())
        currentStatus.append(self._stringLiberties.copy())
        currentStatus.append(self._stringSizes.copy())
        currentStatus.append(self._empties.copy())
        currentStatus.append(self._currentHash)
        self._trailMoves.append(currentStatus)

    def popBoard(self):
        oldStatus = self._trailMoves.pop()
        self._currentHash = oldStatus.pop()
        self._empties = oldStatus.pop()
        self._stringSizes = oldStatus.pop()
        self._stringLiberties = oldStatus.pop()
        self._stringUnionFind = oldStatus.pop()
        self._lastPlayerHasPassed = oldStatus.pop()
        self._gameOver = oldStatus.pop()
        self._board = oldStatus.pop()
        self._nextPlayer = oldStatus.pop()
        self._capturedBLACK = oldStatus.pop()
        self._capturedWHITE = oldStatus.pop()
        self._nbBLACK = oldStatus.pop()
        self._nbWHITE = oldStatus.pop()
        self._historyMoveNames.pop()

    def getPositionHash(self, fcoord, color):
        return self._positionHashes[fcoord][color-1]

    @staticmethod
    def flatten(coord):
        return Board._BOARDSIZE * coord[0] + coord[1]

    @staticmethod
    def unflatten(fcoord):
        return divmod(fcoord, Board._BOARDSIZE)

    @staticmethod
    def flip(player):
        if player == Board._BLACK:
            return Board._WHITE
        return Board._BLACK

    @staticmethod
    def playerName(player):
        if player == Board._BLACK:
            return "black"
        elif player == Board._WHITE:
            return "white"
        return "???"

    # Used only in init to build the neighborsEntries datastructure
    def getNeighbors(self, fcoord):
        x, y = Board.unflatten(fcoord)
        neighbors = ((x+1, y), (x-1, y), (x, y+1), (x, y-1))
        return [Board.flatten(c) for c in neighbors if self._isOnBoard(c[0], c[1])]

    # for union find structure, recover the number of the current string of stones
    def getStringOfStone(self, fcoord):
        successives = []
        while self._stringUnionFind[fcoord] != -1:
            fcoord = self._stringUnionFind[fcoord]
            successives.append(fcoord)
        if len(successives) > 1:
            for fc in successives[:-1]:
                self._stringUnionFind[fc] = fcoord
        return fcoord

    def mergeStringNumber(self, str1, str2):
        #print("merge ", str1, str2)
        self._stringLiberties[str1] += self._stringLiberties[str2]
        self._stringLiberties[str2] = -1
        self._stringSizes[str1] += self._stringSizes[str2]
        self._stringSizes[str2] = -1
        assert self._stringUnionFind[str2] == -1
        self._stringUnionFind[str2] = str1

    def putStone(self, fcoord, color):
        self._board[fcoord] = color
        self._currentHash ^= self.getPositionHash(fcoord, color)
        if self._DEBUG:
            assert fcoord in self._empties
        self._empties.remove(fcoord)

        nbEmpty = 0
        nbSameColor = 0
        i = self._neighborsEntries[fcoord]
        while self._neighbors[i] != -1:
            n = self._board[self._neighbors[i]]
            if  n == Board._EMPTY:
                nbEmpty += 1
            elif n == color:
                nbSameColor += 1
            i += 1
        nbOtherColor = 4 - nbEmpty - nbSameColor
        currentString = fcoord
        self._stringLiberties[currentString] = nbEmpty
        self._stringSizes[currentString] = 1

        stringWithNoLiberties = [] # String to capture (if applies)
        i = self._neighborsEntries[fcoord]
        while self._neighbors[i] != -1:
            fn = self._neighbors[i]
            if self._board[fn] == color: # We may have to merge the strings
                stringNumber = self.getStringOfStone(fn)
                self._stringLiberties[stringNumber] -= 1
                if currentString != stringNumber:
                    self.mergeStringNumber(stringNumber, currentString)
                currentString = stringNumber
            elif self._board[fn] != Board._EMPTY: # Other color
                stringNumber = self.getStringOfStone(fn)
                self._stringLiberties[stringNumber] -= 1
                if self._stringLiberties[stringNumber] == 0:
                    if stringNumber not in stringWithNoLiberties: # We may capture more than one string
                        stringWithNoLiberties.append(stringNumber)
            i += 1

        if Board._DEBUG: # Checks that the board is locally consistent
            string, reached = self.breadthSearchStringAndReached(fcoord)
            assert self._board[fcoord] == color
            assertString = self.getStringOfStone(fcoord)
            looseLiberty = 0 # Checks that my liberties are loosely counted
            for fc in string:
                assert assertString == self.getStringOfStone(fc)
                i = self._neighborsEntries[fc]
                while self._neighbors[i] != -1:
                    fn = self._neighbors[i]
                    assert self._board[fn] == color or fn in reached
                    if self._board[fn] == Board._EMPTY:
                        looseLiberty += 1
                    i += 1
            assert looseLiberty == self._stringLiberties[assertString]
            realLiberty = sum(1 for fc in reached if self._board[fc] == Board._EMPTY)
            assert self._stringLiberties[assertString] >= realLiberty
            assert len(string) == self._stringSizes[assertString]

        return stringWithNoLiberties

    def reset(self):
        self.__init__()


    def _isOnBoard(self,x,y):
        return x >= 0 and x < Board._BOARDSIZE and y >= 0 and y < Board._BOARDSIZE

    def isSuicide(self, fcoord, color):
        opponent = Board.flip(color)
        i = self._neighborsEntries[fcoord]
        libertiesFriends = {}
        libertiesOpponents = {}
        while self._neighbors[i] != -1:
            fn = self._neighbors[i]
            if self._board[fn] == Board._EMPTY:
                return False
            string = self.getStringOfStone(fn)
            if self._board[fn] == color: # check that we don't kill the whole zone
                if string not in libertiesFriends:
                    libertiesFriends[string] = self._stringLiberties[string] - 1
                else:
                    libertiesFriends[string] -= 1
            else:
                if Board._DEBUG:
                    assert self._board[fn] == opponent
                if string not in libertiesOpponents:
                    libertiesOpponents[string] = self._stringLiberties[string] - 1
                else:
                    libertiesOpponents[string] -= 1
            i += 1

        for s in libertiesOpponents:
            if libertiesOpponents[s] == 0:
                return False # At least one capture right after this move, it is legal

        if len(libertiesFriends) == 0: # No a single friend there...
            return True

        # Now checks that when we connect all the friends, we don't create
        # a zone with 0 liberties
        sumLibertiesFriends = 0
        for s in libertiesFriends:
            sumLibertiesFriends += libertiesFriends[s]
        if sumLibertiesFriends == 0:
            return True # At least one friend zone will be captured right after this move, it is unlegal

        return False

    # Checks if the move leads to an already seen board
    def isSuperKo(self, fcoord, color):
        # Check if it is a complex move (if it takes at least a stone)
        tmpHash = self._currentHash ^ self.getPositionHash(fcoord, color)
        assert self._currentHash == tmpHash ^ self.getPositionHash(fcoord, color)
        i = self._neighborsEntries[fcoord]
        libertiesOpponents = {}
        opponent = Board.flip(color)
        while self._neighbors[i] != -1:
            fn = self._neighbors[i]
            #print("superko looks at ", self.coordToName(fn), "for move", self.coordToName(fcoord))
            if self._board[fn] == opponent:
                s = self.getStringOfStone(fn)
                #print("superko sees string", self.coordToName(s))
                if s not in libertiesOpponents:
                    libertiesOpponents[s] = self._stringLiberties[s] - 1
                else:
                    libertiesOpponents[s] -= 1
            i += 1

        for s in libertiesOpponents:
            if libertiesOpponents[s] == 0:
                #print("superko computation for move ", self.coordToName(fcoord), ":")
                for fn in self.breadthSearchString(s):
                    #print(self.coordToName(fn)+" ", end="")
                    assert self._board[fn] == opponent
                    tmpHash ^= self.getPositionHash(fn, opponent)
                #print()

        if tmpHash in self._seenHashes:
            return True, tmpHash
        return False, tmpHash

    # Too costly to be used in all the cases
    def breadthSearchStringAndReached(self, fc):
        color = self._board[fc]
        string = set([fc])
        reached = set()
        frontier = [fc]
        while frontier:
            current_fc = frontier.pop()
            string.add(current_fc)
            i = self._neighborsEntries[current_fc]
            while self._neighbors[i] != -1:
                fn = self._neighbors[i]
                i += 1
                if self._board[fn] == color and not fn in string:
                    frontier.append(fn)
                elif self._board[fn] != color:
                    reached.add(fn)
        return string, reached

    # Too costly to be used in all the cases
    def breadthSearchString(self, fc):
        color = self._board[fc]
        string = set([fc])
        frontier = [fc]
        while frontier:
            current_fc = frontier.pop()
            string.add(current_fc)
            i = self._neighborsEntries[current_fc]
            while self._neighbors[i] != -1:
                fn = self._neighbors[i]
                i += 1
                if self._board[fn] == color and not fn in string:
                    frontier.append(fn)
        return string

    #deprecated: will be removed
    def winner(self):
        totalWhite = 0
        totalBlack = 0
        for m in range(self._BOARDSIZE**2):
            if self._board[m] == Board._WHITE:
                totalWhite += 1
            elif self._board[m] == Board._BLACK:
                totalBlack += 1
        if totalWhite > totalBlack:
            return Board._BLACK
        if totalWhite < totalBlack:
            return Board._WHITE
        return Board._EMPTY


    def isGameOver(self):
        return  self._gameOver

    def is_game_over(self):
        return self._gameOver

    # Renvoi la liste des coups possibles
    # Note: cette méthode pourrait être codée plus efficacement
    def legal_moves(self):
        moves = [Board.coordToName(m) for m in self._empties if not self.isSuicide(m, self._nextPlayer) and not self.isSuperKo(m,
            self._nextPlayer)[0]]
        moves.append("PASS") # We can always ask to pass
        return moves

    # Kept for my own retro-compatibility
    def legalMoves(self):
        return self.legal_moves()

    # Kept for my own retro-compatibility
    def generate_legal_moves(self):
        return self.legalMoves()

    def _piece2str(self, c):
        if c==self._WHITE:
            return 'O'
        elif c==self._BLACK:
            return 'X'
        else:
            return '.'

    def __str__(self):
        toreturn=""
        for i,c in enumerate(self._board):
            toreturn += self._piece2str(c) + " " # +'('+str(i)+":"+str(self._stringUnionFind[i])+","+str(self._stringLiberties[i])+') '
            if (i+1) % Board._BOARDSIZE == 0:
                toreturn += "\n"
        toreturn += "Next player: " + ("BLACK" if self._nextPlayer == self._BLACK else "WHITE") + "\n"
        toreturn += str(self._nbBLACK) + " blacks and " + str(self._nbWHITE) + " whites on board\n"
        return toreturn

    def prettyPrint(self):
        if Board._BOARDSIZE not in [5,7,9]:
            print(self)
            return
        print()
        print("To Move: ", "black" if self._nextPlayer == Board._BLACK else "white")
        print("Last player has passed: ", "yes" if self._lastPlayerHasPassed else "no")
        print()
        print("     WHITE (O) has captured %d stones" % self._capturedBLACK)
        print("     BLACK (X) has captured %d stones" % self._capturedWHITE)
        print()
        print("     WHITE (O) has %d stones" % self._nbWHITE)
        print("     BLACK (X) has %d stones" % self._nbBLACK)
        print()
        if Board._BOARDSIZE == 9:
            specialPoints = [(2,2), (6,2), (4,4), (2,6), (6,6)]
            headerline = "    A B C D E F G H J"
        elif Board._BOARDSIZE == 7:
            specialPoints = [(2,2), (4,2), (3,3), (2,4), (4,4)]
            headerline = "    A B C D E F G"
        else:
            specialPoints = [(1,1), (3,1), (2,2), (1,3), (3,3)]
            headerline = "    A B C D E"
        print(headerline)
        for l in range(Board._BOARDSIZE):
            line = Board._BOARDSIZE - l
            print("  %d" % line, end="")
            for c in range(Board._BOARDSIZE):
                p = self._board[Board.flatten((l,c))]
                ch = '.'
                if p==Board._WHITE:
                    ch = 'O'
                elif p==Board._BLACK:
                    ch = 'X'
                elif (l,c) in specialPoints:
                    ch = '+'
                print(" " + ch, end="")
            print(" %d" % line)
        print(headerline)
        print("hash = ", self._currentHash)

    @staticmethod
    def moveNameToCoord(s):
        if s == 'PASS': return -1
        indexLetters = {'A':0, 'B':1, 'C':2, 'D':3, 'E':4, 'F':5, 'G':6, 'H':7, 'J':8}

        col = indexLetters[s[0]]
        lin = Board._BOARDSIZE - int(s[1:])
        return (lin, col)

    @staticmethod
    def coordToName(fcoord):
        if fcoord == -1: return 'PASS'
        letterIndex = "ABCDEFGHJ"
        line = fcoord // Board._BOARDSIZE
        col = letterIndex[fcoord % Board._BOARDSIZE ]
        return col+str(Board._BOARDSIZE - line)

    def captureString(self, fc):
        string = self.breadthSearchString(fc)
        for s in string:
            if self._nextPlayer == Board._WHITE:
                self._capturedBLACK += 1
                self._nbBLACK -= 1
            else:
                self._capturedWHITE += 1
                self._nbWHITE -= 1
            self._currentHash ^= self.getPositionHash(s, self._board[s])
            self._board[s] = self._EMPTY
            self._empties.add(s)
            i = self._neighborsEntries[s]
            while self._neighbors[i] != -1:
                fn = self._neighbors[i]
                if self._board[fn] != Board._EMPTY:
                    st = self.getStringOfStone(fn)
                    if st != s:
                        self._stringLiberties[st] += 1
                i += 1
            self._stringUnionFind[s] = -1
            self._stringSizes[s] = -1
            self._stringLiberties[s] = -1

    def fullPlayMove(self, fcoord):
        if self._gameOver: return
        if fcoord != -1:  # pass otherwise
            tmpHash = self.isSuperKo(fcoord, self._nextPlayer)[1]
            captured = self.putStone(fcoord, self._nextPlayer)

            # captured is the list of Strings that have 0 liberties
            for fc in captured:
                self.captureString(fc)

            assert tmpHash == self._currentHash
            self._lastPlayerHasPassed = False
            if self._nextPlayer == self._WHITE:
                self._nbWHITE += 1
            else:
                self._nbBLACK += 1
        else:
            if self._lastPlayerHasPassed:
                self._gameOver = True
            else:
                self._lastPlayerHasPassed = True
            self._currentHash ^= self._passHash

        self._seenHashes.add(self._currentHash)
        self._historyMoveNames.append(self.coordToName(fcoord))
        self._nextPlayer = Board.flip(self._nextPlayer)

    def playNamedMove(self, m):
        if m != "PASS":
            self.fullPlayMove(self.flatten(Board.moveNameToCoord(m)))
        else:
            self.fullPlayMove(-1)

    def push(self, m):
        assert not self._gameOver
        self.pushBoard()
        self.playNamedMove(m)

    def pop(self):
        hashtopop = self._currentHash
        self.popBoard()
        if hashtopop in self._seenHashes:
            self._seenHashes.remove(hashtopop)

    def result(self):
        if self._nbWHITE > self._nbBLACK:
            return "1-0"
        elif self._nbWHITE < self._nbBLACK:
            return "0-1"
        else:
            return "1/2-1/2"
