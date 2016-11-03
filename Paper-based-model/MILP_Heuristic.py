from gurobipy import *
import numpy as np
import pandas as pd

###Basic Information
o = float(10/60)
# i_o = [10,6,0] #time that comsume power
i_b = [14,10,5] #total operation time
i_m = [15,11,5]#minimum time interval
prod = [36,36,36] #Production rate (Ton per batch)
#Assume each machine can process at most 36 Ton materials
machine = 3 #number of machine in each batch
batch = 6#number of batch
T = 144 #Tol time period (10min)
X = {} #Binary variable. 1 if machine m is started on batch b at or before time t and 0 otherwise
Y = {} #Binary variable. 1 if machine m is ended on batch b at or befroe time t and 0 otherwise
C = [] #Electricity market price
P = {}
E = {}
capability = [2,2,1]
power_consumed = [17,4,0]
records = []
#creation of Electricity market price (random)
# for i in range(T):
#     C.append(random.random())
cost = 0
#creation of Electricity market price 
xl = pd.ExcelFile("elec_price.xls")
df = xl.parse("Sheet1")
for i in range(24):
    for j in range(6):
        C.append(df[i+1])

for b in range(batch):

    model = Model()

    for m in range(machine):
        for t in range(T):
            X[m,b,t] = model.addVar(vtype=GRB.BINARY, name="X_m{}_b{}_t{}".format(m,b,t))
            Y[m,b,t] = model.addVar(vtype=GRB.BINARY, name="Y_m{}_b{}_t{}".format(m,b,t))
    model.update()

    for m in range(machine):
        model.addConstr(quicksum(X[m,b,t] for t in range(T)) >= i_b[m])
        for t in range(T):
            if m>0 and t<T-i_m[m-1]: #if time is still enough
                #sequential constraints
                model.addConstr(quicksum(X[m-1,b,e] for e in range(t)) >= quicksum(X[m,b,e] for e in range(t+i_m[m-1])))
                model.addConstr(quicksum(X[m,b,e] for e in range(t)) >= quicksum(Y[m,b,e] for e in range(t)))
            if t>0: #if m at batch start on or defore time t, it should start before time t+1
                model.addConstr(X[m,b,t-1] <= X[m,b,t])
                model.addConstr(Y[m,b,t-1] <= Y[m,b,t])
    #runtime constrains
    for m in range(machine):
            model.addConstr(quicksum((X[m,b,t]-Y[m,b,t]) for t in range(T)) == i_b[m])

    #consistancy constraints
    for m in range(machine):
        if m < (machine - 1):
            model.addConstr(quicksum(Y[m,b,t]-X[m+1,b,t] for t in range(T)) == 1)

    #capability constraints
    for m in range(machine):
        for t in range(T):
            usage = 0
            for i in range(b):
                usage += records[i][m,t]
            if usage == capability[m]:
                model.addConstr(X[m,b,t] == 0)
    # for m in range(machine):
    #     for t in range(T):
    #         model.addConstr(quicksum((X[m,b,t]-Y[m,b,t]) for b in range(batch)) <= capability[m])

    #calculate power consumed
    for m in range(machine):
        for t in range(T):
            if m == machine - 1:
                P[m,b,t] = 0 #the last step don't consume power
            else:
                P[m,b,t] = (X[m,b,t]-Y[m,b,t]) * power_consumed[m]/i_b[m]

    for t in range(T):
        E[t] = quicksum(P[m,b,t] for m in range(machine))

    model.setObjective(quicksum((E[t]*C[t] for t in range(T))), GRB.MINIMIZE)
    model.update()
    model.optimize()

    record = np.zeros((machine,T))
    for m in range(machine):
        for t in range(T):
            record[m,t] = abs(X[m,b,t].x - Y[m,b,t].x)
    records.append(record)

    #print result
    for m in range(machine):
        for t in range(T):
            if X[m,b,t].x == 1:
                print "machine %s at batch %s starts at time %s" % (m,b,t)
                break
        for t in range(T):
            if Y[m,b,t].x == 1:
                print "machine %s at batch %s ends at time %s" % (m,b,t)
                break
    cost += model.objVal

print cost