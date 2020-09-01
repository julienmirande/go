class PlayerInterface():
    # Returns your player name, as to be displayed during the game
    def getPlayerName(self):
        return "Not Defined"

    # Returns your move. The move must be a valid string of coordinates ("A1", 
    # "D5", ...) on the grid or the special "PASS" move. a couple of two integers,
    # which are the coordinates of where you want to put your piece on the board.
    # Coordinates are the coordinates given by the Goban.py method legal_moves().
    def getPlayerMove(self): 
        return "PASS" 

    # Inform you that the oponent has played this move. You must play it with no 
    # search (just update your local variables to take it into account)
    def playOpponentMove(self, move): 
        pass

    # Starts a new game, and give you your color.  As defined in Goban.py : color=1
    # for BLACK, and color=2 for WHITE
    def newGame(self, color): 
        pass

    # You can get a feedback on the winner
    # This function gives you the color of the winner
    def endGame(self, color):
        pass


