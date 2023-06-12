import pulp as p
from data_objects import track, location, train
from input_data import data


class math_model:
    def __init__(self, input_data: data):
        self.inputs: data = input_data
        self.model: p.LpProblem = p.LpProblem("train_dispatching", p.LpMinimize)
        departure_time = min(t.departure_time for t in self.inputs.trains)
        departure_time: int = departure_time if departure_time % self.inputs.time_step == 0 else self.inputs.time_step + self.inputs.time_step * (
                departure_time // self.inputs.time_step)
        arrival_time: int = max(t.arrival_time for t in self.inputs.trains)
        max_time_stamp: int = departure_time + 2 * (arrival_time - departure_time) + self.inputs.time_step
        self.travel_arc_variables: dict = {}
        self.waiting_arc_variables: dict = {}
        # self.arrival_arc_variable: dict = {}
        obj = 0
        for t in self.inputs.trains:
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    tr_arc: travel_arc = travel_arc(t, time, tr)
                    self.travel_arc_variables["t".join(tr_arc.get_unique_key())] = tr_arc.get_binary_variable()
                for loc in t.route:
                    if loc == t.arrival_location or loc == t.departure_location:
                        continue
                    w_arc: waiting_arc = waiting_arc(t, time, loc)
                    self.waiting_arc_variables["w".join(w_arc.get_unique_key())] = w_arc.get_binary_variable_for_waiting()
                    # self.arrival_arc_variable["a".join(w_arc.get_unique_key())] = w_arc.get_binary_variable_for_arrival()

            # objective function
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    if tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        time_stamp: int = time + tr.traveled_time(self.inputs.trains_speed)
                        obj += self.travel_arc_variables['t'.join(tr_arc.get_unique_key())] * (time_stamp - t.arrival_time) * t.category

            constraint_value2 = constraint_value3 = constraint_value22 = constraint_value33 = 0
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    if tr.departure_location == t.departure_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        uni_key: str = 't'.join(tr_arc.get_unique_key())
                        if time >= t.departure_time:
                            constraint_value2 += self.travel_arc_variables[uni_key]
                        else:
                            constraint_value22 += self.travel_arc_variables[uni_key]
                    elif tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        uni_key: str = 't'.join(tr_arc.get_unique_key())
                        if time >= t.departure_time:
                            constraint_value3 += self.travel_arc_variables[uni_key]
                        else:
                            constraint_value33 += self.travel_arc_variables[uni_key]
            # constraint 2
            self.model += constraint_value2 == 1
            self.model += constraint_value22 == 0
            # constraint 3
            self.model += constraint_value3 == 1
            self.model += constraint_value33 == 0

            # constraint 4
            for time in range(t.departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    if tr.arrival_location == t.arrival_location:
                        continue
                    tr_arc: travel_arc = travel_arc(t, time, tr)
                    uni_key: str = 't'.join(tr_arc.get_unique_key())
                    sum1 = self.travel_arc_variables[uni_key]
                    time_stamp: int = time + tr.traveled_time(self.inputs.trains_speed)
                    # ar_arc: waiting_arc = waiting_arc(t, self.inputs.time_step * (time_stamp // self.inputs.time_step), tr.arrival_location)
                    # uni_key2: str = 'a'.join(ar_arc.get_unique_key())
                    # if uni_key2 in self.arrival_arc_variable:
                    #     self.model += self.travel_arc_variable[uni_key] == self.arrival_arc_variable[uni_key2]
                    if not tr.arrival_location.is_siding:
                        time_stamp += self.inputs.trains_waiting_time_in_stations
                    #     ar_arc: waiting_arc = waiting_arc(t, self.inputs.time_step * (time_stamp // self.inputs.time_step), tr.arrival_location)
                    #     uni_key2: str = 'a'.join(ar_arc.get_unique_key())
                    #     if uni_key2 in self.arrival_arc_variable:
                    #         self.model += self.travel_arc_variable[uni_key] == self.arrival_arc_variable[uni_key2]
                    w_arc: waiting_arc = waiting_arc(t, self.inputs.time_step * (time_stamp // self.inputs.time_step), tr.arrival_location)
                    uni_key2: str = 'w'.join(w_arc.get_unique_key())
                    sum1 += self.waiting_arc_variables[uni_key2] if uni_key2 in self.waiting_arc_variables else 0
                    sum2 = 0
                    if time_stamp % self.inputs.time_step > 0:
                        time_stamp = self.inputs.time_step * (time_stamp // self.inputs.time_step)
                    w_arc: waiting_arc = waiting_arc(t, time_stamp + self.inputs.time_step, tr.arrival_location)
                    uni_key: str = 'w'.join(w_arc.get_unique_key())
                    sum2 += self.waiting_arc_variables[uni_key] if uni_key in self.waiting_arc_variables.keys() else 0
                    for tr2 in t.tracks:
                        if tr2.departure_location == tr.arrival_location:
                            tr_arc2: travel_arc = travel_arc(t, time_stamp + self.inputs.time_step, tr2)
                            uni_key: str = 't'.join(tr_arc2.get_unique_key())
                            sum2 += self.travel_arc_variables[uni_key] if uni_key in self.travel_arc_variables.keys() else 0
                            break
                    self.model += sum1 == sum2
            for time in range(t.departure_time, max_time_stamp, self.inputs.time_step):
                for loc in t.route:
                    if loc == t.arrival_location or loc == t.departure_location:
                        continue
                    w_arc: waiting_arc = waiting_arc(t, time, loc)
                    uni_key: str = 'w'.join(w_arc.get_unique_key())
                    sum1 = self.waiting_arc_variables[uni_key]
                    for tr in t.tracks:
                        if tr.arrival_location == loc:
                            for dep_time in range(t.departure_time, max_time_stamp, self.inputs.time_step):
                                time_stamp: int = dep_time + tr.traveled_time(self.inputs.trains_speed)
                                if not loc.is_siding:
                                    time_stamp += self.inputs.trains_waiting_time_in_stations
                                # time_stamp = self.inputs.time_step * (time_stamp // self.inputs.time_step)
                                if time_stamp >= time:
                                    tr_arc: travel_arc = travel_arc(t, dep_time, tr)
                                    uni_key: str = 't'.join(tr_arc.get_unique_key())
                                    sum1 += self.travel_arc_variables[uni_key] if uni_key in self.travel_arc_variables.keys() else 0
                                    break
                            break
                    sum2 = 0
                    w_arc: waiting_arc = waiting_arc(t, time + self.inputs.time_step, loc)
                    uni_key: str = 'w'.join(w_arc.get_unique_key())
                    sum2 += self.waiting_arc_variables[uni_key] if uni_key in self.waiting_arc_variables.keys() else 0
                    for tr in t.tracks:
                        if tr.departure_location == loc:
                            tr_arc: travel_arc = travel_arc(t, time + self.inputs.time_step, tr)
                            uni_key: str = 't'.join(tr_arc.get_unique_key())
                            sum2 += self.travel_arc_variables[uni_key] if uni_key in self.travel_arc_variables else 0
                            break
                    self.model += sum1 == sum2

        # waiting sites capacity constraint
        for key, x in self.waiting_arc_variables.items():
            w_arc = get_waiting_arc(self.inputs, key)
            constraint_value = x
            c: bool = False
            for t in self.inputs.trains:
                if t != w_arc.train:
                    w_arc2: waiting_arc = waiting_arc(t, w_arc.time_stamp, w_arc.waiting_station)
                    uni_key: str = 'w'.join(w_arc2.get_unique_key())
                    if uni_key in self.waiting_arc_variables.keys():
                        c = True
                        constraint_value += self.waiting_arc_variables[uni_key]
                    # uni_key: str = 'a'.join(w_arc2.get_unique_key())
                    # if uni_key in self.arrival_arc_variable.keys():
                    #     c = True
                    #     constraint_value += self.arrival_arc_variable[uni_key]
            if c:
                self.model += constraint_value <= w_arc.waiting_station.capacity

        # conflicts constraint
        for key, x in self.travel_arc_variables.items():
            tr_arc = get_travel_arc(self.inputs, key)
            travel_time = tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
            constraint_value = x
            c: bool = False
            for t in self.inputs.trains:
                if t != tr_arc.train:
                    for time in range(tr_arc.time_stamp + self.inputs.time_step, max_time_stamp, self.inputs.time_step):
                        if time - tr_arc.time_stamp <= travel_time:
                            tr_arc2 = travel_arc(t, time, tr_arc.traveled_track)
                            uni_key: str = "t".join(tr_arc2.get_unique_key())
                            if uni_key in self.travel_arc_variables.keys():
                                c = True
                                constraint_value += self.travel_arc_variables[uni_key]
                            if tr_arc.traveled_track.is_single_track:
                                tr_arc3 = travel_arc(t, time, tr_arc.traveled_track.get_inverse())
                                uni_key: str = "t".join(tr_arc3.get_unique_key())
                                if uni_key in self.travel_arc_variables.keys():
                                    c = True
                                    constraint_value += self.travel_arc_variables[uni_key]
            if c:
                self.model += constraint_value <= 1
        self.model += obj

    def solve(self):
        self.model.solve()
        print(f'Result status = {p.LpStatus[self.model.status]}')
        print(f'Objective function value = {p.value(self.model.objective)}')
        delay: int = 0
        for key, x in self.travel_arc_variables.items():
            if p.value(x) == 1:
                tr_arc = get_travel_arc(self.inputs, key)
                if tr_arc.train.arrival_location == tr_arc.traveled_track.arrival_location:
                    time_stamp: int = tr_arc.time_stamp + tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
                    delay += (time_stamp - tr_arc.train.arrival_time)
        print(f'Total delay of trains = {delay}')
        for key, x in self.travel_arc_variables.items():
            if p.value(x) == 1:
                tr_arc = get_travel_arc(self.inputs, key)
                time_stamp: int = tr_arc.time_stamp + tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
                if tr_arc.traveled_track.departure_location == tr_arc.train.departure_location:
                    print(f'Train {tr_arc.train} travel from {tr_arc.train.departure_location} to {tr_arc.train.arrival_location}')
                print(
                    f'departure from {tr_arc.traveled_track.departure_location.index + 1} at {toTimeFormat(tr_arc.time_stamp)},'
                    f' arrival to {tr_arc.traveled_track.arrival_location.index + 1} at {toTimeFormat(time_stamp)}')
                if tr_arc.traveled_track.arrival_location == tr_arc.train.arrival_location:
                    print(f'Scheduled arrival time for train {tr_arc.train.index + 1} is {toTimeFormat(tr_arc.train.arrival_time)}')


class travel_arc:
    def __init__(self, trn: train, time: int, tr: track):
        self.train = trn
        self.time_stamp: int = time
        self.traveled_track: track = tr

    def get_unique_key(self) -> tuple:
        return str(self.time_stamp), str(self.traveled_track.departure_location.index), str(
            self.traveled_track.arrival_location.index), str(self.train.index)

    def get_binary_variable(self):
        return p.LpVariable("t".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)


class waiting_arc:
    def __init__(self, trn: train, time: int, loc: location):
        self.train = trn
        self.time_stamp: int = time
        self.waiting_station: location = loc

    def get_unique_key(self) -> tuple:
        return str(self.time_stamp), str(self.waiting_station.index), str(self.train.index)

    def get_binary_variable_for_waiting(self):
        return p.LpVariable("w".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)

    def get_binary_variable_for_arrival(self):
        return p.LpVariable("a".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)


def get_waiting_arc(input_data: data, s: str) -> waiting_arc:
    l = s.split('w')
    return waiting_arc(input_data.trains[int(l[2])], int(l[0]), input_data.locations[int(l[1])])


def get_arrival_arc(input_data: data, s: str) -> waiting_arc:
    l = s.split('a')
    return waiting_arc(input_data.trains[int(l[2])], int(l[0]), input_data.locations[int(l[1])])


def get_travel_arc(input_data: data, s: str) -> travel_arc:
    l = s.split('t')
    return travel_arc(input_data.trains[int(l[3])], int(l[0]), track(input_data.locations[int(l[1])], input_data.locations[int(l[2])]))


def toTimeFormat(time: int) -> str:
    hour = time // 60
    s = ("0" if hour < 10 else "") + str(hour) + ":"
    minutes = time % 60
    s += ("0" if minutes < 10 else "") + str(minutes)
    return s
