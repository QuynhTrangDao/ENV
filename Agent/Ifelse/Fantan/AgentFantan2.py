import numpy as np
from numba import njit
from numba.typed import List
import sys, os
from setup import SHORT_PATH
import importlib.util

game_name = sys.argv[1]


def setup_game(game_name):
    spec = importlib.util.spec_from_file_location(
        "env", f"{SHORT_PATH}Base/{game_name}/env.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


env = setup_game(game_name)

getActionSize = env.getActionSize
getStateSize = env.getStateSize
getAgentSize = env.getAgentSize

getValidActions = env.getValidActions
getReward = env.getReward


def DataAgent():
    return List([np.zeros((1, 1))])


@njit()
def Test(state, per):
    ValidAction = getValidActions(state)
    ValidAction = np.where(ValidAction == 1)[0]
    myCards = np.where(state[0:52] == 1)[0]
    validCards = np.where(state[52:104] == 1)[0]

    returnAction = -1

    #  print("My Cards: ",myCards)
    #  print("Valid Cards: ",validCards)
    #  print("Chip: ", state[104], state[109:112])
    #  print("Other Cards: ", state[105:108])
    #  print(ValidAction)
    #  print("-----------")

    #  for i in range(0,52):
    #      if i in ValidAction and (i%13 != 6) and (i %13 == 0 or i%13 == 12):
    #          return i, per

    if len(myCards) < min(state[105:108]) - 1:
        if min(state[109:112]) >= 10 and 52 in ValidAction:
            return 52, per

    for j in range(5, 0, -1):
        for i in range(0, 52):
            if (
                i in ValidAction
                and (i % 13 != 6)
                and (
                    (i + j in myCards and (i // 13 == (i + j) // 13) and i % 13 > 6)
                    or (i - j in myCards and (i // 13 == (i - j) // 13))
                    and i % 13 < 6
                )
            ):
                return i, per

    for i in range(0, 5):
        for j in range(4):
            if i + j * 13 in ValidAction:
                return i + j * 13, per

            if 12 - i + j * 13 in ValidAction:
                return 12 - i + j * 13, per

    for i in range(0, 52):
        if i in ValidAction and i % 13 != 6:
            return i, per

    for i in range(0, 52):
        if i in ValidAction:
            return i, per

    if returnAction == -1:
        returnAction = ValidAction[np.random.randint(len(ValidAction))]

    return returnAction, per
