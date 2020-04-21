from epynet import Network
import numpy as np

inp_file = "C:\\Users\\FanBo\\PycharmProjects\\fyp_ga\\pattern_2.inp"


def solve_and_return_pressures(num_junctions):
    network = Network("pattern_2.inp")

    # network.load_network()

    network.ep.ENopen("pattern_2.inp")

    network.ep.ENopenH()
    network.ep.ENinitH()

    # temp array for storing pressure of each junction at each timestep
    temp_pressure_array = np.array([])

    # big array of all pressures for all junctions at all timesteps
    perm_pressure_array = np.empty((num_junctions, 0))

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

    print(min_average_pressure)

    return min_average_pressure


def average_initial_pressures(perm_pressure_array):

    avg_pressure_at_each_junc = np.mean(perm_pressure_array, axis=1)

    return avg_pressure_at_each_junc


def add_tank_get_score(num_junctions, avg_initial_pressure_at_each_junc):
    network = Network(inp_file)

    junc_elev_array = []
    junc_x_y_array = []
    junc_id_array = []

    score_array = []

    for junction in range(num_junctions):

        junc_elev_array.append(network.ep.ENgetnodevalue(junction + 1, 0))
        junc_x_y_array.append(network.ep.ENgetcoord(junction + 1))
        junc_id_array.append(network.ep.ENgetnodeid(junction + 1))

        network.add_tank(uid='balancing_tank', x=junc_x_y_array[junction][0], y=junc_x_y_array[junction][1],
                         elevation=junc_elev_array[junction] + avg_initial_pressure_at_each_junc[junction],
                         diameter=1000, maxlevel=1000, minlevel=0, tanklevel=0)

        network.add_pipe(uid='balancing_tank_pipe', from_node=junc_id_array[junction],
                         to_node='balancing_tank', diameter=1000, length=10, roughness=1E9, check_valve=False)

        network.save_inputfile("pattern_2.inp")

        score_array.append(score_pressure_array(solve_and_return_pressures(num_junctions)))

        network.delete_link('balancing_tank_pipe')
        network.delete_node('balancing_tank')
        network.reset()

        network.save_inputfile("pattern_2.inp")

    return score_array


def main():
    network = Network(inp_file)

    num_junctions = 0

    num_nodes = network.ep.ENgetcount(0)

    for node in range(num_nodes):
        if network.ep.ENgetnodetype(node + 1) == 0:
            num_junctions += 1

    print("Number of junctions: ", num_junctions)

    avg_initial_pressure_at_each_junc = average_initial_pressures(solve_and_return_pressures(num_junctions))

    print(avg_initial_pressure_at_each_junc)

    scores = add_tank_get_score(num_junctions, avg_initial_pressure_at_each_junc)

    print("Best junction: ", np.argmax(scores))
    print(np.max(scores))

main()