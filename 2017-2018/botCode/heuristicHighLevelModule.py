#!/usr/bin/env python3

import os, copy
import robomodules as rm
from operator import itemgetter
from variables import *
from grid import grid
from search import bfs
from messages import MsgType, message_buffers, LightState, PacmanCommand

ADDRESS = os.environ.get("LOCAL_ADDRESS","localhost")
PORT = os.environ.get("LOCAL_PORT", 11295)

FREQUENCY = 30
PELLET_WEIGHT = 0.65
GHOST_WEIGHT = 0.35
GHOST_CUTOFF = 4

class HeuristicHighLevelModule(rm.ProtoModule):
    def __init__(self, addr, port):
        self.subscriptions = [MsgType.LIGHT_STATE]
        super().__init__(addr, port, message_buffers, MsgType, FREQUENCY, self.subscriptions)
        self.state = None
        self.previous_loc = None
        self.direction = PacmanCommand.EAST
        self.grid = copy.deepcopy(grid)

    def _get_direction(self, p_loc, next_loc):
        if p_loc[0] == next_loc[0]:
            if p_loc[1] < next_loc[1]:
                return PacmanCommand.NORTH
            else:
                return PacmanCommand.SOUTH
        else:
            if p_loc[0] < next_loc[0]:
                return PacmanCommand.EAST
            else:
                return PacmanCommand.WEST

    def _find_paths_to_closest_ghosts(self, pac_loc):
        ghosts = [self.state.red_ghost, self.state.pink_ghost, self.state.orange_ghost, self.state.blue_ghost]
        state_paths = [(ghost.state, bfs(self.grid, pac_loc, (ghost.x, ghost.y), GHOST_CUTOFF)) for ghost in ghosts]
        print(ghosts)
        print(state_paths)
        return [sp for sp in state_paths if sp[1] is not None]

    def _find_distance_of_closest_pellet(self, target_loc):
        print('getting pellet')
        return len(bfs(self.grid, target_loc, [o])) - 1

    def _target_is_invalid(self, target_loc):
        return self.grid[target_loc[0]][target_loc[1]] in [I, n]

    def _is_power_pellet_closer(self, path):
        return O in path

    def _find_best_target(self, p_loc):
        targets = [p_loc, (p_loc[0] - 1, p_loc[1]), (p_loc[0] + 1, p_loc[1]), (p_loc[0], p_loc[1] - 1), (p_loc[0], p_loc[1] + 1)]
        heuristics = []
        for target_loc in targets:
            if self._target_is_invalid(target_loc):
                heuristics.append(float('inf'))
                continue
            dist_to_pellet = self._find_distance_of_closest_pellet(target_loc)
            paths_to_ghosts = self._find_paths_to_closest_ghosts(target_loc)
            closest_ghost = (None, float('inf'))
            for state, path in paths_to_ghosts:
                dist = len(path) - 1
                closest_ghost = (state, dist) if dist < closest_ghost[1] else closest_ghost
                if self._is_power_pellet_closer(path):
                    if target_loc == p_loc:
                        return path[1]
                    else:
                        return path[0]
            ghost_heuristic = 0 if closest_ghost[1] > GHOST_CUTOFF else pow((GHOST_CUTOFF - closest_ghost[1]), 2) * GHOST_WEIGHT
            ghost_heuristic = ghost_heuristic * -1 if closest_ghost[0] == LightState.FRIGHTENED else ghost_heuristic
            print('ghost: {}'.format(ghost_heuristic))
            pellet_heuristic = dist_to_pellet * PELLET_WEIGHT
            print('pellet: {}'.format(pellet_heuristic))
            heuristics.append(ghost_heuristic + pellet_heuristic)
        print(heuristics)
        mins = []
        min_heur = float('inf')
        for i, heur in enumerate(heuristics):
            if heur < min_heur:
                min_heur = heur
                mins = [(i, heur)]
            elif heur == min_heur:
                mins.append((i, heur))
        


    def _update_game_state(self):
        p_loc = (self.state.pacman.x, self.state.pacman.y)
        if self.grid[p_loc[0]][p_loc[1]] in [o, O]:
            self.grid[p_loc[0]][p_loc[1]] = e

    def _send_command_message_to_target(self, p_loc, target):
        new_msg = PacmanCommand()
        new_msg.dir = self._get_direction(p_loc, target)
        self.write(new_msg.SerializeToString(), MsgType.PACMAN_COMMAND)

    def _send_stop_command(self):
        new_msg = PacmanCommand()
        new_msg.dir = PacmanCommand.STOP
        self.write(new_msg.SerializeToString(), MsgType.PACMAN_COMMAND)

    def msg_received(self, msg, msg_type):
        if msg_type == MsgType.LIGHT_STATE:
            if self.previous_loc != msg.pacman:
                if self.previous_loc is not None:
                   self.direction = self._get_direction((self.previous_loc.x, self.previous_loc.y), (msg.pacman.x, msg.pacman.y))
                self.previous_loc = self.state.pacman
            self.state = msg

    def tick(self):
        if self.state and self.state.mode == LightState.RUNNING:
            self._update_game_state()
            p_loc = (self.state.pacman.x, self.state.pacman.y)
            next_loc = self._find_best_target(p_loc)
            if next_loc != p_loc:
                self._send_command_message_to_target(p_loc, next_loc)
                return
        self._send_stop_command()


def main():
    module = HeuristicHighLevelModule(ADDRESS, PORT)
    module.run()

if __name__ == "__main__":
    main()