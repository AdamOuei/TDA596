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
import random

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------


# Class board for handling board actions
class Board:

    board = {}

    def __init__(self):
        self.unique_id = 0

    def add(self, entry):
        self.board[self.unique_id] = entry
        self.unique_id += 1

    def modify(self, element_id, entry):
        self.board[element_id] = entry

    def delete(self, element_id):
        self.board.pop(element_id)


try:
    app = Bottle()
    board = Board()

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

    def leader_selection_start(node_id):
        random_value = random.randint(0, 100000)
        data = {'node_id': node_id,
                'random_value': random_value, 'start_node': node_id}
        send_to_next_vessel(node_id, data)

        # ------------------------------------------------------------------------------------------------------
        # DISTRIBUTED COMMUNICATIONS FUNCTIONS
        # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET request, once
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
        # Distributes to each vessel (except to yourself)
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    def send_to_next_vessel(sender_node, data):
        global vessel_list, node_id

        path = '/propagate/leader/{}'.format(node_id)

        next_id = (int(node_id) % 9) + 1
        next_ip = vessel_list.get(str(next_id))

        thread = Thread(target=contact_vessel, args=(next_ip, path))
        thread.daemon = True
        thread.start()

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
        ''' Reads the entry and adds it to the clients Board.
        Creates a thread and propagates the same entry to the other vessels'''
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
        ''' Depending on the action, either modifies or removes an entry in the clients board
        Creates a thread and propagates the same action to the other vessels'''
        try:
            action = request.forms.get('delete')
            str_element_id = str(element_id)
            if action == 'delete':
                delete_element_from_store(element_id)
                thread = Thread(target=propagate_to_vessels,
                                args=('/propagate/delete/' + str_element_id, None))

            elif action == 'modify':
                new_entry = request.forms.get('modify_entry')
                modify_element_in_store(element_id, new_entry)
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
        ''' Reads the propagated data and depending on the action,
        adds, modifies or deletes the entry from the vessels Board'''
        print request.body.read()
        json_object = request.json
        if action == "add":
            add_new_element_to_store(json_object, is_propagated_call=True)
        else:
            int_element_id = int(element_id)
            if action == "delete":
                delete_element_from_store(
                    int_element_id, is_propagated_call=True)
            elif action == "modify":
                modify_element_in_store(
                    int_element_id, json_object, is_propagated_call=True)

    @app.post('/propagate/leader/<sender_node>')
    def select_leader(sender_node):
        try:
            json = request.json
            print json
        except Exception as e:
            print e

    # def select_leader(list_of_nodes=[], current_id=2):
    #     # Get a random index to start searching for leader
    #     global vessel_list, node_id, leader
    #     if current_id != node_id:
    #         print "exit"
    #         exit
    #     try:
    #         random_number = random.randint(0, 10000)
    #         next_ip = vessel_list[str((node_id % 9) + 1)]
    #         if len(list_of_nodes == 0):
    #             list_of_nodes.append({'id': node_id, 'rand': random_number})
    #             print "if" + str(list_of_nodes)
    #             contact_vessel(next_ip, '/propagate/leader', list_of_nodes)
    #         elif node_id != int(list_of_nodes[0].id):
    #             list_of_nodes = request.json
    #             print "first elif {}".format(list_of_nodes)
    #             list_of_nodes.append({'id': node_id, 'rand': random_number})
    #             print "elif" + list_of_nodes
    #             contact_vessel(next_ip, '/propagate/leader', list_of_nodes)
    #             print "Current node is:{} Next node should be : {} ".format(node_id, node_id+1)
    #         else:
    #             list_of_nodes = request.json
    #             leader = list_of_nodes[0].id
    #             for node in list_of_nodes:
    #                 if list_of_nodes[leader].rand < node.rand:
    #                     leader = node
    #         print "The leader chosen was: " + leader
    #     except Exception as e:
    #         requests.HTTPError("Could not choose leader")

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
            thread = Thread(target=select_leader, args=node_id)
            thread.start()
            run(app, host=vessel_list[str(node_id)], port=port)
            thread.join()
            sleep(1)
            print "Test"
            # leader_thread = Thread(target=select_leader, args=)
            # select_leader(vessel_list)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
