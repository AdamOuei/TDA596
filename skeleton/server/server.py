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
        self.board[entry['ident']] = entry

    def modify(self, element_id, data):
        self.board.get(element_id)['data'] = data

    def pop(self, element_id):
        return self.board.pop(element_id)

    def sort(self):
        tmp = {}
        for i in sorted(self.board.keys()):
            tmp[i] = self.board[i]
        self.board = tmp

    def lookup(self, element_id):
        return self.board.get(element_id)

    def exists(self, element_id):
        if self.lookup(element_id) != None:
            return True
        return False

    def modifyId(self, element_id):
        self.board.get(element_id)['ident'] = element_id + 1

    def iteritems(self):
        tmp = []
        for i in sorted(self.board.keys()):
            tmp.append((i, self.lookup(i)['data']))
        return tmp

    def deleteAll(self):
        self.board.clear()


try:
    app = Bottle()
    board = Board()
    action_history = []
    action_waiting = []
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
            board.pop(element_id)
            success = True
        except Exception as e:
            print e
        return success

# Vill nog lägga in detta i add_element_to_store och använda is_propagated_call
    def update_element_id_in_store(entry):
        global board, unique_id
        curr_id = entry.get('ident')

        if not board.exists(curr_id):
            unique_id = curr_id
            add_new_element_to_store(entry, is_propagated_call=True)
            board.sort()
        elif entry.get('node_id') > board.lookup(curr_id).get('node_id'):
            changing_entry = board.pop(curr_id)
            changing_entry['ident'] = curr_id + 1
            unique_id = curr_id + 1
            add_new_element_to_store(entry, is_propagated_call=True)
            board.sort()
            update_element_id_in_store(changing_entry)
        else:
            entry['ident'] = curr_id + 1
            unique_id = curr_id + 1
            update_element_id_in_store(entry)

    # ------------------------------------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def create_entry(new_entry):
        # Gives each new entry a unique id
        global unique_id, node_id
        unique_id += 1
        entry = {'ident': unique_id, 'data': new_entry, 'node_id': node_id}
        return entry

    def add_to_history(action, data):
        global action_history
        history_data = {'data': data, 'action': action}
        action_history.append(history_data)

    def add_to_waiting(action, data):
        global action_history, action_waiting
        action_in_history = False
        for a in action_history:
            if a.get('action') == 'delete':
                if a.get('data') == data:
                    action_in_history = True
            else:
                if a.get('data').get('ident') == data.get('ident'):
                    action_in_history = True
        if not action_in_history:
            waiting_data = {'data': data, 'action': action}
            action_waiting.append(waiting_data)

    def check_waiting_actions():
        global action_waiting
        for action in action_waiting:
            if board.exists(action.get('ident')):
                if action.get('action') == 'delete':
                    delete_element_from_store(action.get('ident'))
                else:
                    modify_element_in_store(action.get(
                        'data').get('ident'), action.get('data'))

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
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()), members_name_string='YOUR NAME')

    @app.get('/board')
    def get_board():
        global board, node_id
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        ''' Reads the entry and creates an entry_object with an ID for the entry.
        Creates a thread and propagates the same entry_object to the other vessels'''
        global node_id, board
        try:
            new_entry = request.forms.get('entry')
            entry_object = create_entry(new_entry)
            update_element_id_in_store(entry_object)
            thread = Thread(target=propagate_to_vessels,
                            args=('/propagate/add/0', entry_object))
            thread.daemon = True
            thread.start()
            thread.join()
            check_waiting_actions()
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
                                args=('/propagate/{}/{}'.format(action, element_id), None))
            elif action == 'modify':
                modify_element_in_store(element_id, new_entry)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/{}/{}'.format(action, element_id), new_entry))
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
            update_element_id_in_store(json_object)
            check_waiting_actions()
        else:
            int_element_id = int(element_id)
            if board.exists(int_element_id):
                if action == "delete":
                    delete_element_from_store(
                        int_element_id, is_propagated_call=True)
                elif action == "modify":
                    modify_element_in_store(
                        int_element_id, json_object, is_propagated_call=True)
                add_to_history(action, json_object)

            else:
                add_to_waiting(action, json_object)

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
