import numpy as np
from numba import njit, jit
from index import*

@njit(fastmath=True, cache=True)
def getActionSize():
    return 54

@njit(fastmath=True, cache=True)
def getAgentSize():
    return 4

@njit()
def getStateSize():
    return 130


@njit()
def initEnv():
    normal_card = np.full(NUMBER_TYPE_NORMAL_CARD, NUMBER_PER_NORMAL_CARD)
    start_player = np.concatenate((np.array([0, 1, 0, 1]), np.zeros(16)))
    card_buy_in_turn = np.zeros(NUMBER_TYPE_NORMAL_CARD)
    env_state = np.concatenate((start_player, start_player, start_player, start_player, normal_card, card_buy_in_turn, np.array([-0.5, 0, 0, 0, 0, 1, 0])))
    #[card_sell, player_continue, last_dice, picked_player, id_action, phase, check_end_game]
    return env_state

@njit()
def getAgentState(env_state):
    player_state = np.zeros(P_LENGTH, dtype= np.int32)
    player_action = int(env_state[ENV_ID_ACTION])
    player_state[: ATTRIBUTE_PLAYER] = env_state[ATTRIBUTE_PLAYER * player_action : ATTRIBUTE_PLAYER * (player_action + 1)]
    for idx in range(1, 4): 
        id = int((player_action + idx)%4)
        all_other_player_in4 = env_state[ATTRIBUTE_PLAYER * id : ATTRIBUTE_PLAYER * (id + 1)]
        player_state[ATTRIBUTE_PLAYER * idx : ATTRIBUTE_PLAYER * (idx + 1)] = all_other_player_in4
    player_state[P_NORMAL_CARD : P_CARD_SELL] = env_state[ENV_NORMAL_CARD : ENV_CARD_SELL]
    #card sell
    if env_state[ENV_CARD_SELL] != -0.5:
        player_state[P_CARD_SELL + int(env_state[ENV_CARD_SELL])] = 1
    #player_continue
    player_state[P_PLAYER_CONTINUE] = env_state[ENV_PLAYER_CONTINUE]
    player_state[P_LAST_DICE] = env_state[ENV_LAST_DICE]
    #người chơi bị chọn
    if env_state[ENV_PICKED_PLAYER] != 0:
        # print(list(env_state))
        player_state[P_PICKED_PLAYER + int(env_state[ENV_PICKED_PLAYER] )] = 1
    #phase game
    player_state[P_PHASE + int(env_state[ENV_PHASE] - 1)] = 1
    #check end game
    player_state[P_CHECK_END] = env_state[ENV_CHECK_END]
    return player_state

@njit()
def getValidActions(player_state_origin):
    list_action_return = np.zeros(getActionSize(), dtype= np.int32)
    player_state = player_state_origin.copy()
    # phase_env = np.where(player_state[P_PHASE : P_PHASE + NUMBER_PHASE] == 1)[0][0] + 1
    phase_env = -1
    if len(np.where(player_state[P_PHASE : P_PHASE + NUMBER_PHASE] == 1)[0]) != 0:
        phase_env = np.where(player_state[P_PHASE : P_PHASE + NUMBER_PHASE] == 1)[0][0] + 1
    player_state_own = player_state[:ATTRIBUTE_PLAYER]
    '''
        Quy ước phase: 
        phase1: chọn xúc sắc để đổ
        phase2: chọn đổ lại hay k
        phase3: chọn lấy tiền của ai
        phase4: chọn người để đổi
        phase5: chọn lá bài để đổi
        phase6: chọn lá bài muốn lấy
        phase7: chọn mua thẻ
    '''
    # print('PHASE', phase_env)
    if phase_env == 1:
        if player_state_own[-1] != 0:
        #chọn số xúc sắc để đổ: 1 ứng với 1 xúc sắc, 2 ứng với 2 xúc sắc
            list_action_return[np.array([1, 2])] = 1 
        else:
            list_action_return[1] = 1
        
    elif phase_env == 2:
        #chọn đổ lại hay k, 0 là ko, 1 là đổ 1, 2 là đổ 2 
        list_action_return[np.array([0, 1, 2])] = 1
    
    elif phase_env == 3:
        #3, 4, 5 lần lượt là lấy tiền của người ở vị trí 1,2,3 sau mình
        all_player_coin = np.array([player_state[ATTRIBUTE_PLAYER], player_state[ATTRIBUTE_PLAYER * 2], player_state[ATTRIBUTE_PLAYER * 3]])
        id_can_stole = np.where(all_player_coin > 0)[0]
        list_action_return[id_can_stole + 3 ] = 1

    elif phase_env == 4:
        #6, 7, 8 lần lượt là chọn đổi thẻ với người ở vị trí 1,2,3 sau mình, 9 là ko đổi với ai
        list_action_return[np.array([6, 7, 8, 9])] = 1

    elif phase_env == 5:
        #duyệt trong các thẻ đang có, có thẻ nào đổi được thì đưa vào list_action range(10, 22)
        list_action = np.where(player_state_own[1 : 1 + NUMBER_TYPE_NORMAL_CARD] > 0)[0] + 10
        list_action_return[list_action] = 1
    elif phase_env == 6:
        #duyệt trong các thẻ của người chơi mình muốn đổi range(22-34)
        player_picked = np.where(player_state[P_PICKED_PLAYER : P_PICKED_PLAYER + NUMBER_PLAYER])[0][0]
        player_picked_card = player_state[ATTRIBUTE_PLAYER * player_picked : ATTRIBUTE_PLAYER * (player_picked + 1)][1 : 1 + NUMBER_TYPE_NORMAL_CARD]
        list_action_return[np.where(player_picked_card>0)[0] + 22 ] = 1

    elif phase_env == 7:
        #chọn mua thẻ, hành động trải từ 34-53 với 53 là hành động bỏ qua ko mua thêm
        list_action_return[53] = 1
        p_coin = player_state[0]
        card_board = player_state[P_NORMAL_CARD : P_CARD_BUY_IN_TURN]
        card_bought = player_state[P_CARD_BUY_IN_TURN : P_CARD_SELL]
        if p_coin > 0:
            if card_board[0] > 0 and card_bought[0] == 0:
                #mua thẻ lúa mì
                list_action_return[34] = 1
        if p_coin > 0:
            if card_board[1] > 0 and card_bought[1] == 0:
                #mua thẻ nông trại
                list_action_return[35] = 1
        if p_coin > 0 :
            if card_board[2] > 0 and card_bought[2] == 0:
                #mua thẻ tiệm bánh
                list_action_return[36] = 1
        if p_coin > 1 :
            if card_board[3] > 0 and card_bought[3] == 0:
                #mua thẻ quán cà phê
                list_action_return[37] = 1
        if p_coin > 1 :
            if card_board[4] > 0 and card_bought[4] == 0:
                #mua thẻ cửa hàng tiện lợi
                list_action_return[38] = 1
        if p_coin > 2 :
            if card_board[5] > 0 and card_bought[5] == 0:
                #mua thẻ rừng
                list_action_return[39] = 1
        if p_coin > 4 :
            if card_board[6] > 0 and card_bought[6] == 0:
                #mua thẻ nhà máy pho mát
                list_action_return[40] = 1
        if p_coin > 2 :
            if card_board[7] > 0 and card_bought[7] == 0:
                #mua thẻ nhà máy nội thất
                list_action_return[41] = 1
        if p_coin > 5 :
            if card_board[8] > 0 and card_bought[8] == 0:
                #mua thẻ mỏ quặng
                list_action_return[42] = 1
        if p_coin > 2 :
            if card_board[9] > 0 and card_bought[9] == 0:
                #mua thẻ quán ăn gia đình
                list_action_return[43] = 1
        if p_coin > 2 :
            if card_board[10] > 0 and card_bought[10] == 0:
                #mua thẻ vườn táo
                list_action_return[44] = 1
        if p_coin > 1 :
            if card_board[11] > 0 and card_bought[11] == 0:
                #mua thẻ chợ trái cây
                list_action_return[45] = 1

        if p_coin > 5 :
            if player_state_own[13] == 0:
                #mua thẻ sân vận động
                list_action_return[46] = 1
        if p_coin > 6 :
            if player_state_own[14] == 0:
                #mua thẻ đài truyền hình
                list_action_return[47] = 1
        if p_coin > 7 :
            if player_state_own[15] == 0:
                #mua thẻ trung tâm thương mại
                list_action_return[48] = 1

        if p_coin > 3:
            if player_state_own[-1] == 0:
                #mua thẻ 22 coin
                list_action_return[52] = 1
        if p_coin > 9:
            if player_state_own[-2] == 0:
                #mua thẻ 16 coin
                list_action_return[51] = 1
        if p_coin > 15:
            if player_state_own[-3] == 0:
                #mua thẻ 10 coin
                list_action_return[50] = 1
        if p_coin > 21:
            if player_state_own[-4] == 0:
                #mua thẻ 4 coin
                list_action_return[49] = 1

    return list_action_return

@njit()
def stepEnv(env_state, action):
    phase_env = env_state[ENV_PHASE]
    id_action = int(env_state[ENV_ID_ACTION])
    player_in4 = env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)]

    if phase_env == 1:
        dice1 = 0
        dice2 = 0
        if action == 1:     #nếu đổ 1 xúc sắc
            dice1 = np.random.randint(1,7)
            dice = dice1
        elif action == 2:               #nếu đổ 2 xúc sắc
            dice1 = np.random.randint(1,7)
            dice2 = np.random.randint(1,7)
            dice =  dice1 + dice2
        env_state[ENV_LAST_DICE] = dice
        if player_in4[-3] != 0 and dice1 == dice2 and dice1 != 0:
            #đánh dấu là được đổ tiếp
            env_state[ENV_PLAYER_CONTINUE] = 1
        if player_in4[-4] > 0:
            #nếu đổ lại đc thì truyền xem có đổ lại k
            env_state[-ENV_LAST_DICE] = dice
            env_state[ENV_PHASE] = 2
        else:
            if dice == 1:
                for id in range(4):
                    env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 1]

            elif dice == 2:
                for id in range(4):
                    env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 2]

                if player_in4[-2] > 0:
                    env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 3] * 2
                else:
                    env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 3] 

            elif dice == 3:
                next = 1
                while 0 < player_in4[0] and next <= 3:
                    id_next = (id_action - next) % 4
                    player_id = env_state[ATTRIBUTE_PLAYER * id_next : ATTRIBUTE_PLAYER * (id_next + 1)]
                    coin_get = player_id[4] * (1 + int(player_id[-2] > 0))
                    delta_coin = min(coin_get, player_in4[0])
                    player_id[0] += delta_coin
                    player_in4[0] -= delta_coin
                    env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                    next += 1

                player_in4[0] += player_in4[3] * (1 + int(player_in4[-2] > 0))          #cộng tiền từ tiệm bánh

                env_state[ATTRIBUTE_PLAYER * id_action] = player_in4[0]   #cập nhật tiền của người chơi

            elif dice == 4:
                if player_in4[-2] > 0:
                    env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 5] * 4
                else:
                    env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 5] * 3 

            elif dice == 5:
                for id in range(4):
                    env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 6]

            elif dice == 6:
                if player_in4[13] > 0:
                    for next in range(1,4):
                        id_next = (id_action + next) % 4
                        delta_coin = min(2, env_state[ATTRIBUTE_PLAYER * id_next])
                        env_state[ATTRIBUTE_PLAYER * id_next] -= delta_coin
                        player_in4[0] += delta_coin
                    env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4

                all_other_player_coin = np.zeros(3)
                for next in range(1, 4):
                    all_other_player_coin[next-1] = env_state[ATTRIBUTE_PLAYER * ((id_action + next) % 4)]


                if player_in4[14] > 0 and np.sum(all_other_player_coin) > 0:      #nếu có thẻ đài truyền hình
                    env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
                    env_state[ENV_PHASE] = 3           #trạng thái chọn người để lấy tiền
                    return env_state
                else:
                    if player_in4[15] > 0:  #nếu có thẻ trung tâm thương mại
                        env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
                        env_state[ENV_PHASE] = 4       #trạng thái chọn người để đổi thẻ
                        return env_state

            elif dice == 7:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 7] * env_state[ATTRIBUTE_PLAYER * id_action + 2] * 3

            elif dice == 8:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 8] * (env_state[ATTRIBUTE_PLAYER * id_action + 6] + env_state[ATTRIBUTE_PLAYER * id_action + 9]) * 3

            elif dice == 9:
                
                next = 1
                while 0 < player_in4[0] and next <= 3:
                    id_next = (id_action - next) % 4
                    player_id = env_state[ATTRIBUTE_PLAYER * id_next : ATTRIBUTE_PLAYER * (id_next + 1)]
                    coin_get = player_id[10] * (2 + int(player_id[-2] > 0))
                    delta_coin = min(coin_get, player_in4[0])
                    player_id[0] += delta_coin
                    player_in4[0] -= delta_coin
                    env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                    next += 1
                for id in range(4):
                    env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 9] * 5
                env_state[ATTRIBUTE_PLAYER * id_action] = player_in4[0]   #cập nhật tiền của người chơi

            elif dice == 10:
                
                next = 1
                while 0 < player_in4[0] and next <= 3:
                    id_next = (id_action - next) % 4
                    player_id = env_state[ATTRIBUTE_PLAYER * id_next : ATTRIBUTE_PLAYER * (id_next + 1)]
                    coin_get = player_id[10] * (2 + int(player_id[-2] > 0))
                    delta_coin = min(coin_get, player_in4[0])
                    player_id[0] += delta_coin
                    player_in4[0] -= delta_coin
                    env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                    next += 1
                for id in range(4):
                    env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 11] * 3
                env_state[20 * id_action] = player_in4[0]   #cập nhật tiền của người chơi

            elif dice == 11 or dice == 12:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 12] * (env_state[ATTRIBUTE_PLAYER * id_action + 1] + env_state[ATTRIBUTE_PLAYER * id_action + 11]) * 3
            #sau khi cập nhật xu, cho roll tiếp nếu đạt yêu cầu, giảm biến đánh dấu xuống
            if env_state[ENV_PLAYER_CONTINUE] == 1:
                env_state[ENV_PHASE] = 1
                env_state[ENV_PLAYER_CONTINUE] = 0
            else:
                if env_state[ENV_PHASE] == 1:
                    env_state[ENV_PHASE] = 7
                           
    elif phase_env == 2:
        dice = 0
        dice1 = 0
        dice2 = 0
        if action == 0:
            dice = env_state[ENV_LAST_DICE]
        elif action == 1:
            env_state[ENV_PLAYER_CONTINUE] = 0
            dice1 = np.random.randint(1,7)
            dice = dice1
        elif action == 2:
            env_state[ENV_PLAYER_CONTINUE] = 0
            dice1 = np.random.randint(1,7)
            dice2 = np.random.randint(1,7)
            dice =  dice1 + dice2
        
        env_state[ENV_LAST_DICE] = dice
        if player_in4[-3] != 0 and dice1 == dice2 and dice1 != 0:
            #đánh dấu là được đổ tiếp
            env_state[ENV_PLAYER_CONTINUE] = 1
  
        if dice == 1:
            for id in range(4):
                env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 1]

        elif dice == 2:
            for id in range(4):
                env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 2]

            if player_in4[-2] > 0:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 3] * 2
            else:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 3] 

        elif dice == 3:
            next = 1
            while 0 < player_in4[0] and next <= 3:
                id_next = (id_action - next) % 4
                player_id = env_state[ATTRIBUTE_PLAYER * id_next : ATTRIBUTE_PLAYER * (id_next + 1)]
                coin_get = player_id[4] * (1 + int(player_id[-2] > 0))
                delta_coin = min(coin_get, player_in4[0])
                player_id[0] += delta_coin
                player_in4[0] -= delta_coin
                env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                next += 1
            player_in4[0] += player_in4[3] * (1 + int(player_in4[-2] > 0))          #cộng tiền từ tiệm bánh
            env_state[ATTRIBUTE_PLAYER * id_action] = player_in4[0]   #cập nhật tiền của người chơi

        elif dice == 4:
            if player_in4[-2] > 0:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 5] * 4
            else:
                env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 5] * 3 

        elif dice == 5:
            for id in range(4):
                env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 6]

        elif dice == 6:
            if player_in4[13] > 0:
                for next in range(1,4):
                    id_next = (id_action + next) % 4
                    delta_coin = min(2, env_state[ATTRIBUTE_PLAYER * id_next])
                    env_state[ATTRIBUTE_PLAYER * id_next] -= delta_coin
                    player_in4[0] += delta_coin
                env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
            
            all_other_player_coin = np.zeros(3)
            for next in range(1, 4):
                all_other_player_coin[next-1] = env_state[ATTRIBUTE_PLAYER * ((id_action + next) % 4)]

            if player_in4[14] > 0 and np.sum(all_other_player_coin) > 0:      #nếu có thẻ đài truyền hình
                env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
                env_state[ENV_PHASE] = 3           #trạng thái chọn người để lấy tiền
                return env_state
            else:
                if player_in4[15] > 0:  #nếu có thẻ trung tâm thương mại
                    env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
                    env_state[ENV_PHASE] = 4       #trạng thái chọn người để đổi thẻ
                else:
                    if env_state[ENV_PLAYER_CONTINUE] == 1:
                        env_state[ENV_PHASE] = 1
                        env_state[ENV_PLAYER_CONTINUE] = 0
                    else:
                        if env_state[ENV_PHASE] == 2:
                            env_state[ENV_PHASE] = 7
                return env_state

        elif dice == 7:
            env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 7] * env_state[ATTRIBUTE_PLAYER * id_action + 2] * 3

        elif dice == 8:
            env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 8] * (env_state[ATTRIBUTE_PLAYER * id_action + 6] + env_state[ATTRIBUTE_PLAYER * id_action + 9]) * 3

        elif dice == 9:
            next = 1
            while 0 < player_in4[0] and next <= 3:
                id_next = (id_action - next) % 4
                player_id = env_state[ATTRIBUTE_PLAYER * id_next : ATTRIBUTE_PLAYER * (id_next + 1)]
                coin_get = player_id[10] * (2 + int(player_id[-2] > 0))
                delta_coin = min(coin_get, player_in4[0])
                player_id[0] += delta_coin
                player_in4[0] -= delta_coin
                env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                next += 1
            for id in range(4):
                env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 9] * 5
            env_state[20 * id_action] = player_in4[0]   #cập nhật tiền của người chơi

        elif dice == 10:
            next = 1
            while 0 < player_in4[0] and next <= 3:
                id_next = (id_action - next) % 4
                player_id = env_state[20 * id_next : 20 * (id_next + 1)]
                coin_get = player_id[10] * (2 + int(player_id[-2] > 0))
                delta_coin = min(coin_get, player_in4[0])
                player_id[0] += delta_coin
                player_in4[0] -= delta_coin
                env_state[ATTRIBUTE_PLAYER * id_next] = player_id[0]
                next += 1
            for id in range(4):
                env_state[ATTRIBUTE_PLAYER * id] += env_state[ATTRIBUTE_PLAYER * id + 11] * 3
            env_state[20 * id_action] = player_in4[0]   #cập nhật tiền của người chơi

        elif dice == 11 or dice == 12:
            env_state[ATTRIBUTE_PLAYER * id_action] += env_state[ATTRIBUTE_PLAYER * id_action + 12] * (env_state[ATTRIBUTE_PLAYER * id_action + 1] + env_state[ATTRIBUTE_PLAYER * id_action + 11]) * 3
            env_state[ENV_PHASE] = 4  
        #sau khi cập nhật xu, cho roll tiếp nếu đạt yêu cầu, giảm biến đánh dấu xuống
        if env_state[ENV_PLAYER_CONTINUE] == 1:
            env_state[ENV_PHASE] = 1
            env_state[ENV_PLAYER_CONTINUE] = 0
        else:
            if env_state[ENV_PHASE] == 2:
                env_state[ENV_PHASE] = 7

    elif phase_env == 3:
        #xử lí thẻ đài truyền hình
        id_picked = int(env_state[ENV_ID_ACTION] + action - 2) % 4
        delta_coin = min(5, env_state[ATTRIBUTE_PLAYER * id_picked])
        env_state[ATTRIBUTE_PLAYER * id_picked] -= delta_coin
        player_in4[0] += delta_coin
        if player_in4[15] > 0:  #nếu có thẻ trung tâm thương mại
            env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
            env_state[ENV_PHASE] = 4       #trạng thái chọn người để đổi thẻ
        else:
            if env_state[ENV_PLAYER_CONTINUE] == 1:
                env_state[ENV_PHASE] = 1
                env_state[ENV_PLAYER_CONTINUE] = 0
            else:
                env_state[ENV_PHASE] = 7

    elif phase_env == 4:
        if action == 9:
            if env_state[ENV_PLAYER_CONTINUE] == 1:
                env_state[ENV_PHASE] = 1
                env_state[ENV_PLAYER_CONTINUE] = 0
            else:
                env_state[ENV_PHASE] = 7
        else:
            id_picked = int(action - 5) % 4
            env_state[ENV_PICKED_PLAYER] = id_picked
            env_state[ENV_PHASE] = 5
    
    elif phase_env == 5:
        card_sell = action - 9
        env_state[ENV_CARD_SELL] = card_sell
        env_state[ENV_PHASE] = 6

    elif phase_env == 6:
        card_buy = action - 21
        card_sell = int(env_state[ENV_CARD_SELL])
        id_picked = int(env_state[ENV_PICKED_PLAYER] + env_state[ENV_ID_ACTION]) % 4
        player_picked = env_state[ATTRIBUTE_PLAYER * id_picked : ATTRIBUTE_PLAYER * (id_picked + 1)]
        player_picked[card_buy] -= 1
        player_picked[card_sell] += 1

        player_in4[card_buy] += 1
        player_in4[card_sell] -= 1
        env_state[ATTRIBUTE_PLAYER * id_picked : ATTRIBUTE_PLAYER * (id_picked + 1)] = player_picked
        env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
        env_state[ENV_CARD_SELL] = -0.5
        env_state[ENV_PICKED_PLAYER] = 0
        if env_state[ENV_PLAYER_CONTINUE] == 1:
            env_state[ENV_PHASE] = 1
            env_state[ENV_PLAYER_CONTINUE] = 0
        else:
            env_state[ENV_PHASE] = 7

    elif phase_env == 7:
        if action == 53:
            env_state[ENV_PHASE] = 1
            env_state[ENV_CARD_BUY_IN_TURN : ENV_CARD_SELL] = np.zeros(12)
            env_state[ENV_ID_ACTION] = (env_state[ENV_ID_ACTION] + 1) % 4
        else:
            card_buy = action - 33
            player_in4[card_buy] += 1
            player_in4[0] -= ALL_CARD_FEE[card_buy-1]
            env_state[ATTRIBUTE_PLAYER * id_action : ATTRIBUTE_PLAYER * (id_action + 1)] = player_in4
            if card_buy < 13:
                #nếu mua thẻ trên bàn thì trừ ở bàn chơi đi
                env_state[ENV_CARD_BUY_IN_TURN : ENV_CARD_SELL][card_buy-1] += 1
                env_state[ENV_NORMAL_CARD + card_buy-1] -= 1
            if player_in4[0] == 0:
                env_state[ENV_PHASE] = 1
                env_state[ENV_CARD_BUY_IN_TURN : ENV_CARD_SELL] = np.zeros(12)
                env_state[ENV_ID_ACTION] = (env_state[ENV_ID_ACTION] + 1) % 4
    
    return env_state 

@njit()
def random_Env(p_state, per):
    arr_action = getValidActions(p_state)
    if np.sum(arr_action) == 0:
        print(list(p_state))
    arr_action = np.where(arr_action == 1)[0]
    act_idx = np.random.randint(0, len(arr_action))
    return arr_action[act_idx], per

@njit(fastmath=True, cache=True)
def system_check_end(env_state):
    for id_player in range(NUMBER_PLAYER):
        if np.sum(env_state[ATTRIBUTE_PLAYER * id_player: ATTRIBUTE_PLAYER * (id_player + 1)][-NUMBER_TARGET_CARD:]) == NUMBER_TARGET_CARD:
            return False
    return True

@njit()
def getReward(player_state):
    value_return = -1
    if player_state[P_CHECK_END] != 1:
        return value_return
    else:
        for id_player in range(NUMBER_PLAYER):
            player_in4 = player_state[ATTRIBUTE_PLAYER * id_player : ATTRIBUTE_PLAYER * (id_player + 1)]
            if np.sum(player_in4[-NUMBER_TARGET_CARD:]) == NUMBER_TARGET_CARD:
                value_return = id_player 
                break
        if value_return == 0:
            return 1
        else:
            return 0

@njit()
def check_winner(env_state):
    winner = -1
    for id_player in range(NUMBER_PLAYER):
        player_in4 = env_state[ATTRIBUTE_PLAYER * id_player : ATTRIBUTE_PLAYER * (id_player + 1)]
        if np.sum(player_in4[-NUMBER_TARGET_CARD:]) == NUMBER_TARGET_CARD:
            return id_player
    return winner


def one_game(list_player, per_file):
    env_state = initEnv()
    count_turn = 0
    while system_check_end(env_state) and count_turn < 1000:
        p_id_action = int(env_state[ENV_ID_ACTION])
        p_state = getAgentState(env_state)

        action, per_file = list_player[p_id_action](p_state, per_file)
        list_action = getValidActions(p_state)
        if list_action[action] != 1:
            raise Exception("action ko hợp lệ")
        env_state = stepEnv(env_state, action)
        count_turn += 1
    env_state[ENV_CHECK_END] = 1
    winner = check_winner(env_state)
    for id_player in range(NUMBER_PLAYER):
        env_state[ENV_PHASE] = 1
        env_state[ENV_ID_ACTION] = id_player
        p_state = getAgentState(env_state)
        action, per_file = list_player[p_id_action](p_state, per_file)
    return winner, per_file

def normal_main(list_player, times, file_per):
    count = np.zeros(len(list_player)+1)
    all_id_player = np.arange(len(list_player))
    for van in range(times):
        shuffle = np.random.choice(all_id_player, 4, replace=False)
        shuffle_player = [list_player[shuffle[0]], list_player[shuffle[1]], list_player[shuffle[2]], list_player[shuffle[3]]]
        file_temp = [[0],[0],[0],[0]]
        winner, file_per = one_game(shuffle_player, file_per)
        if winner == -1:
            count[winner] += 1
        else:
            count[shuffle[winner]] += 1
    return list(count.astype(np.int64)), file_per

@njit()
def numba_one_game(p_lst_idx_shuffle, p0, p1, p2, p3, per_file):
    env_state = initEnv()
    count_turn = 0
    while system_check_end(env_state) and count_turn < 1000:
        p_idx = int(env_state[ENV_ID_ACTION])
        p_state = getAgentState(env_state)
        if p_lst_idx_shuffle[p_idx] == 0:
            act, per_file = p0(p_state, per_file)
        elif p_lst_idx_shuffle[p_idx] == 1:
            act, per_file = p1(p_state, per_file)
        elif p_lst_idx_shuffle[p_idx] == 2:
            act, per_file = p2(p_state, per_file)
        else:
            act, per_file = p3(p_state, per_file)
        if getValidActions(p_state)[act] != 1:
            raise Exception('bot dua ra action khong hop le')
        env_state = stepEnv(env_state, act)
        count_turn += 1

    env_state[ENV_CHECK_END] = 1
    winner = check_winner(env_state)
    for id_player in range(4):
        env_state[ENV_PHASE] = 1
        p_state = getAgentState(env_state)
        p_idx = int(env_state[ENV_ID_ACTION])
        if p_lst_idx_shuffle[p_idx] == 0:
            act, per_file = p0(p_state, per_file)
        elif p_lst_idx_shuffle[p_idx] == 1:
            act, per_file = p1(p_state, per_file)
        elif p_lst_idx_shuffle[p_idx] == 2:
            act, per_file = p2(p_state, per_file)
        else:
            act, per_file = p3(p_state, per_file)
    
        env_state[ENV_ID_ACTION] = (env_state[ENV_ID_ACTION] + 1)%4
    return winner, per_file

@njit()
def numba_main(p0, p1, p2, p3, num_game,per_file):
    count = np.zeros(getAgentSize()+1, dtype= np.int32)
    p_lst_idx = np.array([0,1,2,3])
    for _n in range(num_game):
        np.random.shuffle(p_lst_idx)
        winner, per_file = numba_one_game(p_lst_idx, p0, p1, p2, p3, per_file )
        if winner == -1:
            count[winner] += 1
        else:
            count[p_lst_idx[winner]] += 1
    return count, per_file


@jit()
def one_game_numba(p0, list_other, per_player, per1, per2, per3, p1, p2, p3):
    env_state = initEnv()
    count_turn = 0
    while system_check_end(env_state) and count_turn < 1000:
        idx = int(env_state[ENV_ID_ACTION])
        player_state = getAgentState(env_state)
        if list_other[idx] == -1:
            action, per_player = p0(player_state,per_player)
        elif list_other[idx] == 1:
            action, per1 = p1(player_state,per1)
        elif list_other[idx] == 2:
            action, per2 = p2(player_state,per2)
        elif list_other[idx] == 3:
            action, per3 = p3(player_state,per3) 

        if getValidActions(player_state)[action] != 1:
            raise Exception('bot dua ra action khong hop le')

        env_state = stepEnv(env_state, action)
        count_turn += 1

    env_state[ENV_CHECK_END] = 1

    for p_idx in range(4):
        env_state[ENV_PHASE] = 1
        if list_other[int(env_state[ENV_ID_ACTION])] == -1:
            act, per_player = p0(getAgentState(env_state), per_player)
        env_state[ENV_ID_ACTION] = (env_state[ENV_ID_ACTION] + 1)%4

    winner = False
    if np.where(list_other == -1)[0] ==  check_winner(env_state): winner = True
    else: winner = False
    return winner,  per_player

@jit()
def n_game_numba(p0, num_game, per_player, list_other, per1, per2, per3, p1, p2, p3):
    win = 0
    for _n in range(num_game):
        np.random.shuffle(list_other)
        winner,per_player  = one_game_numba(p0, list_other, per_player, per1, per2, per3, p1, p2, p3)
        win += winner
    return win, per_player

import importlib.util, json, sys
from setup import SHOT_PATH

def load_module_player(player):
    spec = importlib.util.spec_from_file_location('Agent_player', f"{SHOT_PATH}Agent/{player}/Agent_player.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module 
    spec.loader.exec_module(module)
    return module
    
def numba_main_2(p0, n_game, per_player, level, *args):
    list_other = np.array([1, 2, 3, -1])
    if level == 0:
        per_agent_env = np.array([0])
        return n_game_numba(p0, n_game, per_player, list_other, per_agent_env, per_agent_env, per_agent_env, random_Env, random_Env, random_Env)
    else:
        env_name = sys.argv[1]
        if len(args) > 0:
            dict_level = json.load(open(f'{SHOT_PATH}Log/check_system_about_level.json'))
        else:
            dict_level = json.load(open(f'{SHOT_PATH}Log/level_game.json'))

        if str(level) not in dict_level[env_name]:
            raise Exception('Hiện tại không có level này') 
        lst_agent_level = dict_level[env_name][str(level)][2]

        p1 = load_module_player(lst_agent_level[0]).Test
        p2 = load_module_player(lst_agent_level[1]).Test
        p3 = load_module_player(lst_agent_level[2]).Test
        per_level = []
        for id in range(getAgentSize()-1):
            data_agent_env = list(np.load(f'{SHOT_PATH}Agent/{lst_agent_level[id]}/Data/{env_name}_{level}/Train.npy',allow_pickle=True))
            per_level.append(data_agent_env)
        
        return n_game_numba(p0, n_game, per_player, list_other, per_level[0], per_level[1], per_level[2], p1, p2, p3)

        










