# Brute-force search algorithm for the optimisation of buffer tank nodal location
# Written by Bowen Fan, UCL

from epynet import Network
import numpy as np
import PySimpleGUI as sg
import pandas as pd

score_index_counter = 0
tank_elev_array = []


def solve_and_return_pressures(num_junctions):
    # function to calculate the pressure of every node at any timestep

    # call EPANET to load the network

    network = Network(inp_file)
    network.ep.ENopen(inp_file)

    network.ep.ENopenH()
    network.ep.ENinitH()

    # temp array for storing pressure of each junction at each timestep
    temp_pressure_array = np.array([])

    # big array of all pressures for all junctions at all timesteps
    perm_pressure_array = np.empty((num_junctions, 0))

    # solve for all timesteps and store each node's pressure at each timestep in an array
    runtime = 0

    while network.ep.ENnextH() > 0:

        network.ep.ENrunH()

        for junction in range(num_junctions):
            junction_pressure = network.ep.ENgetnodevalue(junction + 1, 11)
            temp_pressure_array = np.append(temp_pressure_array, junction_pressure)

        perm_pressure_array = np.append(perm_pressure_array, temp_pressure_array.reshape(num_junctions, 1), axis=1)

        runtime += network.ep.ENgettimeparam(1)
        temp_pressure_array = []

    network.ep.ENcloseH()
    network.ep.ENdeleteproject()

    return perm_pressure_array


def score_pressure_array(perm_pressure_array):
    global score_index_counter

    # array of pressures averaged across all junctions, for each timestep
    avg_pressure_array = np.array([])

    # minimum network pressure, for each timestep
    min_pressure_array = np.array([])

    # minimum average network pressure, this should occur at the time of peak demand. THIS IS THE SCORE RETURNED.
    min_average_pressure = np.array([])

    # average pressure at each junction, averaged across all timesteps
    avg_pressure_at_each_junc = np.array([])

    avg_pressure_array = np.mean(perm_pressure_array, axis=0)
    min_pressure_array = np.min(perm_pressure_array, axis=0)
    min_average_pressure = np.min(avg_pressure_array)

    score_index_counter += 1

    return min_average_pressure


def average_initial_pressures(perm_pressure_array):
    # simple function to average all nodal pressures in the network
    avg_pressure_at_each_junc = np.mean(perm_pressure_array, axis=1)

    return avg_pressure_at_each_junc


def add_tank_get_score(num_junctions, avg_initial_pressure_at_each_junc):
    global tank_elev_array
    network = Network(inp_file)

    junc_elev_array = []
    junc_x_y_array = []
    junc_id_array = []

    score_array = []

    # this loop add a tank to Node 1, calculate the peak-demand average pressure, stores it, and deletes the tank
    # it then adds a tank to Node 2 and repeats until all nodal locations are scored

    for junction in range(num_junctions):
        junc_elev_array.append(network.ep.ENgetnodevalue(junction + 1, 0))
        junc_x_y_array.append(network.ep.ENgetcoord(junction + 1))
        junc_id_array.append(network.ep.ENgetnodeid(junction + 1))

        optimum_elevation = junc_elev_array[junction] + avg_initial_pressure_at_each_junc[junction]

        tank_elev_array.append(optimum_elevation)

        network.add_tank(uid='balancing_tank', x=junc_x_y_array[junction][0], y=junc_x_y_array[junction][1],
                         elevation=optimum_elevation, diameter=100, maxlevel=1000, minlevel=0, tanklevel=0)

        network.add_pipe(uid='balancing_tank_pipe', from_node=junc_id_array[junction],
                         to_node='balancing_tank', diameter=1000, length=10, roughness=1E9, check_valve=False)

        network.save_inputfile(inp_file)

        junction_score = score_pressure_array(solve_and_return_pressures(num_junctions))

        score_array.append(junction_score)
        print("Junction index ", score_index_counter, " : ", junction_score)

        network.delete_link('balancing_tank_pipe')
        network.delete_node('balancing_tank')
        network.reset()

        network.save_inputfile(inp_file)

    return score_array


def main():
    network = Network(inp_file)

    num_junctions = 0
    num_nodes = network.ep.ENgetcount(0)

    for node in range(num_nodes):
        if network.ep.ENgetnodetype(node + 1) == 0:
            num_junctions += 1

    print("Number of junctions: ", num_junctions, "\n")

    avg_initial_pressure_at_each_junc = average_initial_pressures(solve_and_return_pressures(num_junctions))

    scores = add_tank_get_score(num_junctions, avg_initial_pressure_at_each_junc)

    best_junction = network.ep.ENgetnodeid(int(np.argmax(scores) + 1))

    junction_ids = []

    for junction in range(num_junctions):
        junction_ids.append(network.ep.ENgetnodeid(junction + 1))

    print("\nIndex of best junction: ", np.argmax(scores) + 1)

    print("ID of best junction: ", best_junction, "\nMin avg network pressure with optimized tank: ", np.max(scores))

    original_score = score_pressure_array(solve_and_return_pressures(num_junctions))

    print("\nMin avg network pressure without buffer tank: ", original_score)

    score_dataframe = pd.DataFrame({"Junction ID":junction_ids,
                                    "Min Avg Network Pressure":scores,
                                    "Tank Elevation":tank_elev_array})

    score_dataframe.index = score_dataframe.index + 1
    score_dataframe.index.name = "Junction Index"

    sorted_scores = score_dataframe.sort_values("Min Avg Network Pressure", ascending=False)

    print("\nTank locations sorted by minimum average network pressure:\n")
    print(sorted_scores)

    print("\nSaving CSV...")
    sorted_scores.to_csv("Optimal_Location_List.csv")


# GUI window using PySimpleGUI

layout = [[sg.Text('EPANET network .inp file:', size=(21, 1)),
           sg.Input(key='inp_filepath',
                    default_text='C:\\Users\\FanBo\\PycharmProjects\\fyp_ga\\pattern2.inp'),
           sg.FileBrowse(file_types=(("INP", ".inp"),))],

          [sg.Text('', size=(21, 1)),
           sg.Button('Run Search', size=(15, 1))]
          ]

window = sg.Window('Balancing Tank Location Optimization - UCL Third Year Project - Bowen Fan', layout)

while True:
    action, values = window.Read()

    inp_file = values['inp_filepath']

    if action == 'Run Search':
        main()

    elif action is None:
        break

    break

window.Close()
