from gurobipy import *
import math as math
import traceback

try:

    # Create a new model
    m = Model("industrial process")

    iterations = 3

    EAFS = 2
    LFS = 2
    VCS = 1

    EAF_DURATION = 140
    LF_DURATION = 100
    VC_DURATION = 50

    EAF_LF_TRANSFER_TIME = 10
    LF_VC_TRANSFER_TIME = 10

    EAF_MIN_DOWN_TIME = 60
    EAF_MAX_DOWM_TIME = 180

    # closer to 59 euros. min 50 max 68
    # normal prices
    ELECTRICITY_PRICES = [5, 5, 6, 7, 7, 8, 9, 9, 10, 11, 12, 13, 13, 12, 12, 11, 10, 10, 9, 8, 8, 7, 6, 5]
    # weird prices
    # ELECTRICITY_PRICES = [15, 14, 13, 12, 11, 9, 7, 5, 3, 8, 12, 16, 12, 11, 10, 9, 8, 6, 4, 4, 3, 2, 2, 2]
    # ELECTRICITY_PRICES = [15, 14, 13, 50, 11, 9, 7, 5, 3, 8, 80, 16, 12, 11, 10, 100, 8, 6, 4, 4, 3, 2, 2, 2]
    # actual prices
    # ELECTRICITY_PRICES = [32.13, 31.53, 30.46, 30.50, 31.11, 29.95, 34.78, 51.33, 59.24, 59.00, 50.35, 42.44, 41.65, 41.16, 37.59, 39.09, 39.91, 49.40, 53.76, 59.67, 45.74, 40.39, 38.17, 31.56]
    INTERVALS = len(ELECTRICITY_PRICES)
    def averaged(x):
        res = {}
        for i in range(0,len(x)):
            res[i] = x[i] - sum(x) / len(x)
        return res
    averaged_prices = averaged(ELECTRICITY_PRICES)
    EAF_ELECTRICITY_USAGE = 17  # between 10 and 80
    LF_ELECTRICITY_USAGE = 4

    eaf_start_times = {}
    lf_start_times = {}
    vc_start_times = {}

    eaf_iteration_interval_decisions = {}
    lf_iteration_interval_decisions = {}

    def get_cost_from_interval_decision(decisions, usage):
        cost = 0
        for i in range(INTERVALS):
                cost += ELECTRICITY_PRICES[i] * usage * decisions[i]
        return cost

    def get_benefit_from_interval_decision(decisions, usage):
        cost = 0
        for i in range(INTERVALS):
                cost += averaged_prices[i] * usage * decisions[i]
        return cost

    for eaf in range(EAFS):
        for iteration in range(iterations):
            s_eaf = m.addVar(vtype=GRB.INTEGER, name="s_eaf%d_i%d" % (eaf, iteration))
            # eaf_price_index = m.addVar(vtype=GRB.INTEGER, name="eaf%d_pindex_i%d" % (eaf, iteration))
            start_times = eaf_start_times.setdefault(eaf, [])
            start_times.append(s_eaf)
            m.update()

            # m.addConstr(eaf_price_index == (s_eaf * INTERVALS) / 1440, "eaf%d_pindex_i%d_c" % (eaf, iteration))
            eaf_price_index = (s_eaf * INTERVALS) / 1440

            gets = 0
            gts = 0

            for i in range(INTERVALS):
                in_interval_i = m.addVar(vtype=GRB.BINARY, name="interval%d_eaf%d_i%d" % (i, eaf, iteration))
                index_get_interval = m.addVar(vtype=GRB.BINARY, name="index_get_interval%d_eaf%d_i%d" % (i, eaf, iteration))
                index_gt_interval = m.addVar(vtype=GRB.BINARY, name="index_gt_interval%d_eaf%d_i%d" % (i, eaf, iteration))
                gets += index_get_interval
                gts += index_gt_interval

                m.update()
                m.addConstr(i * index_get_interval - eaf_price_index <= 0, "eaf%d_i%d_inter%d_1" % (eaf, iteration, i))
                m.addConstr((i + 1) * index_gt_interval - (eaf_price_index + 1) <= -1, "eaf%d_i%d_inter%d_2" % (eaf, iteration, i))
                m.addConstr(index_get_interval - index_gt_interval == in_interval_i, "eaf%d_i%d_inter%d_3" % (eaf, iteration, i))

                decisions = eaf_iteration_interval_decisions.setdefault((eaf, iteration), [])
                decisions.append(in_interval_i)

            m.addConstr(gets == eaf_price_index + 1, "gets_eaf%d_i%d" % (eaf, iteration))
            m.addConstr(gts == eaf_price_index, "gts_eaf%d_i%d" % (eaf, iteration))
            m.addConstr(quicksum(eaf_iteration_interval_decisions[eaf, iteration]) >= 1, "interval_decision_eaf%d_i%d" % (eaf, iteration))

            if iteration == 0:
                m.addConstr(s_eaf >= 0, "s0_eaf%d" % eaf)

    for lf in range(LFS):
        for iteration in range(iterations):
            s_lf = m.addVar(vtype=GRB.INTEGER, name="s_lf%d_i%d" % (lf, iteration))
            lf_price_index = m.addVar(vtype=GRB.CONTINUOUS, name="lf%d_pindex_i%d" % (lf, iteration))
            start_times = lf_start_times.setdefault(lf, [])
            start_times.append(s_lf)
            m.update()

            m.addConstr(lf_price_index == s_lf * 24 / 1440, "lf%d_pindex_i%d_c" % (eaf, iteration))
            # m.addConstr(lf_price_index == (s_lf * INTERVALS) / 1440, "lf%d_pindex_i%d_c" % (eaf, iteration))
            # lf_price_index = (s_lf * INTERVALS) / 1440

            gets = 0
            gts = 0

            for i in range(INTERVALS):
                in_interval_i = m.addVar(vtype=GRB.BINARY, name="interval%d_lf%d_i%d" % (i, lf, iteration))
                index_get_interval = m.addVar(vtype=GRB.BINARY, name="interval%d_lf%d_get_i" % (i, lf))
                index_gt_interval = m.addVar(vtype=GRB.BINARY, name="interval%d_lf%d_gt_i" % (i, lf))
                gets += index_get_interval
                gts += index_gt_interval

                m.update()
                m.addConstr(i * index_get_interval - lf_price_index <= 0, "lf%d_i%d_inter%d_1" % (lf, iteration, i))
                m.addConstr((i + 1) * index_gt_interval - (lf_price_index + 1) <= -1, "lf%d_i%d_inter%d_2" % (lf, iteration, i))
                m.addConstr(index_get_interval - index_gt_interval == in_interval_i, "lf%d_i%d_inter%d_3" % (lf, iteration, i))

                decisions = lf_iteration_interval_decisions.setdefault((lf, iteration), [])
                decisions.append(in_interval_i)

            m.addConstr(lf_price_index + 0.001 <= gets, "gets_lf%d_i%d" % (lf, iteration))
            m.addConstr(lf_price_index - 0.999 <= gts, "gts_lf%d_i%d" % (lf, iteration))
            # m.addConstr(gets == lf_price_index + 1, "gets_lf%d_i%d" % (lf, iteration))
            # m.addConstr(gts == lf_price_index, "gts_lf%d_i%d" % (lf, iteration))
            m.addConstr(quicksum(lf_iteration_interval_decisions[lf, iteration]) >= 1, "interval_decision_lf%d_i%d" % (lf, iteration))

            # add presedence constraint
            s_eaf = eaf_start_times[lf][iteration]
            m.addConstr(s_eaf + EAF_DURATION + EAF_LF_TRANSFER_TIME == s_lf, "prd_s_lf_eaf%d_i%d" % (lf, iteration))

    for iteration in range(iterations):
        s_vc = m.addVar(vtype=GRB.INTEGER, name="s_vc_i%d" % (iteration))
        start_times = vc_start_times.setdefault(0, [])
        start_times.append(s_vc)
        m.update()

        # add presedence constraints
        for lf in range(LFS):
            s_lf = lf_start_times[lf][iteration]
            m.addConstr(s_lf + LF_DURATION + LF_VC_TRANSFER_TIME == s_vc, "prd_s_vc_lf%d_i%d" % (lf, iteration))

        if iteration > 0:
            for eaf in range(EAFS):
                s_eaf = eaf_start_times[eaf][iteration]
                prev_s_eaf = eaf_start_times[eaf][iteration - 1]
                m.addConstr((prev_s_eaf + EAF_DURATION + EAF_MIN_DOWN_TIME) - s_eaf <= 0, "prd_s_prev_eaf_eaf_mindt_i%d" % iteration)
                m.addConstr(s_eaf - (prev_s_eaf + EAF_DURATION + EAF_MAX_DOWM_TIME) <= 0, "prd_s_prev_eaf_eaf_mindt_i%d" % iteration)

                s_lf = lf_start_times[eaf][iteration]
                prev_s_lf = lf_start_times[eaf][iteration - 1]
                m.addConstr((prev_s_lf + LF_DURATION) - s_lf <= 0, "prd_s_prev_lf_i%d" % iteration)

            s_vc = vc_start_times[0][iteration]
            prev_s_vc = vc_start_times[0][iteration - 1]
            m.addConstr((prev_s_vc + VC_DURATION) - s_vc <= 0, "prd_s_prev_vc_i%d" % iteration)

    last_s_vc = vc_start_times[0][iterations - 1]
    m.addConstr(last_s_vc + VC_DURATION <= 1440, "end_time")

    objective = 0
    benefit = 0
    for iteration in range(iterations):
        for eaf in range(EAFS):
            cost = get_cost_from_interval_decision(eaf_iteration_interval_decisions[eaf, iteration], EAF_ELECTRICITY_USAGE)
            cost += get_cost_from_interval_decision(lf_iteration_interval_decisions[eaf, iteration], LF_ELECTRICITY_USAGE)
            objective = objective + cost

            benefit += get_benefit_from_interval_decision(eaf_iteration_interval_decisions[eaf, iteration], EAF_ELECTRICITY_USAGE)
            benefit += get_benefit_from_interval_decision(lf_iteration_interval_decisions[eaf, iteration], LF_ELECTRICITY_USAGE)

    m.setObjective(benefit, GRB.MINIMIZE)

    m.optimize()

    for v in m.getVars():
        if ('interval' not in v.varName and 'index' not in v.varName) and True:
            print(v.varName, v.x)

    print('Obj:', m.objVal)
except GurobiError:
    print('Error reported')
    traceback.print_exc()
