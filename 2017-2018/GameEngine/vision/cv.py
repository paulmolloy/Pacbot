import numpy as np
from pacbot.grid import grid
from comm.pacmanState_pb2 import PacmanState
import asyncio, cv2

FREQUENCY = 60

class MovementProcessor:
    def __init__(self, client, edges=None, cam_number=0, loop=None):
        self.client = client
        self.loop = loop or asyncio.get_event_loop()
        self.loop.call_soon(self.tick)
        self.edges = edges or {'l':342, 'r':1185,'u':-8,'d':749}
        self.cap = cv2.VideoCapture(cam_number) # set camera
        self.cap.set(3, 1280) # set frame width
        self.cap.set(4, 720) # set frame height

    def tick(self):
        bot_loc = self._get_bot_location()
        buf = PacmanState.AgentState()
        buf.x = bot_loc[0]
        buf.y = bot_loc[1]
        self.client.write(buf.SerializeToString())
        self._display_grid_image()
        self.loop.call_later(1/FREQUENCY, self.tick)

    def _capture_image(self):
        return self.cap.read()[1]

    def _process_image(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv = cv2.medianBlur(hsv, 5)
        draw_col = (0,0,255)

        p1 = (self.edges['l'], self.edges['d'])
        p2 = (self.edges['r'], self.edges['u'])
        cv2.rectangle(hsv, p1, p2, draw_col)

        vert_spacing = (self.edges['r'] - self.edges['l'])/float(len(grid))
        for i in range(1, len(grid)):
            x_pos = int(self.edges['l'] + i*vert_spacing)
            p1 = (x_pos, self.edges['d'])
            p2 = (x_pos, self.edges['u'])
            cv2.line(hsv, p1, p2, draw_col)

        horiz_spacing = (self.edges['d'] - self.edges['u'])/float(len(grid[0]))
        for i in range(1, len(grid[0])):
            y_pos = int(self.edges['u'] + i*horiz_spacing)
            p1 = (self.edges['l'], y_pos)
            p2 = (self.edges['r'], y_pos)
            cv2.line(hsv, p1, p2, draw_col)

        return hsv

    def _detect_bot(self, hsv_image):
        BOT_MIN = np.array([28,8,100], np.uint8)
        BOT_MAX = np.array([32,255,255], np.uint8)

        thresholded_image = cv2.inRange(hsv_image, BOT_MIN, BOT_MAX)
        thresholded_image = cv2.medianBlur(thresholded_image, 15)

        _, contours, hierarchy = cv2.findContours(thresholded_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            (bot_x, bot_y) = (-1000,-1000)
        else:
            bot = contours[0]
            M = cv2.moments(bot)
            if len(bot) > 2:
                bot_x = int(M['m10']/M['m00'])
                bot_y = int(M['m01']/M['m00'])
            else:
                (bot_x, bot_y) = (-1000,-1000)

        return thresholded_image, (bot_x, bot_y)

    def _convert_cam_coords_to_game(self, coords):
        cam_x = coords[0]
        cam_y = coords[1]
        if cam_x < self.edges['l'] or cam_x > self.edges['r'] or cam_y < self.edges['u'] or cam_y > self.edges['d']:
            return (-1,-1)
        else:
            x = int((self.edges['d']-cam_y)/((self.edges['d']-self.edges['u'])/float(len(grid))))
            y = int((cam_x-self.edges['l'])/((self.edges['r']-self.edges['l'])/float(len(grid[0]))))
            return (x, y)

    def _get_bot_location(self):
        image = self._capture_image()
        image = self._process_image(image)
        thresh_image, coords = self._detect_bot(image)
        game_loc = self._convert_cam_coords_to_game(coords)
        return game_loc

    def _display_grid_image(self):
        while True:
            image = self._capture_image()
            image = self._process_image(image)
            cv2.imshow('Grid Reference', image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
