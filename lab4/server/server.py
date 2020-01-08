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
from byzantine_behavior import *

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------


try:
    app = Bottle()
    action_dict = {}
    results_dict = {}
    number_of_nodes = 0
    byzantine = False
    ATTACK = 'ATTACK'
    WITHDRAW = "WITHDRAW"
    BYZANTINE = "BYZANTINE"

    # ------------------------------------------------------------------------------------------------------
    # HELPER FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def eval_result():
        global results_dict, action_dict

        result = []
        attack = None
        withdraw = None

        for i in range(1, number_of_nodes + 1):
            attack = 0
            withdraw = 0

            for k, v in results_dict.iteritems():

                if int(k) == i:  # Remove this if-else case and the algorithm doesn't reach an agreement for 3 and 4 nodes, keep and it reaches an agreement
                    if action_dict.get(str(i)) == ATTACK:
                        attack += 1
                    if action_dict.get(str(i)) == WITHDRAW:
                        withdraw += 1
                else:
                    if v.get(str(i)) == ATTACK:
                        attack += 1
                    if v.get(str(i)) == WITHDRAW:
                        withdraw += 1
                # print "For i = {} , ATTACK: {}  WITHDRAW: {}".format(i, attack, withdraw)
            if attack >= withdraw:
                result.append(ATTACK)
            else:
                result.append(WITHDRAW)
            print "Result from eval: {}".format(result)
        return result

    def check_result():
        result_list = eval_result()
        result = None
        attack = 0
        withdraw = 0

        for i in result_list:
            if i == ATTACK:
                attack += 1
            elif i == WITHDRAW:
                withdraw += 1

        if attack >= withdraw:
            result = ATTACK
        else:
            result = WITHDRAW
        print "Result from check: {} with attack being : {}, and withdraw being: {}".format(result, attack, withdraw)
        return result, result_list

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
                thread = Thread(target=contact_vessel, args=(
                    vessel_ip, path, payload, req))
                thread.daemon = True
                thread.start()

    def propagate_final_result(node_id):
        global action_dict
        payload = {'action_dict': action_dict}
        path = "/propagate/final/{}".format(node_id)
        propagate_to_vessels(path, payload)

    def last_result_received():
        global node_id
        if len(action_dict) == number_of_nodes:
            if(byzantine):
                byz_res = compute_byzantine_vote_round2(
                    number_of_nodes-1, number_of_nodes, True)
                propagate_byzantine_round2(byz_res, node_id)
            else:
                propagate_final_result(node_id)

    def make_byz_action(index):
        if index:
            return ATTACK
        else:
            return WITHDRAW

    def propagate_byzantine_round1(byz_result, node_id):
        i = 0
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                path = "/propagate/{}/{}".format(
                    make_byz_action(byz_result[i]), node_id)

                thread = Thread(target=contact_vessel, args=(
                    vessel_ip, path))
                thread.daemon = True
                thread.start()
                i += 1

    def convert_to_dict(list):
        i = 0
        byz_dict = {}
        for vessel_id, vessel_ip in vessel_list.items():
            byz_dict[vessel_id] = make_byz_action(list[i])
            i += 1
        return byz_dict

    def propagate_byzantine_round2(byz_results, node_id):
        i = 0
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                byz_dict = convert_to_dict(byz_results[i])
                payload = {'action_dict': byz_dict}
                path = "/propagate/final/{}".format(node_id)
                thread = Thread(target=contact_vessel, args=(
                    vessel_ip, path, payload))
                thread.daemon = True
                thread.start()
                i += 1
            # ------------------------------------------------------------------------------------------------------
        # ROUTES
        # ------------------------------------------------------------------------------------------------------
        # a single example (index) for get, and one for post
        # ------------------------------------------------------------------------------------------------------

    @app.route('/')
    def index():
        global node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id))

    @app.get('/vote/result')
    def get_result():
        global results_dict
        if len(results_dict) == number_of_nodes-1:
            res, res_dict = check_result()
        else:
            res = None
            res_dict = None
        return template('server/board_frontpage_footer_template.tpl',  members_name_string='OMAR & TUBAS', result=res, res_dict=res_dict, results_dict=results_dict)
    # ------------------------------------------------------------------------------------------------------

    @app.post('/vote/attack')
    def client_vote_attack():
        global node_id
        propagate_to_vessels('/propagate/{}/{}'.format(ATTACK, node_id))
        action_dict[node_id] = ATTACK
        last_result_received()

    @app.post('/vote/withdraw')
    def client_vote_withdraw():
        global node_id
        propagate_to_vessels('/propagate/{}/{}'.format(WITHDRAW, node_id))
        action_dict[node_id] = WITHDRAW
        last_result_received()

    @app.post('/vote/byzantine')
    def client_vote_byzantine():
        global node_id, byzantine
        byz_arr = compute_byzantine_vote_round1(
            number_of_nodes - 1, number_of_nodes, True)
        byzantine = True
        action_dict[node_id] = BYZANTINE
        propagate_byzantine_round1(
            byz_arr, node_id)
        last_result_received()

    @app.post('/propagate/final/<sender_node>')
    def propagate_final_received(sender_node):
        global results_dict
        json_dict = request.json
        # Remove unicode from the dict, don't know why it happens though
        received_dict = eval(json.dumps(json_dict.get('action_dict')))
        results_dict[sender_node] = received_dict

    @app.post('/propagate/<vote>/<sender_node>')
    def propagate_vote_received(vote, sender_node):
        global node_id
        action_dict[sender_node] = vote
        last_result_received()

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------

    def main():
        global vessel_list, node_id, app, number_of_nodes

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
        number_of_nodes = args.nbv
        print "The number of nodes are: {}".format(number_of_nodes)
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv+1):
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
