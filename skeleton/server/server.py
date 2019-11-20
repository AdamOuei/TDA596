# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: John Doe
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------


class Board:

    board = {}

    def __init__(self):
        self.unique_id = 0

    def add(self, entry):
        self.board[self.unique_id] = entry
        self.unique_id += 1

    def modify(self, entry, element_id):
        if element_id in self.board:
            self.board[element_id] = entry
        else:
            return "Key does not exist"

    def delete(self, element_id):
        self.board.pop(element_id)


try:
    app = Bottle()

    board = Board()

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # You will probably need to modify them
    # ------------------------------------------------------------------------------------------------------

    def add_new_element_to_store(element, is_propagated_call=False):
        global board, node_id, unique_id
        success = False
        try:
            board.add(element)
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(element_id, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board.modify(element_id, modified_element)
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(element_id, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board.delete(element_id)
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), json=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.board.iteritems()), members_name_string='YOUR NAME')

    @app.get('/board')
    def get_board():
        global board, node_id
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id
        try:
            new_entry = request.forms.get('entry')
            add_new_element_to_store(new_entry)
            thread = Thread(target=propagate_to_vessels,
                            args=('/propagate/add/none', new_entry))
            thread.daemon = True
            thread.start()
            thread.join()
            return new_entry
        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global node_id, board
        try:
            action = request.forms.get('delete')
            if action == 'delete':
                delete_element_from_store(element_id)
                str_element_id = str(element_id)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/delete/' + str_element_id, None))
                thread.daemon = True
                thread.start()
                thread.join()

            if action == 'modify':
                new_entry = request.forms.get('modify_entry')
                modify_element_in_store(element_id, new_entry)
                str_element_id = str(element_id)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/modify/' + str_element_id, new_entry))
                thread.daemon = True
                thread.start()
                thread.join()

            return "Success"
        except Exception as e:
            print e
        return False

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        #global node_id, board
        if action == "add":
            json_object = request.json
            add_new_element_to_store(json_object)
        elif action == "delete":
            int_element_id = int(element_id)
            delete_element_from_store(int_element_id)
        elif action == "modify":
            int_element_id = int(element_id)
            modify_element_in_store(int_element_id, request.json)
        pass

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
