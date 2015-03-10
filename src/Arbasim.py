#!/usr/bin/env python
"""
    Arbalet - ARduino-BAsed LEd Table
    Arbasim - Arbalet Simulator

    Simulate an Arbalet table

    Copyright (C) 2015 Yoan Mollard <yoan@konqifr.fr>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import pygame
import os
import logging
import threading
import time
from Grid import *
from Arbastate import *

class Arbasim(threading.Thread):
    def __init__(self, arbalet_width, arbalet_height, sim_width, sim_height, rate=30):
        """
        Arbasim constructor: launches the simulation
        Simulate a "arbalet_width x arbalet_height px" table rendered in a "sim_width x sim_height" window
        :param arbalet_width: Number of pixels of Arbalet in width
        :param arbalet_height: Number of pixels of Arbalet in height
        :param sim_width:
        :param sim_height:
        :param rate: Refresh rate in Hertz
        :return:
        """
        threading.Thread.__init__(self)
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%I:%M:%S')
        self.sim_state = "idle"
        self.running = True
        self.refresh_rate = rate

        # Current table state storing all pixels
        self.arbastate = None
        self.lock_state = threading.Lock()

        self.sim_width = sim_width
        self.sim_height = sim_height
        self.arbalet_width = arbalet_width
        self.arbalet_height = arbalet_height
        self.grid = Grid(sim_width/arbalet_width, sim_height/arbalet_height, arbalet_width, arbalet_height, (40, 40, 40))

        # Init Pygame
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        logging.info("Pygame initialized")
        self.screen = pygame.display.set_mode((self.sim_width, self.sim_height), 0, 32)
        self.sim_state = "idle"
        self.font = pygame.font.SysFont('sans', 14)

    def stop(self, reason=None):
        self.sim_state = "exiting"
        logging.info("Simulator exiting, reason: {}", reason if reason!=None else 'unknown')
        self.running = False

    def set_state(self, arbastate):
        """
        Updates the current state of the simulator
        :param arbastate:
        :return:
        """
        self.lock_state.acquire()
        try:
            self.arbastate = arbastate
        finally:
            self.lock_state.release()
        self.sim_state = "running"

    def run(self):
        # Main Simulation loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop("User request")
                    break

            # Render background and title
            pygame.draw.rect(self.screen,(0, 0, 0), pygame.Rect(0, 0, self.sim_width+2, self.sim_height+2))
            pygame.display.set_caption("Arbasim [{}]".format(self.sim_state))


            # Render grid and pixels
            self.grid.render(self.screen, self.arbastate)
            caption = "[{}] Caption...".format(self.sim_state)
            rendered_caption = self.font.render(caption, 1, (255, 255, 255))
            location_caption = pygame.Rect((10,10), (300,20))
            self.screen.blit(rendered_caption, location_caption)

            pygame.display.update()
            time.sleep(1./self.refresh_rate)


if __name__ == '__main__':
    width = 10
    height = 15
    factor_sim = 30
    sim = Arbasim(width, height, width*factor_sim, height*factor_sim)
    sim.start()
    time.sleep(1)

    # We construct 2 different states to give an example
    state_red = Arbastate(width, height)
    state_green = Arbastate(width, height)

    # The "green" state is filled in background but not shown
    for w in range(width):
        for h in range(height):
            state_green.set_pixel(h, w, 'green')

    # The "red" state is now shown
    sim.set_state(state_red)

    # The "red" state is updated by reference, shown in live
    for w in range(width):
        for h in range(height):
            state_red.set_pixel(h, w, 'red')
            time.sleep(0.05)

    time.sleep(1)

    # We switch immediately to the "green" state...
    sim.set_state(state_green)
    time.sleep(1)

    # ...and back to the "red" again
    sim.set_state(state_red)
    time.sleep(1)
    sim.stop("__main__ example ended")