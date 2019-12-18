# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: Omar Oueidat and Tobias Lindgren
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread
import random

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------


# Class board for handling board actions
class Board:

    board = {}

    def add(self, entry):
        self.board[entry['ident']] = entry['data']

    def modify(self, element_id, data):
        self.board[element_id] = data

    def delete(self, element_id):
        self.board.pop(element_id)

    def sort(self):
        tmp = {}
        for i in sorted(self.board.keys()):
            tmp[i] = self.board[i]
        self.board = tmp


try:
    app = Bottle()
    board = Board()
    unique_id = 0
    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def add_new_element_to_store(element, is_propagated_call=False):
        global board
        success = False
        try:
            board.add(element)
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(element_id, modified_element, is_propagated_call=False):
        global board
        success = False
        try:
            board.modify(element_id, modified_element)
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(element_id, is_propagated_call=False):
        global board
        success = False
        try:
            board.delete(element_id)
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def create_entry(new_entry):
        # Gives each new entry a unique id
        global unique_id
        entry = {'ident': unique_id, 'data': new_entry}
        unique_id += 1
        return entry

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET request, once
        success = False
        try:
            print "I am contacting {}, with path: {} and payload : {}".format(vessel_ip, path, payload)
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), json=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        # Distributes to each vessel (except to yourself)
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
        ''' Reads the entry and creates an entry_object with an ID for the entry. 
        Creates a thread and propagates the same entry_object to the other vessels'''
        global node_id, board
        try:
            new_entry = request.forms.get('entry')
            entry_object = create_entry(new_entry)
            add_new_element_to_store(entry_object)
            board.sort()
            thread = Thread(target=propagate_to_vessels,
                            args=('/propagate/add/0', entry_object))
            thread.daemon = True
            thread.start()
            thread.join()
            return new_entry
        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        ''' Depending on the action, either modifies or removes an entry in the clients board.
        Creates a thread and propagates the same action to the other vessels.'''
        global node_id, vessel_list
        try:
            action = request.forms.get('delete')
            new_entry = request.forms.get('modify_entry')
            if action == 'delete':
                delete_element_from_store(element_id)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/delete/' + str_element_id, None))
            elif action == 'modify':
                modify_element_in_store(element_id, new_entry)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/modify/' + str_element_id, new_entry))
            thread.daemon = True
            thread.start()
            return "Success"
        except Exception as e:
            print e
        return False

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        ''' Reads the propagated data and depending on the action,
        adds, modifies or deletes the entry from the vessels Board'''
        global board
        json_object = request.json
        if action == "add":
            add_new_element_to_store(json_object, is_propagated_call=True)
            board.sort()
        else:
            int_element_id = int(element_id)
            if action == "delete":
                delete_element_from_store(
                    int_element_id, is_propagated_call=True)
            elif action == "modify":
                modify_element_in_store(
                    int_element_id, json_object, is_propagated_call=True)

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
